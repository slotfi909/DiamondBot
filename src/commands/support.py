from typing import Callable, Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from prisma.enums import UserRole, PaymentStatus, PaymentMethod
from prisma.models import User

# Constants
from src.constants import (
    CreateFactorState,
    CONFIRM_FACTOR_PREFIX,
    ConfirmFactorState,
    CONFIRM_CONFIRM_FACTOR_PREFIX,
    JOIN_CHAT_START_COMMAND,
    PENDING_ORDER_LIFETIME_MINUTES
)

# Utils
from src.utils.group import extract_status_change
from src.utils.db import db
from src.utils.keyboard import (
    main_keyboard,
    chat_keyboard,
    create_factor_keyboard,
    confirm_factor_keyboard
)
from src.utils.user import get_user
from src.utils.chat import get_chat, create_chat_message, get_reciever
from src.utils.message import from_student, from_advisor, bold
from src.utils.other import create_order, to_utc
from src.utils.time import substract_minutes
from src.guards import ignore_none_registered, ignore_none_advisor


async def clear_chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE, chat_id=None):
    fake_msg = await ctx.bot.send_message(chat_id=chat_id if chat_id else update.effective_chat.id, text='در حال پاکسازی...', reply_markup=ReplyKeyboardRemove())
    await ctx.bot.delete_message(chat_id=fake_msg.chat_id, message_id=fake_msg.message_id)

    if not chat_id:
        await update.message.delete()


async def add_group(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    was_member, _ = extract_status_change(update.my_chat_member)

    chat_id = update.my_chat_member.chat.id
    chat_name = update.my_chat_member.chat.title

    if was_member:
        return await db.group.delete(
            where={
                'tel_group_id': chat_id
            }
        )

    already_exists = (await db.group.find_unique(
        where={
            "tel_group_id": chat_id
        }
    )) is not None

    if already_exists:
        return

    final_string = 'لیست نهایی ادمین ها:\n'

    async with db.tx() as tx:
        count = await tx.group.count()

        if count == 0:
            admins = await ctx.bot.get_chat_administrators(chat_id=chat_id)

            for admin in admins:
                user_id = admin.user.id
                admin_identifier = admin.user.username if admin.user.username is not None else admin.user.full_name
                final_string += admin_identifier
                final_string += '\n'
                await tx.user.update(
                    where={
                        "tel_id": user_id
                    },
                    data={
                        "user_role": UserRole.ADMIN
                    }
                )

        await tx.group.create(
            data={
                'tel_group_id': chat_id,
                'group_name': chat_name
            }
        )

    if count == 0:  # there isnt any group registered in db
        await ctx.bot.send_message(update.effective_chat.id, text=final_string)


async def add_member_to_advisors(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    chat_id = update.message.chat.id

    group = await db.group.find_first(
        where={
            "tel_group_id": chat_id,
            "primary": True
        }
    )

    if group is None:
        return ConversationHandler.END

    is_not_registered = await ignore_none_registered(update, ctx, with_message=False)

    if is_not_registered:
        full_name = update.effective_user.first_name + \
            " " + update.effective_user.last_name

        text = (
            "برای تبدیل شدن به مشاور باید که توی ربات ثبت نام کنی."
            "\n\n"
            f"کاربر {
                full_name} ابتدا توی ربات ثبت نام کن و یکبار از این گروه لفت بده و دوباره وارد شو تا به مشاور تبدیل بشی."
        )

        await ctx.bot.send_message(update.effective_chat.id, text=text)
        return ConversationHandler.END

    tel_id = update.effective_user.id

    await db.user.update(
        where={
            "tel_id": tel_id,
            "user_role": UserRole.STUDENT
        },
        data={
            "user_role": UserRole.ADVISOR
        }
    )

    await ctx.bot.send_message(update.effective_chat.id, text="مشاور جدید اضافه شد :)")


async def remove_member_from_advisors(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    chat_id = update.message.chat.id

    group = await db.group.find_first(
        where={
            "tel_group_id": chat_id,
            "primary": True
        }
    )

    if group is None:
        return ConversationHandler.END

    is_not_advisor = await ignore_none_advisor(update, ctx, with_message=False)

    if is_not_advisor:
        return ConversationHandler.END

    tel_id = update.effective_user.id

    await db.user.update(
        where={
            "tel_id": tel_id,
            "user_role": UserRole.ADVISOR
        },
        data={
            "user_role": UserRole.STUDENT
        }
    )


def create_request_advisor(join_chat_label="ورود به مکالمه", advisor_group_join_builder: Optional[Callable[[User], str]] = None):
    async def reqest_advisor(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
        primary_group = await db.group.find_first(
            where={
                "primary": True
            }
        )

        keyboard = await main_keyboard(update, ctx)

        if primary_group is None:
            return await message_sender("متاسفانه این قابلیت فعال نمی باشد.", keyboard)

        user = await get_user(update.effective_user.id)

        chat = await db.chat.create(
            data={
                "started_by": {
                    "connect": {
                        "user_id": user.user_id
                    }
                }
            }
        )

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(join_chat_label, url=f'https://t.me/{ctx.bot.username}?start={JOIN_CHAT_START_COMMAND}-{chat.chat_id}')]])

        ctx.user_data["chat_id"] = chat.chat_id

        group_text = f"دانش آموز {user.firstname} {
            user.lastname} در خواست پشتیبانی کرده است برای وارد شدن به مکالمه دکمه زیر را فشار دهید."

        if advisor_group_join_builder is not None:
            group_text = advisor_group_join_builder(user)

        await ctx.bot.send_message(chat_id=primary_group.tel_group_id, text=group_text, reply_markup=keyboard)

        keyboard = await chat_keyboard(update, ctx)

        text = (
            "درخواست شما برای پشتیبانان ارسال شد به محض قبول درخواست وارد مکالمه می شوید..."
            "\n\n"
            f"{bold('  ساعات پاسخگویی: 10 الی 22 🌃')}"
            "\n"
 "در صورتی که خارج از این ساعات درخواست می دهید، دکمه خروج از چت را بزنید"
            "\n\n"
            "ربات تنها امکان انتقال پیام های متنی و عکس را دارد و در صورت ارسال موارد دیگر مثل فایل و یا GIF پیام شما نادیده گرفته می شود."
        )

        await message_sender(text, keyboard, edit=False)

    return reqest_advisor


