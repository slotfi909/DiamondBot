import logging
from datetime import datetime
from click.termui import edit
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import Forbidden, BadRequest, NetworkError

# Utils
from src.utils.keyboard import (
    admin_keyboard,
    cancel_keyboard,
    main_keyboard,
    show_users_list_keyboard,
    advisor_keyboard,
    product_list_for_message_keyboard,
    users_list_for_message_keyboard,
    product_list_keyboard_for_export,
    product_list_keyboard_for_notification
)
from src.utils.message import send_global_message, from_advisor, core_message_sender
from src.utils.other import get_user_info, build_customer_details_excel
from src.utils.db import db
from src.utils.user import get_user
from src.utils.time import convert_to_jajali

# Constants
from src.constants import (
    GlobalMessageState,
    BotMaintenanceState,
    GetStudentsState,
    BACK_TO_ADMIN_MENU,
    BACK_TO_ADVISOR_MENU,
    SendMessageToStudentState,
    ExportExcelState,
    ProductBasedNotification
)


async def show_admin_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    text = (
        "🔒 " + "پنل مدیریت"
    )

    keyboard = InlineKeyboardMarkup(
        admin_keyboard(True) + cancel_keyboard("BACK", True))

    await message_sender(text, keyboard)

    if "in_conversation" in ctx.user_data:
        ctx.user_data["in_conversation"] = False

    return ConversationHandler.END


async def ask_global_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    ctx.user_data["in_conversation"] = True

    keyboard = cancel_keyboard("BACK", callback_data=BACK_TO_ADMIN_MENU)

    await message_sender("لطفا پیام خود را بنویسید", keyboard)

    return GlobalMessageState.COLLECT_GLOBAL_MESSAGE


async def collect_global_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    message = update.message.text

    global_message_sender = send_global_message(update, ctx)

    await message_sender("در حال ارسال...", edit=False)

    await global_message_sender(message)

    keyboard = InlineKeyboardMarkup(
        admin_keyboard(True) + cancel_keyboard("BACK", True, BACK_TO_ADMIN_MENU))

    await message_sender("پیام شما با موفقیت ارسال شد", keyboard)

    if "in_conversation" in ctx.user_data:
        ctx.user_data["in_conversation"] = False

    return ConversationHandler.END


async def ask_maintenance_duration(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    ctx.user_data["in_conversation"] = True

    keyboard = cancel_keyboard("BACK", callback_data=BACK_TO_ADMIN_MENU)

    await message_sender("مدت زمان تعمیر را مشخص کنید به فرمت ۱ ساعت و یا ۳۰ دقیقه", keyboard)

    return BotMaintenanceState.COLLECT_MAINTENANCE_DURATION


async def collect_maintenance_duration(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    duration = update.message.text

    global_message_sender = send_global_message(update, ctx)

    message = (
        f"دانش آموزان عزیز، ربات تا {
            duration} دیگر در دسترس نمی باشد و به محض در دسترس قرار گرفتن مطلع خواهید شد."
    )

    await message_sender("در حال ارسال...", edit=False)

    await global_message_sender(message)

    keyboard = InlineKeyboardMarkup(
        admin_keyboard(True) + cancel_keyboard("BACK", True))

    await message_sender("پیام شما با موفقیت ارسال شد", keyboard)

    if "in_conversation" in ctx.user_data:
        ctx.user_data["in_conversation"] = False

    return ConversationHandler.END


async def show_users_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    ctx.user_data["in_conversation"] = True

    callback_data = update.callback_query.data.split(" ")

    page = int(callback_data[1]) if len(callback_data) == 2 else 1

    keyboard = InlineKeyboardMarkup(await show_users_list_keyboard(
        page, True) + cancel_keyboard("BACK", True, callback_data=BACK_TO_ADMIN_MENU))

    await message_sender(f"لیست کاربران به ترتیب عضویت:\n شماره صفحه: {page}", keyboard)

    return GetStudentsState.COLLECT_STUDENT_ID


async def collect_user_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    tel_id = int(update.callback_query.data.split(" ")[1])

    keyboard = cancel_keyboard("BACK", callback_data=BACK_TO_ADMIN_MENU)

    await message_sender(await get_user_info(tel_id), keyboard)

    if "in_conversation" in ctx.user_data:
        ctx.user_data["in_conversation"] = False

    return ConversationHandler.END


async def show_advisor_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    keyboard = InlineKeyboardMarkup(
        advisor_keyboard(True) + cancel_keyboard("BACK", True))

    await message_sender("👨‍🏫 " + "پنل مشاور", keyboard)

    return ConversationHandler.END


async def show_products_list_for_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    ctx.user_data["in_conversation"] = True

    keyboard = InlineKeyboardMarkup(
        await product_list_for_message_keyboard(True) + cancel_keyboard("BACK", True,
                                                                        callback_data=BACK_TO_ADVISOR_MENU))

    text = (
        "دانش آموزی که می خواهید برای آن پیام بفرستید کدام بسته را خریداری کرده است؟"
    )

    await message_sender(text, keyboard)

    return SendMessageToStudentState.COLLECT_PRODUCT_ID_FOR_MESSAGE


async def collect_product_id_for_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    callback_data = update.callback_query.data.split(" ")

    product_id = int(callback_data[1])

    page = int(callback_data[2]) if len(callback_data) == 3 else 1

    product = await db.product.find_unique(
        where={
            "product_id": product_id
        }
    )

    keyboard = InlineKeyboardMarkup(
        await users_list_for_message_keyboard(product_id, page, True) + cancel_keyboard("BACK", True,
                                                                                        callback_data=BACK_TO_ADVISOR_MENU))

    text = (
        f"لیست دانش‌ آموزانی که {product.title} را خریداری کرده اند"
    )

    await message_sender(text, keyboard)

    return SendMessageToStudentState.COLLECT_STUDENT_ID_FOR_MESSAGE


async def collect_student_id_for_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    callback_data = update.callback_query.data.split(" ")

    student_tel_id = int(callback_data[1])

    ctx.user_data["for_message_student_tel_id"] = student_tel_id

    student = await get_user(student_tel_id)

    keyboard = cancel_keyboard("BACK", callback_data=BACK_TO_ADVISOR_MENU)

    text = (
        f"چه پیامی می خواهید به دانش آموز {
            student.firstname} {student.lastname} بدهید؟"
    )

    await message_sender(text, keyboard)

    return SendMessageToStudentState.COLLECT_ADVISOR_MESSAGE


