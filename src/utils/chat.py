import json
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from prisma.models import Chat
from prisma.enums import UserRole

# Constants
from src.constants import CHAT_LIFETIME_HOURS

# Utils
from src.utils.user import get_user, has_active_chat
from src.utils.db import db
from src.utils.keyboard import chat_keyboard
from src.utils.time import substract_hour, to_utc
from src.utils.message import from_advisor


async def get_chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE, set_chat_message="شما وارد چت شدید"):
    chat = None

    if "chat_id" not in ctx.user_data:
        user = await get_user(update.effective_user.id)

        if user is None:
            return None

        chat = await has_active_chat(user.user_id)

        if chat is None:
            return None

        if set_chat_message:
            await ctx.bot.send_message(text=set_chat_message, chat_id=user.tel_chat_id, reply_markup=await chat_keyboard(update, ctx))

        ctx.user_data["chat_id"] = chat.chat_id
    else:
        chat = await db.chat.find_unique(
            where={
                "chat_id": ctx.user_data["chat_id"],
                "exited_at": None,
                "updated_at": {
                    "gte": to_utc(substract_hour(to_utc(datetime.now()), CHAT_LIFETIME_HOURS))
                },
            },
            include={
                "started_by": True,
                "received_by": True
            }
        )

        if chat is None:
            ctx.user_data.pop("chat_id")

    return chat


async def create_chat_message(chat_id: int, user_tel_id: int, text: str | None, photos: list | None, caption: str | None):
    async with db.tx() as tx:
        data = {
            "chat": {
                "connect": {
                    "chat_id": chat_id,
                }
            },
            "user": {
                "connect": {
                    "tel_id": user_tel_id
                }
            },
            "message": text or caption,
        }

        if photos:
            data["payload"] = json.dumps(list(map(lambda photo: {
                "photo_id": photo.file_id,
                "photo_unique_id": photo.file_unique_id,
                "photo_size": photo.file_size,
            }, photos)))

        await tx.message.create(data=data)

        await tx.chat.update(
            where={
                "chat_id": chat_id
            },
            data={
                "updated_at": datetime.now()
            }
        )


def get_reciever(chat: Chat, tel_chat_id: int):
    return chat.received_by if chat.started_by.tel_chat_id == tel_chat_id else chat.started_by


async def join_chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    tel_id = update.effective_user.id
    user = await get_user(tel_id)
    join_chat = int(ctx.user_data["matcher"]["value"])

    if user is None or user.user_role == UserRole.STUDENT:
        return

    chat = await get_chat(update, ctx)

    if chat:
        return await message_sender("شما در حال حاضر در یک مکالمه فعال هستید. ابتدا آن را ببندید.", edit=False)

    async with db.tx() as tx:
        already_occupied = await tx.chat.find_unique(where={
            "chat_id": join_chat,
            "received_by": None,
            "exited_at": None,
            "updated_at": {
                "gte": to_utc(substract_hour(to_utc(datetime.now()), CHAT_LIFETIME_HOURS))
            },
        }) is None

        if already_occupied:
            return await message_sender("متاسفانه چت توسط مشاور دیگری اشغال شده و یا مهلت آن تمام شده است.", edit=False)

        chat = await tx.chat.update(
            where={
                "chat_id": join_chat
            },
            data={
                "received_by": {
                    "connect": {
                        "tel_id": tel_id
                    }
                }
            },
            include={
                "started_by": True,
            }
        )

    ctx.user_data["chat_id"] = join_chat

    await ctx.bot.send_message(text=await from_advisor(user.tel_id, user.lastname, "چه کمکی از دست من برمیاد؟"), chat_id=chat.started_by.tel_chat_id)

    await message_sender("مشاور عزیز شما وارد مکالمه با دانش آموز شدید.\n\nدقت کنید که ربات تنها امکان انتقال پیام های متنی و عکس را دارد و در صورت ارسال موارد دیگه مثل فایل و یا GIF پیام شما نادیده گرفته می شود.", reply_markup=await chat_keyboard(update, ctx), edit=False)
