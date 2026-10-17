import json
from uuid import uuid4
from os import path, getcwd
from aiofiles import os, open
from datetime import timedelta
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

# Utils
from src.utils.keyboard import (
    main_keyboard,
    complete_profile_keyboard,
    cancel_keyboard,
    retrieve_pdf_keyboard
)
from src.utils.matchers import national_code_matcher
from src.utils.db import db

# Constants
from src.constants import (
    CompleteProfileState,
    PDFTypes,
    DATA_DIR_PATH,
    PDF_DIR_PATH,
    RetrieveProfileState
)


async def complete_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    ctx.user_data["in_conversation"] = True

    tel_id = update.effective_user.id

    user_orders = await db.query_raw("""
        SELECT COUNT(*)
        FROM "User" AS u
        INNER JOIN "Order" AS o ON (o.user_id = u.user_id)
        WHERE u.tel_id = $1
    """, tel_id)

    keyboard = await main_keyboard(update, ctx)

    if not user_orders[0]["count"]:
        await message_sender("متاسفانه این قابلیت برای شما فعال نمی باشد.", keyboard, edit=False)

        if "in_conversation" in ctx.user_data:
            ctx.user_data["in_conversation"] = False

        return ConversationHandler.END

    keyboard = InlineKeyboardMarkup(
        complete_profile_keyboard(True) + cancel_keyboard("BACK", True))

    await message_sender("شما ملزم به ارسال ۴ نوع PDF هستید که زیر لیست شده اند برای ارسال هر کدام که مایل بودید بر روی دکمه آن بزنید. \n دقت کنید که بدون تکمیل تمامی موارد پایین انتخاب رشته شما ناقص می باشد و مسئولیت تمام آن با خود شماست.", keyboard, edit=False)

    return CompleteProfileState.COLLECT_PDF_FOR_PROFILE