async def chat_message_broker(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    chat = await get_chat(update, ctx)

    text = update.effective_message.text
    photos = update.effective_message.photo
    caption = update.effective_message.caption
    tel_chat_id = update.effective_chat.id

    if chat.started_by.tel_chat_id == tel_chat_id and chat.received_by is None:
        if update.effective_message:
            await update.effective_message.delete()

        return await message_sender(text="هنوز مشاوری درخواست پشتیبانی را قبول نکرده لطفا صبر کنید...", reply_markup=await chat_keyboard(update, ctx), edit=False)

    reciever = chat.received_by if chat.started_by.tel_chat_id == tel_chat_id else chat.started_by
    sender = chat.started_by if chat.started_by.tel_chat_id == tel_chat_id else chat.received_by

    await create_chat_message(chat.chat_id, tel_chat_id, text, photos, caption)

    message = await from_advisor(sender.tel_id, sender.lastname, text) if sender.user_role == UserRole.ADVISOR or sender.user_role == UserRole.ADMIN else from_student(
        sender.firstname, sender.lastname, text)

    if text:
        await ctx.bot.send_message(chat_id=reciever.tel_chat_id, text=message)

    if photos:
        await ctx.bot.send_photo(chat_id=reciever.tel_chat_id, photo=photos[-1].file_id, caption=message)


async def exit_chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    chat = await get_chat(update, ctx)

    await db.chat.update(
        where={
            "chat_id": chat.chat_id
        },
        data={
            "exited_at": datetime.now()
        }
    )

    ctx.user_data.pop("chat_id")

    tel_id = update.effective_user.id

    reciever = get_reciever(chat, tel_id)

    if reciever:
        await ctx.bot.send_message(chat_id=reciever.tel_chat_id, text="طرف مقابل چت را خاتمه داد.", reply_markup=await main_keyboard(update, ctx, target_tel_id=reciever.tel_id))
        await clear_chat(update, ctx, reciever.tel_chat_id)

    await clear_chat(update, ctx)

    return await message_sender("شما از چت خارج شدید.", reply_markup=await main_keyboard(update, ctx), edit=False)


async def create_factor(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    keyboard = await create_factor_keyboard()

    return await message_sender("شما در حال حاظر در حال ایجاد فاکتور برای دانش آموزی هستید که در حال مکالمه با آن هستید. ابتدا می بایست مشخص کنید که برای کدام بسته می خواهید فاکتور ایجاد کنید؟ \n\n دقت کنید که فاکتوری که می سازید برای 20 دقیقه معتبر است.", reply_markup=keyboard, edit=False)


async def collect_product_for_factor(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    ctx.user_data["in_conversation"] = True

    chat = await get_chat(update, ctx)
    product_id = int(update.callback_query.data.split(" ")[1])
    student = get_reciever(chat, update.effective_chat.id)

    if not student:
        await message_sender("طرف مقابلی به چت اضافه نشده است.", edit=False)

        if "in_conversation" in ctx.user_data:
            ctx.user_data["in_conversation"] = False

        return ConversationHandler.END

    product = await db.product.find_unique(
        where={
            "product_id": product_id
        }
    )

    text = (
        "مطمئن هستید که می خواهید برای دانش آموز "
        f"{student.firstname} {student.lastname} "
        "فاکتور "
        f"{product.title} "
        "را بسازید؟"
    )

    await message_sender(text, InlineKeyboardMarkup([[InlineKeyboardButton("مطمئن هستم", callback_data=CONFIRM_FACTOR_PREFIX + " " + str(product.product_id))]]), edit=False)

    return CreateFactorState.CONFIRM


async def confirm_create_factor(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    chat = await get_chat(update, ctx)
    product_id = int(update.callback_query.data.split(" ")[1])
    student = get_reciever(chat, update.effective_chat.id)

    if not student:
        await message_sender("طرف مقابلی به چت اضافه نشده است.")

        if "in_conversation" in ctx.user_data:
            ctx.user_data["in_conversation"] = False

        return ConversationHandler.END

    advisor = await get_user(update.effective_user.id)

    product, _, created_successfully = await create_order(product_id=product_id, target_user_tel_id=student.tel_id, payment_method=PaymentMethod.MANUAL)

    if not created_successfully:
        await message_sender("متاسفانه ظرفیت بسته مورد نظر پر شده است.")

        if "in_conversation" in ctx.user_data:
            ctx.user_data["in_conversation"] = False

        return ConversationHandler.END

    await ctx.bot.send_message(chat_id=student.tel_chat_id, text=f"مشاور {advisor.firstname} {advisor.lastname} برای شما فاکتور جدیدی برای {product.title} ساخته است هماهنگی های لازم را با مشاور انجام دهید تا فاکتور شما تایید شود.")

    await message_sender("فاکتور با مشخصات تایید شده ساخته شد، بعد از اطمینان از پرداخت می توانید آن را تایید کنید.", edit=False)

    if "in_conversation" in ctx.user_data:
        ctx.user_data["in_conversation"] = False

    return ConversationHandler.END


async def confirm_factor(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    chat = await get_chat(update, ctx)
    student = get_reciever(chat, update.effective_user.id)
    keyboard = await confirm_factor_keyboard(update, ctx)

    return await message_sender(f"فاکتور های زیر، فاکتور هایی هستند که برای دانش آموز {student.firstname} {student.lastname} ساخته شده است.\n فاکتور های جدید تر بالای لیست قرار دارند.", keyboard, edit=False)


async def collect_factor(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    ctx.user_data["in_conversation"] = True

    order_id = int(update.callback_query.data.split(" ")[1])

    order = await db.order.find_unique(
        where={
            "order_id": order_id
        },
        include={
            "product": True,
            "user": True,
            "payment": True
        }
    )

    text = (
        f"مطمئن هستید که می خواهید فاکتور برای دانش آموز {order.user.firstname} {
            order.user.lastname} را برای {order.product.title} با مبلغ {order.payment.amount} تایید کنید؟"
    )

    await message_sender(text, InlineKeyboardMarkup([[InlineKeyboardButton("مطمئن هستم", callback_data=CONFIRM_CONFIRM_FACTOR_PREFIX + " " + str(order.order_id))]]), edit=False)

    return ConfirmFactorState.CONFIRM_FACTOR_COLLECTED


async def confirm_confirm_factor(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    order_id = int(update.callback_query.data.split(" ")[1])

    async with db.tx() as tx:
        order = await tx.order.find_first(where={
            "order_id": order_id,
            "created_at": {
                'gte': to_utc(substract_minutes(to_utc(datetime.now()), PENDING_ORDER_LIFETIME_MINUTES))
            }
        }, include={
            "payment": True
        })

        if not order:
            await message_sender("متاسفانه مهلت تایید فاکتور به اتمام رسیده است.")
            return ConversationHandler.END

        previous_payment_id = order.payment.payment_id

        order = await db.order.update(
            where={
                "order_id": order.order_id
            },
            data={
                "advisor": {
                    "connect": {
                        "tel_id": update.effective_user.id
                    }
                },
                "payment": {
                    "create": {
                        "amount": order.payment.amount,
                        "method": PaymentMethod.MANUAL,
                        "status": PaymentStatus.COMPLETED
                    }
                }
            },
            include={
                "user": True,
                "product": True,
                "advisor": True,
                "payment": True
            }
        )

        await db.payment.delete(
            where={
                "payment_id": previous_payment_id
            }
        )

    text = (
        "شما فاکتور را برای دانش آموز "
        f"{order.user.firstname} {order.user.lastname} "
        "برای "
        f"{order.product.title} "
        "تایید کردید"
    )

    student_text = (
        "دانش آموز عزیز مشاور "
        f"{order.advisor.firstname} {order.advisor.lastname} "
        "فاکتور شما برای "
        f"{order.product.title} "
        "را تایید کرد."
    )

    await message_sender(text)
    await ctx.bot.send_message(chat_id=order.user.tel_chat_id, text=student_text)

    return ConversationHandler.END
