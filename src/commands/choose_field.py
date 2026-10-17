import logging
from datetime import datetime, timedelta
from telegram import (
    Update,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler
)
from prisma.enums import PaymentMethod, PaymentStatus

# Constants
from src.constants import ChooseFieldState, PENDING_ORDER_LIFETIME_MINUTES

# Utils
from src.utils.keyboard import (
    main_keyboard,
    cancel_keyboard,
    choose_field_keyboard,
    payment_options_keyboard,
    direct_pay_keyboard
)
from src.utils.referral import (
    get_referral_count
)
from src.utils.other import (
    get_refund_count,
    create_order,
    zarinpal,
    to_rial
)
from src.utils.db import db
from src.payment.zarinpal.errors import RPCError
from src.utils.time import to_utc, substract_minutes, set_timeout
from src.utils.message import bold, linked_message

# Commands
from src.commands.support import create_request_advisor

async def choose_field_intro(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    ctx.user_data["in_conversation"] = True

    text = (
        "بسته های زیر، بسته های انتخاب رشته موجود هستند که اسم هر بسته همراه با قیمت کنار آن نوشته شده است."
        "\n"
        "(قیمت ها به تومان می باشد)"
        "\n\n"
        f"{linked_message("https://t.me/DiamonDInfos/48","برای آشنایی با هر کدوم از بسته ها میتونید اینجا کلیک کنید..")}"
    )

    keyboard = InlineKeyboardMarkup(await choose_field_keyboard(True) + cancel_keyboard("BACK", True))

    await message_sender(text, keyboard)

    return ChooseFieldState.COLLECT_CHOOSE_FIELD_PRODUCT


async def collect_choose_field_product(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    product_id = int(update.callback_query.data.split(" ")[1])

    ctx.user_data["choose_field_product_id"] = product_id

    product = await db.product.find_unique(
        where={
            "product_id": product_id
        }
    )

    text = (
        "لطفا یکی از روش های پرداخت زیر را برای پرداخت "
        f"{product.title} "
        "انتخاب کنی: "
    )

    keyboard = InlineKeyboardMarkup(payment_options_keyboard(
        True) + cancel_keyboard("CANCEL", True))

    await message_sender(text, keyboard)

    return ChooseFieldState.SHOW_PAYMENT_OPTIONS


async def clear_payment_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender, sent_message):
    keyboard = await main_keyboard(update, ctx)

    await ctx.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=sent_message.id, text="مهلت پرداخت تمام شد.", reply_markup=keyboard)


