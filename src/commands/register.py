import jdatetime
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

# Constants
from src.constants import RegisterStates

# Utils
from src.utils.role import is_user_registered
from src.utils.keyboard import main_keyboard, cancel_keyboard, grade_keyboard, field_keyboard
from src.utils.matchers import persian_matcher, national_code_matcher, phone_number_matcher, dob_matcher
from src.utils.time import to_utc
from src.utils.db import db
from src.utils.referral import create_referral


async def register_intro(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    ctx.user_data["in_conversation"] = True

    registered = await is_user_registered(update, ctx)

    if registered:
        await message_sender("شما قبلا ثبت نام کرده اید.", await main_keyboard(update, ctx))

        if "in_conversation" in ctx.user_data:
            ctx.user_data["in_conversation"] = False

        return ConversationHandler.END

    keyboard = cancel_keyboard("CANCEL")

    if not update.effective_user.username:
        await message_sender("برای ثبت نام داشتن username برای تلگرام اجباری است. \n جهت ثبت نام برای اکانت تلگرام خود username ست کنید.")

        if "in_conversation" in ctx.user_data:
            ctx.user_data["in_conversation"] = False

        return ConversationHandler.END

    await message_sender("برای ادامه ثبت نام اسمت رو برام بفرست(دقت کن که حتما اسمت باید فارسی باشه، در ضمن فقط نام کوچیکت رو تو این مرحله نیاز داریم)", keyboard)

    return RegisterStates.COLLECT_FIRSTNAME


async def collect_firstname(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    firstname = update.message.text
    keyboard = cancel_keyboard("CANCEL")

    if not persian_matcher(firstname):
        await message_sender("اسمت رو باید فارسی وارد کنی", keyboard, edit=False)

        return RegisterStates.COLLECT_FIRSTNAME

    ctx.user_data["register"] = {
        "firstname": firstname
    }

    await message_sender("حالا نام خانوادگیت رو هم بفرست", keyboard, edit=False)

    return RegisterStates.COLLECT_LASTNAME


async def collect_lastname(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    lastname = update.message.text
    keyboard = cancel_keyboard("CANCEL")

    if not persian_matcher(lastname):
        await message_sender("نام خانوادگیت رو باید فارسی وارد کنی.", keyboard, edit=False)

        return RegisterStates.COLLECT_LASTNAME

    ctx.user_data["register"]["lastname"] = lastname

    await message_sender("کد ملیت هم نیاز میشه(به انگلیسی باشه لطفا)", keyboard, edit=False)

    return RegisterStates.COLLECT_NATIONAL_CODE


async def collect_national_code(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    national_code = update.message.text
    keyboard = cancel_keyboard("CANCEL")

    if not national_code_matcher(national_code):
        await message_sender("کد ملیت صحیح نیست", keyboard, edit=False)

        return RegisterStates.COLLECT_NATIONAL_CODE

    is_duplicate_national_code = await db.user.find_first(
        where={
            "national_code": national_code
        }
    )

    if is_duplicate_national_code:
        await message_sender("کد ملیت توسط فرد دیگه ای استفاده شده.", keyboard, edit=False)

        return RegisterStates.COLLECT_NATIONAL_CODE

    ctx.user_data["register"]["national_code"] = national_code

    await message_sender(" شماره تماست رو هم بفرست ترجیحا مال خودت باشه (به انگلیسی)", keyboard, edit=False)

    return RegisterStates.COLLECT_PHONE_NUMBER


async def collect_phone_number(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    phone_number = update.message.text
    keyboard = cancel_keyboard("CANCEL")

    if not phone_number_matcher(phone_number):
        await message_sender("شماره تماست صحیح نیست", keyboard, edit=False)

        return RegisterStates.COLLECT_PHONE_NUMBER

    ctx.user_data["register"]["phone_number"] = phone_number

    await message_sender("تاریخ تولدت هم نیاز میشه(به فرمت 1381/03/26، یعنی اول سال بعد ماه بعد روز)", keyboard, edit=False)

    return RegisterStates.COLLECT_DOB


async def collect_dob(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    dob = update.message.text
    keyboard = cancel_keyboard("CANCEL")

    if not dob_matcher(dob):
        await message_sender("فرمت تاریخ تولد صحیح نیست", keyboard, edit=False)

        return RegisterStates.COLLECT_DOB

    year, month, day = map(int, dob.split('/'))
    jalali_dob = jdatetime.date(
        year, month, day).togregorian()

    ctx.user_data["register"]["dob"] = to_utc(jalali_dob)

    keyboard = InlineKeyboardMarkup(
        grade_keyboard(array_form=True) + cancel_keyboard("CANCEL", array_form=True))

    await message_sender("پایه تحصیلیت رو هم انتخاب کن", keyboard, edit=False)

    return RegisterStates.COLLECT_GRADE


async def collect_grade(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    grade = update.callback_query.data.split(" ")[1]

    ctx.user_data["register"]["grade"] = grade

    keyboard = InlineKeyboardMarkup(
        field_keyboard(array_form=True) + cancel_keyboard("CANCEL", array_form=True))

    await message_sender("رشته تحصیلیت رو هم بگو", keyboard)

    return RegisterStates.COLLECT_FIELD


async def collect_field(update: Update, ctx: ContextTypes.DEFAULT_TYPE, message_sender):
    field = update.callback_query.data.split(" ")[1]
    tel_id = update.effective_user.id

    async with db.tx() as tx:
        await tx.user.create(
            data={
                "firstname": ctx.user_data["register"]["firstname"],
                "lastname": ctx.user_data["register"]["lastname"],
                "national_code": ctx.user_data["register"]["national_code"],
                "phone_number": ctx.user_data["register"]["phone_number"],
                "dob": ctx.user_data["register"]["dob"],
                "grade": ctx.user_data["register"]["grade"],
                "field": field,
                "tel_id": tel_id,
                "tel_chat_id": update.effective_chat.id
            }
        )

        if "referred_tel_id" in ctx.user_data:
            await create_referral(update.effective_user.id, ctx.user_data["referred_tel_id"], tx)

    keyboard = await main_keyboard(update, ctx)

    await message_sender("ثبت نامت تموم شد حالا میتونی از خدمات ربات استفاده کنی", keyboard)

    if "in_conversation" in ctx.user_data:
        ctx.user_data["in_conversation"] = False

    return ConversationHandler.END