async def collect_advisor_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    message = update.message.text

    student_tel_id = ctx.user_data["for_message_student_tel_id"]

    student = await get_user(student_tel_id)
    advisor = await get_user(update.effective_user.id)

    keyboard = InlineKeyboardMarkup(
        advisor_keyboard(True) + cancel_keyboard("BACK", True))

    try:
        await ctx.bot.send_message(chat_id=student.tel_chat_id,
                                   text=await from_advisor(advisor.tel_id, advisor.lastname, message))

        await message_sender(f"پیام شما با موفقیت برای دانش آموز {student.firstname} {student.lastname} ارسال شد.",
                             keyboard, edit=False)
    except (Forbidden, BadRequest, NetworkError) as ex:
        logging.error(ex.message)

        await message_sender(
            f"متاسفانه پیام ارسال نشد، به احتمال زیاد دانش آموز اکانت تلگرام خود را حذف کرده است. سعی کنید دوباره امتحان کنید.",
            keyboard, edit=False)

    if "in_conversation" in ctx.user_data:
        ctx.user_data["in_conversation"] = False

    return ConversationHandler.END


async def show_product_list_for_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    ctx.user_data["in_conversation"] = True

    keyboard = InlineKeyboardMarkup(await product_list_keyboard_for_export(True) + cancel_keyboard("BACK", True, BACK_TO_ADVISOR_MENU))

    text = (
        "خروجی کدام بسته را می خواهید؟"
    )

    await message_sender(text, keyboard)

    return ExportExcelState.COLLECT_PRODUCT_ID_FOR_EXPORT


async def collect_product_id_for_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    product_id = int(update.callback_query.data.split(" ")[1])
    excel_buffer = await build_customer_details_excel(update, ctx, product_id)

    now = datetime.now()
    today_date = convert_to_jajali(now)
    product = await db.product.find_unique(where={"product_id": product_id})

    await ctx.bot.send_document(chat_id=update.effective_chat.id, document=excel_buffer,
                                filename=f"اطلاعات-مشتریان-{product.title}-{now.minute}-{now.hour}-{today_date.day}-{today_date.month}-{today_date.year}.xlsx")

    excel_buffer.close()

    keyboard = InlineKeyboardMarkup(
        advisor_keyboard(True) + cancel_keyboard("BACK", True))

    text = (
        "اطلاعات مشتریان با موفقیت ارسال شد"
    )

    await message_sender(text, keyboard, edit=False)


async def show_product_list_for_product_notification(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    keyboard = InlineKeyboardMarkup(await product_list_keyboard_for_notification(True) + cancel_keyboard("BACK", True, callback_data=BACK_TO_ADMIN_MENU))

    ctx.user_data["in_conversation"] = True

    await message_sender("برای دانش آموزان کدام بسته می خواهید پیام ارسال کنید؟", keyboard)

    return ProductBasedNotification.COLLECT_PRODUCT_ID_FOR_NOTIFICATION


async def collect_product_id_for_product_based_notification(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    product_id = int(update.callback_query.data.split(" ")[1])

    ctx.user_data["product_id"] = product_id

    keyboard = cancel_keyboard("BACK", callback_data=BACK_TO_ADMIN_MENU)

    await message_sender("پیامی که می خواهید بفرستید را ارسال کنید", keyboard)

    return ProductBasedNotification.COLLECT_NOTIFICATION_MESSAGE_FOR_PRODUCT_BASED


async def collect_notification_message_for_product_based(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    message = update.effective_message.text

    product_id = ctx.user_data["product_id"]

    query_raw = await db.query_raw("""--sql
        SELECT u.tel_chat_id
        FROM "User" AS u
            INNER JOIN "Order" AS o ON (o.user_id = u.user_id)
            INNER JOIN "Product" AS p ON (o.product_id = p.product_id)
        WHERE  p.product_id = $1
    """, product_id)

    await core_message_sender(list(map(lambda u: u["tel_chat_id"], query_raw)), message, ctx)

    await message_sender("پیام شما با موفقیت ارسال شد", await main_keyboard(update, ctx), edit=False)

    if "in_conversation" in ctx.user_data:
        ctx.user_data["in_conversation"] = False

    return ConversationHandler.END
