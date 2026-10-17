import math
from datetime import datetime
from typing import Literal, Optional
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import ContextTypes
from prisma.enums import (
    Grade,
    Field,
    PaymentStatus,
    PaymentMethod,
    UserRole
)

# Constants
from src.constants import (
    REGISTER,
    QA,
    CHOOSE_FIELD,
    REFERRAL,
    ABOUT_US,
    ADMIN,
    ADVISOR,
    BACK_TO_MENU,
    REGISTER_GRADE_PREFIX,
    REGISTER_FIELD_PREFIX,
    CREATE_FACTOR, EXIT_CHAT,
    CONFIRM_FACTOR_PREFIX,
    KeyboardActions,
    COLLECT_PRODUCT_FOR_FACTOR_PREFIX,
    CONFIRM_FACTOR,
    COLLECT_FACTOR_PREFIX,
    COLLECT_CHOOSE_FIELD_PRODUCT_PREFIX,
    ChooseFieldState,
    ADMIN_SHOW_USERS_LIST,
    ADMIN_SEND_NOTIFICATION,
    ADMIN_SEND_MAINTENANCE_NOTIFICATION,
    USER_PER_PAGE,
    ADMIN_COLLECT_STUDENT_ID_PREFIX,
    ADMIN_SHOW_USERS_LIST_CHANGE_PAGE_PREFIX,
    ADVISOR_SHOW_PRODUCTS_LIST,
    COLLECT_PRODUCT_ID_FOR_MESSAGE_PREFIX,
    COLLECT_STUDENT_ID_FOR_MESSAGE_PREFIX,
    ADVISOR_SHOW_USERS_LIST_CHANGE_PAGE_PREFIX,
    ADVISOR_EXPORT_CUSTOMER_DETAILS,
    ADVISOR_COLLECT_PRODUCT_ID_FOR_EXPORT_PREFIX,
    DIRECT_PAY_VERIFICATION_PREFIX,
    PDFTypes,
    TIR_KONKUR_COMPLETE_PROFILE,
    ORDIBEHESHT_KONKUR_COMPLETE_PROFILE,
    CHOOSE_FIELD_BIAS_COMPLETE_PROFILE,
    KHORDAD_GRADES_COMPLETE_PROFILE,
    PENDING_ORDER_LIFETIME_MINUTES,
    ADVISOR_GET_STUDENT_PDF,
    TIR_KONKUR_RETRIEVE_PDF,
    ORDIBEHESHT_KONKUR_RETRIEVE_PDF,
    CHOOSE_FIELD_BIAS_RETRIEVE_PDF,
    KHORDAD_GRADES_RETRIEVE_PDF,
    ADMIN_SEND_PRODUCT_BASED_NOTIFICATION,
    ADMIN_SEND_PRODUCT_BASED_NOTIFICATION_PREFIX,
)

# Utils
from src.utils.role import (
    is_user_registered,
    is_admin,
    is_advisor
)
from src.utils.db import db
from src.utils.other import (
    compact_price,
    to_utc
)
from src.utils.time import substract_minutes


async def main_keyboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE, exclude: list[KeyboardActions] = [],
                        array_form=False, target_tel_id: Optional[int] = None):
    keyboard_actions = {
        KeyboardActions.REGISTER: [InlineKeyboardButton("➕ " + "ثبت نام", callback_data=REGISTER)],
        KeyboardActions.QA: [InlineKeyboardButton("❓ " + "ارتباط با پشتیبان", callback_data=QA)],
        KeyboardActions.CHOOSE_FIELD: [InlineKeyboardButton("📚 " + "انتخاب رشته", callback_data=CHOOSE_FIELD)],
        KeyboardActions.REFERRAL: [InlineKeyboardButton("👥 " + "دریافت لینک معرفی", callback_data=REFERRAL)],
        KeyboardActions.ABOUT_US: [InlineKeyboardButton("📝 " + "درباره ما", callback_data=ABOUT_US)],
        KeyboardActions.ADMIN: [InlineKeyboardButton("🔒 " + "پنل مدیریت", callback_data=ADMIN)],
        KeyboardActions.ADVISOR: [InlineKeyboardButton("👨‍🏫 " + "پنل مشاور", callback_data=ADVISOR)],
    }

    keyboard = []

    registered = await is_user_registered(update, ctx, target_tel_id)
    admin = await is_admin(update, ctx, target_tel_id)
    advisor = await is_advisor(update, ctx, target_tel_id)

    if not registered:
        keyboard.append(keyboard_actions[KeyboardActions.REGISTER])

        return InlineKeyboardMarkup(keyboard) if not array_form else keyboard

    for action, button in keyboard_actions.items():
        if action in exclude or (not admin and action == KeyboardActions.ADMIN) or (
                not advisor and action == KeyboardActions.ADVISOR) or action == KeyboardActions.REGISTER:
            continue

        keyboard.append(button)

    return InlineKeyboardMarkup(keyboard) if not array_form else keyboard


