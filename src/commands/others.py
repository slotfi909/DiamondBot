import logging
import json
from datetime import timedelta
from os import path, getcwd
from asyncio import sleep
from aiofiles import os, open
from uuid import uuid4
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackContext
from telegram.constants import ParseMode

# Constants
from src.constants import (
    JOIN_CHAT_START_COMMAND,
    REFERRAL_LINK_START_COMMAND,
    START, CompleteProfileState,
    PDF_DIR_PATH,
    DATA_DIR_PATH,
    LAST_MESSAGE_KEY,
    PDFTypes
)

# Utils
from src.utils.keyboard import main_keyboard, cancel_keyboard
from src.utils.chat import get_chat, get_reciever
from src.utils.db import db
from src.utils.user import get_user
from src.utils.other import start_arg_matcher, create_matcher, get_refund_count
from src.utils.chat import join_chat
from src.utils.referral import referred_by_referral_link, create_referral_link, get_referral_count
from src.utils.message import send_message, bold, italic, linked_message

# Commands
from src.commands.support import clear_chat


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    if update.message.chat.type in ['group', 'supergroup']:
        return

    keyboard = await main_keyboard(update, ctx)

    # When a user starts the bot with a chat id the behavior is different
    if len(ctx.args) > 0:
        matcher = start_arg_matcher(update, ctx)

        should_continue = await matcher([
            create_matcher(JOIN_CHAT_START_COMMAND, join_chat),
            create_matcher(REFERRAL_LINK_START_COMMAND,
                           referred_by_referral_link)
        ])

        if not should_continue:
            return

    user = await get_user(update.effective_user.id)
    message = 'به ربات مهندس الماسیان خوش آمدید.'

    if user is None:
        message = 'برای استفاده از خدمات ربات اول باید ثبت نام کنید'

    await message_sender(text=message, reply_markup=keyboard, edit=False)