async def complete_tir_konkur(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    keyboard = cancel_keyboard("BACK")

    await message_sender("PDF ای ارسال کن که حاوی اطلاعات کنکور تیر ماه باشه", keyboard)

    return CompleteProfileState.COMPLETE_TIR_KONKUR


async def complete_ordibehesht_konkur(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    keyboard = cancel_keyboard("BACK")

    await message_sender("PDF ای ارسال کن که حاوی اطلاعات کنکور تیر اردیبهشت باشه", keyboard)

    return CompleteProfileState.COMPLETE_ORDIBEHESHT_KONKUR


async def complete_choose_field_bias(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    keyboard = cancel_keyboard("BACK")

    await message_sender("PDF ای ارسال کن که حاوی اطلاعات کارنامه ملاک انتخاب رشته باشه باشه", keyboard)

    return CompleteProfileState.COMPLETE_CHOOSE_FIELD_BIAS


async def complete_khordad_grades(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    keyboard = cancel_keyboard("BACK")

    await message_sender("PDF ای ارسال کن که حاوی اطلاعات کارنامه نمرات خرداد ماه باشه باشه", keyboard)

    return CompleteProfileState.COMPLETE_KHORDAD_GRADES


def collect_pdf_for_profile_generator(pdf_type: PDFTypes):
    async def collect_pdf_for_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
        pdf_document = update.message.document
        tel_id = update.effective_user.id
        pdf_path = path.join(getcwd(), DATA_DIR_PATH,
                             PDF_DIR_PATH, str(pdf_type.value))

        if not path.isdir(pdf_path):
            await os.mkdir(pdf_path)

        payload = {
            "pdf_type": str(pdf_type.value),
        }

        async with db.tx(timeout=timedelta(milliseconds=10000)) as tx:
            pdf_file = await ctx.bot.get_file(pdf_document.file_id)

            user = await tx.user.find_unique(where={
                "tel_id": tel_id
            })

            uploads = await tx.query_raw(f"""
                SELECT u.user_id as user_id,
                    u.tel_id as tel_id,
                    u.national_code AS national_code,
                    up.upload_id as upload_id,
                    up.uploaded_file_name as uploaded_file_name
                FROM "User" AS u
                    INNER JOIN "Upload" AS up ON (u.user_id = up.user_id)
                WHERE u.user_id = $1 AND up.payload IS NOT NULL  AND (up.payload->> 'pdf_type')::TEXT = '{str(pdf_type.value).upper()}'
            """, user.user_id)

            file_name = f"{user.national_code}-{uuid4()}.pdf"
            file_path = path.join(pdf_path, file_name)

            should_edit = len(uploads) > 0

            if should_edit and await os.path.exists(exists_path := path.join(pdf_path, uploads[0]["uploaded_file_name"])):
                await os.unlink(path=exists_path)

            if should_edit:
                await tx.upload.update(
                    where={
                        "upload_id": uploads[0]["upload_id"]
                    },
                    data={
                        "uploaded_file_name": file_name
                    }
                )
            else:
                await tx.upload.create(
                    data={
                        "user": {
                            "connect": {
                                "tel_id": tel_id
                            }
                        },
                        "uploaded_file_name": file_name,
                        "payload": json.dumps(payload)
                    })

            await pdf_file.download_to_drive(custom_path=file_path)

            await message_sender("فایل PDF شما با موفقیت دریافت و ذخیره شد.", await main_keyboard(update, ctx), edit=False)

            if "in_conversation" in ctx.user_data:
                ctx.user_data["in_conversation"] = False

            return ConversationHandler.END

    return collect_pdf_for_profile


async def retrieve_pdf(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    ctx.user_data["in_conversation"] = True

    keyboard = InlineKeyboardMarkup(
        retrieve_pdf_keyboard(True) + cancel_keyboard("BACK", True))

    await message_sender("کدام نوع PDF را می خواهید دریافت کنید؟", keyboard)

    return RetrieveProfileState.COLLECT_NATIONAL_CODE


async def retrieve_tir_konkur(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    keyboard = cancel_keyboard("BACK")

    await message_sender("کد ملی دانش آموز مورد نظر را وارد کنید تا PDF کنکور تیر را دریافت کنید.", keyboard)

    return RetrieveProfileState.RETRIEVE_TIR_KONKUR


async def retrieve_ordibehesht_konkur(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    keyboard = cancel_keyboard("BACK")

    await message_sender("کد ملی دانش آموز مورد نظر را وارد کنید تا PDF کنکور اردیبهشت را دریافت کنید.", keyboard)

    return RetrieveProfileState.RETRIEVE_ORDIBEHESHT_KONKUR


async def retrieve_choose_field_bias(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    keyboard = cancel_keyboard("BACK")

    await message_sender("کد ملی دانش آموز مورد نظر را وارد کنید تا PDF کارنامه ملاک انتخاب رشته را دریافت کنید.", keyboard)

    return RetrieveProfileState.RETRIEVE_CHOOSE_FIELD_BIAS


async def retrieve_khordad_grades(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    keyboard = cancel_keyboard("BACK")

    await message_sender("کد ملی دانش آموز مورد نظر را وارد کنید تا PDF نمرات خرداد ماه را دریافت کنید.", keyboard)

    return RetrieveProfileState.RETRIEVE_KHORDAD_GRADES


def retrieve_pdf_generator(pdf_type: PDFTypes):
    async def retrieve_pdf(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
        national_code = update.effective_message.text

        keyboard = cancel_keyboard("BACK")

        if not national_code and not national_code_matcher(national_code):
            await message_sender("کد ملی معتبر نمی باشد", keyboard)
            return

        query_result = await db.query_raw(sth := f"""--sql
            SELECT up.uploaded_file_name AS uploaded_file_name
            FROM "User" AS u
                INNER JOIN "Upload" AS up ON (u.user_id = up.user_id)
            WHERE u.national_code = $1 AND (up.payload->> 'pdf_type')::TEXT = '{str(pdf_type.value).upper()}'
        """, national_code)

        if len(query_result) == 0:
            await message_sender("متاسفانه دانش آموز PDF آپلود نکرده است و یا کد ملی دانش آموز ثبت شده ای نمی باشد.", keyboard)
            return

        pdf_file_path = path.join(getcwd(), DATA_DIR_PATH, PDF_DIR_PATH, str(pdf_type.value), query_result[0]["uploaded_file_name"])

        keyboard = await main_keyboard(update, ctx)

        if not await os.path.isfile(pdf_file_path):
            await message_sender("متاسفانه فایل PDF یافت نشد.", keyboard)
            return

        async with open(pdf_file_path, "rb") as pdf_file:
            await ctx.bot.send_document(chat_id=update.effective_chat.id, document=await pdf_file.read(), filename=query_result[0]["uploaded_file_name"])

            await message_sender("فایل شما با موفقیت ارسال شد.", keyboard)

            if "in_conversation" in ctx.user_data:
                ctx.user_data["in_conversation"] = False

            return ConversationHandler.END


    return retrieve_pdf
