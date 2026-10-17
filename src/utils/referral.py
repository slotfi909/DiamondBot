from base64 import b64encode, b64decode
from telegram import Update
from telegram.ext import ContextTypes
from prisma.enums import PaymentStatus

from src.constants import REFERRAL_LINK_START_COMMAND
from src.utils.db import db
from src.utils.user import get_user


def create_referral_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    encoded_user_id = b64encode(str(update.effective_user.id).encode('utf-8'))

    return f'https://t.me/{ctx.bot.username}?start={REFERRAL_LINK_START_COMMAND}-{
        encoded_user_id.decode('utf-8')}'


async def create_referral(referrer_tel_id: int, referred_tel_id: int, tx=None):
    return await (tx or db).referral.create(
        data={
            'referrer': {
                "connect": {
                    'tel_id': referrer_tel_id
                }
            },
            "referred": {
                "connect": {
                    "tel_id": referred_tel_id
                }
            }
        },
        include={
            "referred": True,
            "referrer": True
        }
    )


async def referred_by_referral_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    referrer_tel_id = update.effective_user.id

    referrer = await get_user(referrer_tel_id)

    referred_tel_id = int(b64decode(
        ctx.user_data["matcher"]["value"]).decode('utf-8'))

    if not referrer:
        ctx.user_data["referred_tel_id"] = referred_tel_id
        return True

    referral = await create_referral(referrer_tel_id, referred_tel_id)

    text = (
        "دانش آموز عزیز لینک معرفی شما توسط "
        f"{referral.referrer.firstname} {referral.referrer.lastname} "
        "استفاده شد به محض انجام اولین پرداختی به تعداد افرادی که معرفی کرده اید اضافه می شود."
    )

    await ctx.bot.send_message(chat_id=referral.referred.tel_chat_id, text=text)

    return True


async def get_referral_count(referred_tel_id: int, tx=None):
    query_result = await (tx or db).query_raw(f"""
        WITH tmp AS (
            SELECT r.referrer_id
            FROM "Referral" AS r
                INNER JOIN "User" AS u on (r.referred_id = u.user_id)
                INNER JOIN "Order" AS o on (o.user_id = r.referrer_id)
                INNER JOIN "Payment" AS p on (p.payment_id = o.payment_id)
            where u.tel_id = $1 AND p.status = '{str(PaymentStatus.COMPLETED).upper()}'
            group by r.referrer_id
        )
        SELECT COUNT(*)
        FROM tmp
    """, referred_tel_id)

    return query_result[0]["count"]