def cancel_keyboard(type: Literal["CANCEL", "BACK"], array_form=False, callback_data=BACK_TO_MENU):
    keyboard = []

    match type:
        case "CANCEL":
            keyboard.append([InlineKeyboardButton(
                "❌ " + "کنسل", callback_data=BACK_TO_MENU)])
        case "BACK":
            keyboard.append([InlineKeyboardButton(
                "🔙 " + "بازگشت به منو", callback_data=callback_data)])

    return InlineKeyboardMarkup(keyboard) if not array_form else keyboard


def grade_keyboard(array_form=False):
    keyboard = [
        [InlineKeyboardButton(
            "دهم", callback_data=REGISTER_GRADE_PREFIX + " " + Grade.TENTH)],
        [InlineKeyboardButton(
            "یازدهم", callback_data=REGISTER_GRADE_PREFIX + " " + Grade.ELEVENTH)],
        [InlineKeyboardButton(
            "دوازدهم", callback_data=REGISTER_GRADE_PREFIX + " " + Grade.TWELVTH)],
        [InlineKeyboardButton(
            "پشت کنکوری", callback_data=REGISTER_GRADE_PREFIX + " " + Grade.DIPLOMA)],
    ]

    return InlineKeyboardMarkup(keyboard) if not array_form else keyboard


def field_keyboard(array_form=False):
    keyboard = [
        [InlineKeyboardButton(
            "ریاضی", callback_data=REGISTER_FIELD_PREFIX + " " + Field.MATH)],
        [InlineKeyboardButton(
            "تجربی", callback_data=REGISTER_FIELD_PREFIX + " " + Field.MEDICAL)],
        [InlineKeyboardButton(
            "انسانی", callback_data=REGISTER_FIELD_PREFIX + " " + Field.MEDICAL)],
    ]

    return InlineKeyboardMarkup(keyboard) if not array_form else keyboard


async def chat_keyboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard_actions = [
        [CREATE_FACTOR],
        [CONFIRM_FACTOR],
        [EXIT_CHAT]
    ]

    advisor = await is_advisor(update, ctx)

    if not advisor:
        return ReplyKeyboardMarkup([keyboard_actions[-1]])

    return ReplyKeyboardMarkup(keyboard_actions)


async def create_factor_keyboard(array_form=False):
    products = await db.product.find_many(where={
        "deleted_at": None
    })

    keyboard = list(map(lambda p: [InlineKeyboardButton(
        p.title, callback_data=COLLECT_PRODUCT_FOR_FACTOR_PREFIX + " " + str(p.product_id))], products))

    return InlineKeyboardMarkup(keyboard) if not array_form else keyboard


async def confirm_factor_keyboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE, array_form=False):
    from src.utils.chat import get_chat, get_reciever

    chat = await get_chat(update, ctx)

    student = get_reciever(chat, update.effective_user.id)

    orders = await db.order.find_many(
        where={
            "user_id": student.user_id,
            "payment": {
                "status": PaymentStatus.PENDING,
                "method": PaymentMethod.MANUAL
            },
            "created_at": {
                'gte': to_utc(substract_minutes(to_utc(datetime.now()), PENDING_ORDER_LIFETIME_MINUTES))
            }
        },
        order={
            "created_at": "desc"
        },
        include={
            "product": True
        }
    )

    print("\n\n\n", orders, )

    keyboard = list(map(lambda o: [InlineKeyboardButton(
        f"فاکتور برای {o.product.title}", callback_data=COLLECT_FACTOR_PREFIX + " " + str(o.order_id))], orders))

    return InlineKeyboardMarkup(keyboard) if not array_form else keyboard


async def choose_field_keyboard(array_form=False):
    products = await db.product.find_many(where={
        "deleted_at": None
    })

    keyboard = list(map(lambda p: [InlineKeyboardButton(
        f"{p.title} {compact_price(p.price)}",
        callback_data=COLLECT_CHOOSE_FIELD_PRODUCT_PREFIX + " " + str(p.product_id))], products))

    return InlineKeyboardMarkup(keyboard) if not array_form else keyboard


