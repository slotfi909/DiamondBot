import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter
from telegram.constants import ParseMode
from prisma.models import User

# Constants
from src.constants import LAST_MESSAGE_KEY

# Utils
from src.utils.db import db


def send_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    last_message_id = ctx.chat_data.get(LAST_MESSAGE_KEY)

    async def send_message(text: str, reply_markup=None, edit=True, parse_mode=ParseMode.HTML):
        sent_message = None

        try:
            if edit:
                if last_message_id:
                    sent_message = await ctx.bot.edit_message_text(message_id=last_message_id, chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
                else:
                    sent_message = await ctx.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
            else:
                sent_message = await ctx.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

            ctx.chat_data[LAST_MESSAGE_KEY] = sent_message.id
        except (BadRequest, Forbidden) as ex:
            logging.error(ex.message)

        return sent_message

    return send_message


def from_student(firstname: str, lastname: str, text: str):
    return f"👩‍💻 پیام از طرف {firstname} {lastname}:\n {text}"


def bold(input: str):
    return f'<b>{input}</b>'


def italic(input: str):
    return f'<i>{input}</i>'


def linked_message(link: str, message: str):
    return f'<a href="{link}">{message}</a>'


async def from_advisor(tel_id: int, lastname: str, text: str):
    from src.utils.other import get_advisor_id

    return f"👩‍💻 پیام از طرف مشاور {await get_advisor_id(tel_id)}({lastname}):\n {text}"


async def core_message_sender(users: list[User] | list[int], message: str, ctx: ContextTypes.DEFAULT_TYPE):
    for user in users:
        while True:
            try:
                await ctx.bot.send_message(chat_id=user.tel_chat_id if isinstance(user, User) else user, text=message)
                break
            except (BadRequest, Forbidden) as ex:
                logging.error(ex)
                break
            except (NetworkError, RetryAfter) as ex:
                logging.error(ex)
                continue
            except Exception as ex:
                logging.error(ex)
                break


def send_global_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    async def global_message_sender(message: str):
        users = await db.user.find_many(where={
            "NOT": [
                {
                    "tel_id": update.effective_user.id
                }
            ]
        })

        await core_message_sender(users, message, ctx)

    return global_message_sender