async def make_primary_group(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    if update.message.chat.type in ['private', 'channel']:
        return

    already_exists = (await db.group.find_first(
        where={
            "primary": True
        }
    )) is not None

    if already_exists:
        return await message_sender("متاسفانه گروه دیگری به عنوان گروه مشاوران انتخاب شده است.")

    chat_id = update.message.chat.id

    await db.group.update(
        where={
            'tel_group_id': chat_id
        },
        data={
            "primary": True
        }
    )

    return await message_sender("گروه به گروه مشاوران ارتقا یافت.", edit=False)


async def unmake_primary_group(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    if update.message.chat.type in ['private', 'channel']:
        return

    chat_id = update.message.chat.id

    doesnt_exists = (await db.group.find_first(
        where={
            'tel_group_id': chat_id,
            "primary": True
        }
    )) is None

    if doesnt_exists:
        return await message_sender("گروه فعلی گروه مشاوران نمی باشد.")

    await db.group.update(
        where={
            "tel_group_id": chat_id
        },
        data={
            "primary": False
        }
    )

    return await message_sender("گروه از گروه مشاوران خارج شد.", edit=False)


async def back_to_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    keyboard = await main_keyboard(update, ctx)

    await message_sender(text="🟥 " + "منوی ربات", reply_markup=keyboard)

    if "in_conversation" in ctx.user_data:
        ctx.user_data["in_conversation"] = False

    return ConversationHandler.END


async def show_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE, messsage_sender):
    text = "🟥 " + "منوی ربات"

    return await messsage_sender(text, reply_markup=await main_keyboard(update, ctx), edit=False)


async def exit_all_chats(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    chat = await get_chat(update, ctx)

    if not chat:
        await clear_chat(update, ctx)
        return await message_sender("شما در حال حاظر در هیج چت فعالی نیستید", await main_keyboard(update, ctx), edit=False)

    await db.chat.update(
        where={
            "chat_id": chat.chat_id,
            "exited_at": None
        },
        data={
            "exited_at": datetime.now()
        }
    )

    tel_chat_id = update.effective_user.id
    reciever = get_reciever(chat, tel_chat_id)

    if reciever:
        await ctx.bot.send_message(chat_id=reciever.tel_chat_id, text="طرف مقابل چن را خاتمه داد")

    await clear_chat(update, ctx)

    return await message_sender("شما از تمامی چت های فعال خود خارج شدید.", await main_keyboard(update, ctx), edit=False)


async def get_referral_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    referral_link = create_referral_link(update, ctx)

    tel_id = update.effective_user.id
    total_refellar_count = await get_referral_count(tel_id)
    tottal_refund_count = await get_refund_count(tel_id)

    text = (
        "اگه بتونی ۴ نفر رو با لینک معرفیت به ربات معرفی کنی و همشون پرداختی داشته باشن، میتونی که انتخاب رشتت رو رایگان انجام بدی "
        "🥳\n\n"
        "حتی اگه برای انتخاب رشتت هزینه پرداخت کردی میتونی یا پیام دادن به پشتیبانان مبلغ پرداخت شده رو بر گردونی، پس اگه نگرانی که ظرفیت انتخاب رشته ها پر بشه میتونی هزینش رو بدی و بعد منظر باشی که ۴ تا از دوستات روی لینک بزنن"
        "\n\n"
        "تعداد افراد معرفی شده توسط شما: "
        f"{total_refellar_count}"
        "\n\n"
        "تعداد پرداخت هایی که توسط معرفی انجام شده اند: "
        f"{tottal_refund_count}"
        "\n\n"
        "تعداد معرفی های قابل استفاده: "
        f"{total_refellar_count - (4 * tottal_refund_count)}"
        "\n\n"
        "لینک معرفی: \n"
        f"`{referral_link}`"
    )

    await message_sender(text, cancel_keyboard("BACK"), parse_mode=ParseMode.MARKDOWN)


async def about_us(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    ABOUT_US_PHOTO_ADDR = 'assets/mohsen_almasian.jpg'
    ABOUT_US_PHOTO_DESCRIPTION = f'{bold("مهندس محسن الماسیان")}\n\
     من محسن الماسیان کارشناس ارشد برنامه ریزی درسی هستم . تحصیلات دانشگاهی من در رشته مهندسی عمران - عمران دانشگاه اصفهان است و کارشناسی ارشد خود را در رشته برنامه ریزی درسی اخذ نموده ام . از سال۱۳۸۵ تا ۱۳۸۷ مشاوره و برنامه ریزی درسی و پشتیبانی دانش آموزان کنکوری را به صورت کار دانشجویی در نزد استادان خود همچون آقایان دکتر بوذری و مهندس خزایی و ... آموختم و در نهایت از تیر ۱۳۸۷ مشاوره و برنامه ریزی کنکور را آغاز نمودم .من با بررسی نیازهای دانش آموزان تلاش می کنم تا آنها را به شکلی نوین و به روز در راستای دستیابی به اهدافشان یاری نمایم'

    ABOUT_US_MESSAGE_FIRST = f'{italic("نتایج ما")}\n\
        رتبه های 3 رقمی: 🥉 637 \n\
        رتبه های 2 رقمی: 🥈 114 \n\
        رتبه های 1 رقمی: 🥇 42 \n\
            \n\
            {linked_message("https://t.me/FeedbacksOfAlmasian", " تجربه شاگرد ها✍🏻 ")}'

    ABOUT_US_MESSAGE_SECOND = ':) جهت اطلاعات بیشتر به وبسایت ما سر بزنید ℹ️ \nwww.mohsenalmasian.com'

    await ctx.bot.delete_message(chat_id=update.effective_chat.id, message_id=ctx.chat_data[LAST_MESSAGE_KEY])

    await ctx.bot.send_photo(update.effective_chat.id, photo=ABOUT_US_PHOTO_ADDR, caption=ABOUT_US_PHOTO_DESCRIPTION)
    await sleep(1)

    await ctx.bot.send_message(update.effective_chat.id, text=ABOUT_US_MESSAGE_FIRST)
    await sleep(1)

    await message_sender(ABOUT_US_MESSAGE_SECOND, await main_keyboard(update, ctx), edit=False)


async def keep_chat_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    await update.message.delete()


async def error_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    logging.error(ctx.error)

    if isinstance(update, Update):
        message_sender = send_message(update, ctx)

        await message_sender(text=f"متاسفانه مشکلی پیش اومده، اگه با /{START} درست نشد بهمون پیام بده تا مشکل رو رفع کنیم.")


async def last_resort(update: Update, ctx: CallbackContext):
    logging.info("\n\n\n\n")
    logging.info("Update: ", update.to_json())
    logging.info("bot_data: ", json.dumps(ctx.bot_data))
    logging.info("user_data: ", json.dumps(ctx.user_data))
    logging.info("chat_data: ", json.dumps(ctx.chat_data))
    logging.info("\n\n\n\n")