def payment_options_keyboard(array_form=False):
    keyboard = [
        # [InlineKeyboardButton("پرداخت مستقیم از طریق درگاه",
        #                       callback_data=str(ChooseFieldState.PAY_DIRECTLY))],
        [InlineKeyboardButton("ارتباط با پشتیبان برای پرداخت",
                              callback_data=str(ChooseFieldState.PAY_VIA_OPERATOR))],
        [InlineKeyboardButton("پرداخت با دعوت از دوستان",
                              callback_data=str(ChooseFieldState.PAY_BY_REFERRAL))],
    ]

    return InlineKeyboardMarkup([keyboard]) if not array_form else keyboard


def admin_keyboard(array_form=False):
    keyboard = [
        [InlineKeyboardButton("📋 نمایش لیست کاربران",
                              callback_data=ADMIN_SHOW_USERS_LIST)],
        [InlineKeyboardButton("🚨 ارسال پیام همگانی",
                              callback_data=ADMIN_SEND_NOTIFICATION)],
        [InlineKeyboardButton(
            "🛠️ ارسال پیام تعمیر ربات", callback_data=ADMIN_SEND_MAINTENANCE_NOTIFICATION)],
        [InlineKeyboardButton("📚 ارسال پیام همگانی برای بسته انتخاب رشته",
                              callback_data=ADMIN_SEND_PRODUCT_BASED_NOTIFICATION)],
    ]

    return InlineKeyboardMarkup([keyboard]) if not array_form else keyboard


async def show_users_list_keyboard(page: int, array_form=False):
    where = {
        "AND": [
            {
                "NOT": [
                    {
                        "user_role": UserRole.ADVISOR
                    }
                ]
            },
            {
                "NOT": [
                    {
                        "user_role": UserRole.ADMIN
                    }
                ]
            },
        ]
    }

    users = await db.user.find_many(
        where=where,
        take=USER_PER_PAGE,
        skip=(page - 1) * USER_PER_PAGE,
        order={
            "created_at": "desc"
        }
    )

    total_pages_count = math.ceil((await db.user.count(where=where)) / USER_PER_PAGE)

    keyboard = []

    for user in users:
        keyboard.append([InlineKeyboardButton(
            f"{user.user_id}- {user.firstname} {user.lastname}",
            callback_data=ADMIN_COLLECT_STUDENT_ID_PREFIX + " " + str(user.tel_id))])

    if page < total_pages_count:
        keyboard.append([InlineKeyboardButton(
            "⏭️ صفحه بعدی", callback_data=ADMIN_SHOW_USERS_LIST_CHANGE_PAGE_PREFIX + " " + str(page + 1))])

    if page != 1:
        keyboard.append([InlineKeyboardButton(
            "⏮️ صفحه قبلی", callback_data=ADMIN_SHOW_USERS_LIST_CHANGE_PAGE_PREFIX + " " + str(page - 1))])

    return InlineKeyboardMarkup(keyboard) if not array_form else keyboard


def advisor_keyboard(array_form=False):
    keyboard = [
        [InlineKeyboardButton("📦 ارسال پیام به دانش آموزان",
                              callback_data=ADVISOR_SHOW_PRODUCTS_LIST)],
        [InlineKeyboardButton("💾 خروجی اطلاعات مشتریان",
                              callback_data=ADVISOR_EXPORT_CUSTOMER_DETAILS)],
        [InlineKeyboardButton("📕 دریافت اطلاعات دانش آموزان به صورت PDF",
                              callback_data=ADVISOR_GET_STUDENT_PDF)]
    ]

    return InlineKeyboardMarkup(keyboard) if not array_form else keyboard


async def product_list_for_message_keyboard(array_form=False):
    products = await db.product.find_many(where={
        "deleted_at": None
    })

    keyboard = []

    for product in products:
        keyboard.append([InlineKeyboardButton(
            product.title, callback_data=COLLECT_PRODUCT_ID_FOR_MESSAGE_PREFIX + " " + str(product.product_id))])

    return InlineKeyboardMarkup(keyboard) if not array_form else keyboard


