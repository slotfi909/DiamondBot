from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from prisma.enums import UserRole

from src.utils.db import db


async def is_user_registered(update: Update, ctx: ContextTypes.DEFAULT_TYPE, target_tel_id: Optional[int] = None):
    user_id = target_tel_id or update.effective_user.id

    user = await db.user.find_unique(
        where={
            'tel_id': user_id
        }
    )

    return bool(user)


async def is_advisor(update: Update, ctx: ContextTypes.DEFAULT_TYPE, target_tel_id: Optional[int] = None):
    tel_id = target_tel_id or update.effective_user.id

    user = await db.user.find_first(
        where={
            'tel_id': tel_id,
            "OR": [
                {

                    'user_role': UserRole.ADVISOR
                },
                {

                    'user_role': UserRole.ADMIN
                },
            ]
        }
    )

    return bool(user)


async def is_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE, target_tel_id: Optional[int] = None):
    tel_id = target_tel_id or update.effective_user.id

    user = await db.user.find_first(
        where={
            "tel_id": tel_id,
            "user_role": UserRole.ADMIN
        }
    )

    return bool(user)
