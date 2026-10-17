from telegram import Update
from telegram.ext import ContextTypes

from src.utils.role import is_user_registered, is_advisor, is_admin
from src.utils.message import send_message
from src.utils.keyboard import main_keyboard
from src.utils.chat import get_chat


async def ignore_none_registered(update: Update, ctx: ContextTypes.DEFAULT_TYPE, with_message=True):
    is_registered = await is_user_registered(update, ctx)
    message_sender = send_message(update, ctx)

    if not is_registered and with_message:
        await message_sender(text="برای استفاده از این امکان باید ثبت نام کنی.", reply_markup=await main_keyboard(update, ctx))

    return not is_registered


async def ignore_none_advisor(update: Update, ctx: ContextTypes.DEFAULT_TYPE, with_message=True):
    advisor = await is_advisor(update, ctx)
    message_sender = send_message(update, ctx)

    if not advisor:
        await message_sender(text="به بخش مشاور ها دسترسی نداری", reply_markup=await main_keyboard(update, ctx))

    return not advisor


async def ignore_none_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE, with_message=True):
    admin = await is_admin(update, ctx)
    message_sender = send_message(update, ctx)

    if not admin:
        await message_sender(text="به بخش ادمین ها دسترسی نداری", reply_markup=await main_keyboard(update, ctx))

    return not admin


async def ignore_while_in_chat(update: Update, ctx: ContextTypes):
    chat = await get_chat(update, ctx)
    message_sender = send_message(update, ctx)

    if chat:
        await message_sender(text="شما در حال حاضر داخل یک چت فعال هستید، ابتدا باید از آن خارج شوید.", edit=False)

    return chat


async def ignore_while_not_in_chat(update: Update, ctx: ContextTypes):
    chat = await get_chat(update, ctx)
    message_sender = send_message(update, ctx)

    if not chat:
        await message_sender(text="فقط موقعی که توی چت هستی میتونی به این قابلیت دسترسی داشته باشی", reply_markup=await main_keyboard(update, ctx), edit=False)

    return not chat