async def users_list_for_message_keyboard(product_id: int, page: int, array_form=False):
    count_result = await db.query_raw(f"""--sql
        WITH tmp as (
                    SELECT u.user_id AS user_id
                    FROM "User" AS u
                        INNER JOIN "Order" AS o ON (o.user_id = u.user_id)
                    WHERE user_role = '{str(UserRole.STUDENT).upper()}' AND o.product_id = $1
                    GROUP BY u.user_id
        )
        SELECT COUNT(*)
        FROM tmp
    """, product_id)

    count = count_result[0]["count"]

    users = await db.query_raw(f"""--sql
      SELECT u.user_id AS user_id, MAX(u.firstname) AS firstname, MAX(u.lastname) AS lastname, MAX(u.tel_id) as tel_id
      FROM "User" AS u
        INNER JOIN "Order" AS o ON (o.user_id = u.user_id)
      WHERE user_role = '{str(UserRole.STUDENT).upper()}' AND o.product_id = $1
      GROUP BY u.user_id
      ORDER BY MAX(u.created_at)
      LIMIT $2 OFFSET $3
    """, product_id, USER_PER_PAGE, (page - 1) * USER_PER_PAGE)

    keyboard = []

    total_pages_count = math.ceil(count / USER_PER_PAGE)

    for user in users:
        keyboard.append([InlineKeyboardButton(
            f"{user["user_id"]}-{user["firstname"]} {user["lastname"]}",
            callback_data=COLLECT_STUDENT_ID_FOR_MESSAGE_PREFIX + " " + str(user["tel_id"]))])

    if page < total_pages_count:
        keyboard.append([InlineKeyboardButton(
            "⏭️ صفحه بعدی",
            callback_data=ADVISOR_SHOW_USERS_LIST_CHANGE_PAGE_PREFIX + " " + str(product_id) + " " + str(page + 1))])

    if page != 1:
        keyboard.append([InlineKeyboardButton(
            "⏮️ صفحه قبلی",
            callback_data=ADVISOR_SHOW_USERS_LIST_CHANGE_PAGE_PREFIX + " " + str(product_id) + " " + str(page - 1))])

    return InlineKeyboardMarkup(keyboard) if not array_form else keyboard


async def product_list_keyboard_for_export(array_form=False):
    products = await db.product.find_many(where={
        "deleted_at": None
    })

    keyboard = []

    for product in products:
        keyboard.append([InlineKeyboardButton(
            product.title, callback_data=ADVISOR_COLLECT_PRODUCT_ID_FOR_EXPORT_PREFIX + " " + str(product.product_id))])

    return InlineKeyboardMarkup(keyboard) if not array_form else keyboard


def direct_pay_keyboard(payment_link: str, order_id: int, array_form=False):
    keyboard = [
        [InlineKeyboardButton(
            "🔗 " + "ورود به درگاه پرداخت", url=payment_link)],
        [InlineKeyboardButton(
            "✅ " + "تایید پرداخت", callback_data=DIRECT_PAY_VERIFICATION_PREFIX + " " + str(order_id))]
    ]

    return InlineKeyboardMarkup(keyboard) if not array_form else keyboard


def complete_profile_keyboard(array_form=False):
    keyboard = [
        [InlineKeyboardButton(
            "نتیجه کنکور تیر ماه", callback_data=TIR_KONKUR_COMPLETE_PROFILE)],
        [InlineKeyboardButton(
            "نتیجه کنکور اردیبهشت ماه", callback_data=ORDIBEHESHT_KONKUR_COMPLETE_PROFILE)],
        [InlineKeyboardButton(
            "کارنامه ملاک انتخاب رشته", callback_data=CHOOSE_FIELD_BIAS_COMPLETE_PROFILE)],
        [InlineKeyboardButton(
            "کارنامه نمرات خرداد ماه", callback_data=KHORDAD_GRADES_COMPLETE_PROFILE)]
    ]

    return InlineKeyboardMarkup(keyboard) if not array_form else keyboard


def retrieve_pdf_keyboard(array_form=False):
    keyboard = [
        [InlineKeyboardButton(
            "نتیجه کنکور تیر ماه", callback_data=TIR_KONKUR_RETRIEVE_PDF)],
        [InlineKeyboardButton(
            "نتیجه کنکور اردیبهشت ماه", callback_data=ORDIBEHESHT_KONKUR_RETRIEVE_PDF)],
        [InlineKeyboardButton(
            "کارنامه ملاک انتخاب رشته", callback_data=CHOOSE_FIELD_BIAS_RETRIEVE_PDF)],
        [InlineKeyboardButton(
            "کارنامه نمرات خرداد ماه", callback_data=KHORDAD_GRADES_RETRIEVE_PDF)]
    ]

    return InlineKeyboardMarkup(keyboard) if not array_form else keyboard


async def product_list_keyboard_for_notification(array_form=False):
    products = await db.product.find_many(where={
        "deleted_at": None
    })

    keyboard = []

    for product in products:
        keyboard.append([InlineKeyboardButton(
            product.title, callback_data=ADMIN_SEND_PRODUCT_BASED_NOTIFICATION_PREFIX + " " + str(product.product_id))])


    return InlineKeyboardMarkup(keyboard) if not array_form else keyboard