async def pay_directly(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    tel_id = update.effective_user.id
    product_id = ctx.user_data["choose_field_product_id"]

    async with db.tx() as tx:
        product, order, created_successfully = await create_order(product_id=product_id, target_user_tel_id=tel_id, payment_method=PaymentMethod.GATE, outter_tx=tx)

        if not created_successfully:
            keyboard = InlineKeyboardMarkup(await choose_field_keyboard(True) + cancel_keyboard("BACK", True))

            await message_sender("متاسفانه ظرفیت بسته انتخاب شده پر شده است 😔، بسته دیگری انتخاب کنید.۰", keyboard)

            return ChooseFieldState.COLLECT_CHOOSE_FIELD_PRODUCT

        try:
            gate_request_result = await zarinpal.request(
                amount=to_rial(order.payment.amount),
                description=f"خرید {product.title}",
                callback_url=f"https://t.me/{ctx.bot.username}"
            )

            logging.info("\n\n\n\n\n")
            logging.info("gate results: \n\n")
            logging.info(gate_request_result)
            logging.info("\n\n\n\n\n")

            await tx.payment.update(
                where={
                    "payment_id": order.payment.payment_id
                },
                data={
                    "authority": gate_request_result["authority"]
                }
            )

            text = (
                "فاکتور شما برای خرید "
                f"{product.title} "
                "ساخته شد، برای تکمیل فرآیند خرید بر روی دکمه ورود به درگاه بزنید و پس از پرداخت بر روی دکمه تایید پرداخت بزنید تا فاکتور شما تایید شود"
                "\n\n"
                "دقت کنید که لینک پرداخت تا 20 دقیقه بیشتر معتبر نمی باشد و پرداخت پس از این مدت عودت داده می شود."
            )

            keyboard = InlineKeyboardMarkup(direct_pay_keyboard(
                gate_request_result.payment_gateway_url, order.order_id, True) + cancel_keyboard("CANCEL", True))

            sent_message = await message_sender(text, keyboard)

            async def set_time():
                await clear_payment_link(update, ctx, message_sender, sent_message)

            set_timeout(set_time, PENDING_ORDER_LIFETIME_MINUTES * 60 * 1000)

            return ChooseFieldState.CONFIRM_DIRECT_PAYMENT

        except RPCError as ex:
            keyboard = InlineKeyboardMarkup(payment_options_keyboard(
                True) + cancel_keyboard("CANCEL", True))

            await message_sender(f"متاسفانه مشکلی در پرداخت به وجود آمده است 😔، \n پیام زرین پال: {ex.get_error(ex.code)["fa"]}", keyboard)

            await tx.payment.update(where={
                "payment_id": order.payment.payment_id
            }, data={
                "status": PaymentStatus.CANCELED,
            })

            return ChooseFieldState.SHOW_PAYMENT_OPTIONS


async def pay_via_operator(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    product = await db.product.find_unique(where={
        "product_id": ctx.user_data["choose_field_product_id"]
    })
    request_advisor = create_request_advisor(
        f"ورود به مکالمه برای خرید {product.title}", lambda user: f"دانش آموز {user.firstname} {user.lastname} قصد خرید {product.title} را دارد و برای پرداخت درخواست ارتباط با پستیبان را دارد، بر روی دکمه زیر بزنید تا وارد مکالمه با او شوید.")

    await request_advisor(update, ctx, message_sender)

    if "in_conversation" in ctx.user_data:
        ctx.user_data["in_conversation"] = False

    return ConversationHandler.END


async def pay_by_referral(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    tel_id = update.effective_user.id
    product_id = ctx.user_data["choose_field_product_id"]

    keyboard = await main_keyboard(update, ctx)

    async with db.tx() as tx:
        total_referral_count = await get_referral_count(tel_id, tx)
        refund_count = await get_refund_count(tel_id, tx)

        total_referral_available = total_referral_count - (4 * refund_count)

        if total_referral_available < 4:
            await message_sender("متاسفانه شما به تعداد کافی از دوستان خود را معرفی نکرده اید 😔 برای مشاهده اطلاعات بیشتر به منوی دعوت از دوستان مراجعه کنید.", keyboard)

            if "in_conversation" in ctx.user_data:
                ctx.user_data["in_conversation"] = False

            return ConversationHandler.END

        _, _, created_successfully = await create_order(product_id=product_id, target_user_tel_id=tel_id, payment_method=PaymentMethod.REFERRAL, payment_status=PaymentStatus.COMPLETED, refunded_at=datetime.now(), outter_tx=tx)

        if not created_successfully:
            await message_sender("متاسفانه ظرفیت بسته انتخاب شده پر شده است 😔", keyboard)

            if "in_conversation" in ctx.user_data:
                ctx.user_data["in_conversation"] = False

            return ConversationHandler.END

    await message_sender("پرداخت شما با موفقیت انجام شد 🎉"
                         "\n\n"
                         f'{bold("کارشناس هامون تا یکم دیگه باهاتون در ارتباط قرار میگیرن و مراحل بعدی رو بهتون میگن..")}', keyboard)

    if "in_conversation" in ctx.user_data:
        ctx.user_data["in_conversation"] = False

    return ConversationHandler.END


async def confirm_direct_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    order_id = int(update.callback_query.data.split(" ")[1])

    order = await db.order.find_unique(where={
        "order_id": order_id
    }, include={"payment": True})

    try:
        async with db.tx(timeout=timedelta(milliseconds=6000)) as tx:
            verify_result = await zarinpal.verify(
                amount=to_rial(order.payment.amount),
                authority=order.payment.authority
            )

            keyboard = await main_keyboard(update, ctx)

            payment = await tx.payment.find_first(where={
                "payment_id": order.payment.payment_id,
                'created_at': {
                    'gte': to_utc(substract_minutes(to_utc(datetime.now()), PENDING_ORDER_LIFETIME_MINUTES))
                }
            })

            if not payment:
                await message_sender("متاسفانه پرداخت شما خارج از زمان رزرو شده بود و تراکنش تایید نشد.\n اگر وجه برای شما تا 72 ساعت عودت داده نشده است به مشاوران ما پیام بدهید.", keyboard)

                if "in_conversation" in ctx.user_data:
                    ctx.user_data["in_conversation"] = False

                return ConversationHandler.END

            await tx.payment.update(where={
                "payment_id": payment.payment_id,
            }, data={
                "status": PaymentStatus.COMPLETED
            })

            await message_sender("پرداخت شما با موفقیت انجام شد 🎉", keyboard)

            if "in_conversation" in ctx.user_data:
                ctx.user_data["in_conversation"] = False

            return ConversationHandler.END

    except RPCError as ex:
        keyboard = InlineKeyboardMarkup(direct_pay_keyboard(
            zarinpal.create_payment_gateway_url(order.payment.authority), order_id, True) + cancel_keyboard("CANCEL", True))

        await message_sender(f"متاسفانه پرداخت شما تایید نشد.\n پیام زرین پال {ex.get_error(ex.code)["fa"]}", keyboard)

        return ChooseFieldState.CONFIRM_DIRECT_PAYMENT
