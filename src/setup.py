from datetime import datetime
from os import path, getcwd
from aiofiles import os, open
from telegram import Update
from telegram.ext import (
    Application,
    ExtBot,
    JobQueue,
    ConversationHandler,
    filters,
    ChatMemberHandler,
    TypeHandler
)

# Utils
from src.utils.db import connect_to_db, db

# Commands
from src.commands.others import (
    start,
    back_to_menu,
    make_primary_group,
    unmake_primary_group,
    show_menu,
    exit_all_chats,
    get_referral_link,
    about_us,
    keep_chat_clear,
    error_handler,
    last_resort
)
from src.commands.register import (
    register_intro,
    collect_firstname,
    collect_lastname,
    collect_national_code,
    collect_phone_number,
    collect_dob,
    collect_grade,
    collect_field
)
from src.commands.support import (
    add_group,
    add_member_to_advisors,
    remove_member_from_advisors,
    create_request_advisor,
    chat_message_broker,
    exit_chat,
    create_factor,
    collect_product_for_factor,
    confirm_create_factor,
    confirm_factor,
    collect_factor,
    confirm_confirm_factor
)
from src.commands.choose_field import (
    choose_field_intro,
    collect_choose_field_product,
    pay_directly,
    pay_via_operator,
    pay_by_referral,
    confirm_direct_payment
)
from src.commands.management import (
    show_admin_menu,
    ask_global_message,
    collect_global_message,
    ask_maintenance_duration,
    collect_maintenance_duration,
    show_users_list,
    collect_user_id,
    show_advisor_menu,
    show_products_list_for_message,
    collect_product_id_for_message,
    collect_student_id_for_message,
    collect_advisor_message,
    show_product_list_for_export,
    collect_product_id_for_export,
    show_product_list_for_product_notification,
    collect_product_id_for_product_based_notification,
    collect_notification_message_for_product_based
)
from src.commands.pdf import (
    complete_profile,
    complete_tir_konkur,
    complete_ordibehesht_konkur,
    complete_choose_field_bias,
    complete_khordad_grades,
    collect_pdf_for_profile_generator,
    retrieve_pdf,
    retrieve_tir_konkur,
    retrieve_ordibehesht_konkur,
    retrieve_choose_field_bias,
    retrieve_khordad_grades,
    retrieve_pdf_generator
)

# Constants
from src.constants import (
    START,
    REGISTER,
    BACK_TO_MENU,
    REGISTER_GRADE_PREFIX,
    REGISTER_FIELD_PREFIX,
    MAKE_PRIMARY_GROUP,
    UNMAKE_PRIMARY_GROUP,
    QA,
    EXIT_CHAT,
    RegisterStates,
    SHOW_MENU,
    CREATE_FACTOR,
    PRE_PRODUCTS,
    EXIT_ALL_CHATS,
    CreateFactorState,
    CONFIRM_FACTOR,
    COLLECT_PRODUCT_FOR_FACTOR_PREFIX,
    CONFIRM_FACTOR_PREFIX,
    ConfirmFactorState,
    COLLECT_FACTOR_PREFIX,
    CONFIRM_CONFIRM_FACTOR_PREFIX,
    REFERRAL,
    ABOUT_US,
    CHOOSE_FIELD,
    ChooseFieldState,
    COLLECT_CHOOSE_FIELD_PRODUCT_PREFIX,
    ADMIN,
    ADMIN_SEND_NOTIFICATION,
    ADMIN_SEND_MAINTENANCE_NOTIFICATION,
    ADMIN_SHOW_USERS_LIST,
    GlobalMessageState,
    BotMaintenanceState,
    GetStudentsState,
    ADMIN_COLLECT_STUDENT_ID_PREFIX,
    ADMIN_SHOW_USERS_LIST_CHANGE_PAGE_PREFIX,
    BACK_TO_ADMIN_MENU,
    ADVISOR,
    ADVISOR_SHOW_PRODUCTS_LIST,
    BACK_TO_ADVISOR_MENU,
    RetrieveProfileState,
    SendMessageToStudentState,
    COLLECT_PRODUCT_ID_FOR_MESSAGE_PREFIX,
    ADVISOR_SHOW_USERS_LIST_CHANGE_PAGE_PREFIX,
    COLLECT_STUDENT_ID_FOR_MESSAGE_PREFIX,
    ADVISOR_EXPORT_CUSTOMER_DETAILS,
    COMPLETE_PROFILE,
    CompleteProfileState,
    DATA_DIR_PATH,
    PDF_DIR_PATH,
    ExportExcelState,
    ADVISOR_COLLECT_PRODUCT_ID_FOR_EXPORT_PREFIX,
    DIRECT_PAY_VERIFICATION_PREFIX,
    PDFTypes,
    TIR_KONKUR_COMPLETE_PROFILE,
    ORDIBEHESHT_KONKUR_COMPLETE_PROFILE,
    CHOOSE_FIELD_BIAS_COMPLETE_PROFILE,
    KHORDAD_GRADES_COMPLETE_PROFILE,
    ADVISOR_GET_STUDENT_PDF,
    TIR_KONKUR_RETRIEVE_PDF,
    ORDIBEHESHT_KONKUR_RETRIEVE_PDF,
    CHOOSE_FIELD_BIAS_RETRIEVE_PDF,
    KHORDAD_GRADES_RETRIEVE_PDF,
    ADMIN_SEND_PRODUCT_BASED_NOTIFICATION,
    ProductBasedNotification,
    ADMIN_SEND_PRODUCT_BASED_NOTIFICATION_PREFIX,
    CHAT_HANDLERS_GROUP,
    PDF_HANDLERS_GROUP
)

# Handlers
from src.handlers import (
    SuperCommandHandler,
    SuperCallbackQueryHandler,
    SuperMessageHandler
)


async def create_pre_products():
    async with db.tx() as tx:
        for product in PRE_PRODUCTS:
            fetched_product = await tx.product.find_first(where={
                "title": product["title"],
            })

            if not fetched_product and not product["deleted"]:
                await tx.product.create(data={
                    "title": product["title"],
                    "price": product["price"],
                    "capacity": product["capacity"]
                })

                continue

            if fetched_product and (
                    fetched_product.price != product["price"] or
                    fetched_product.capacity != product["capacity"] or
                    product["deleted"] != bool(fetched_product.deleted_at)
            ):
                await tx.product.update(
                    where={
                        "product_id": fetched_product.product_id
                    },
                    data={
                        "price": product["price"],
                        "capacity": product["capacity"],
                        "deleted_at": datetime.now() if product["deleted"] else None
                    }
                )


async def create_data_dir():
    data_dir_path = path.join(getcwd(), DATA_DIR_PATH)

    if not path.isdir(data_dir_path):
        await os.mkdir(data_dir_path)

    await os.makedirs(path.join(getcwd(), DATA_DIR_PATH, PDF_DIR_PATH), exist_ok=True)


async def setup(
        application: Application[ExtBot, dict, dict, JobQueue],
):
    # Pre setup actions
    await connect_to_db()
    await create_pre_products()
    await create_data_dir()

    ######################## General Handlers ########################
    start_handler = SuperCommandHandler(
        START, start, guard="none", while_in_chat_behavior="DISABLE")

    show_menu_handler = SuperCommandHandler(
        SHOW_MENU, show_menu, guard="none", while_in_chat_behavior="DISABLE")

    exit_all_chats_hanlder = SuperCommandHandler(
        EXIT_ALL_CHATS, exit_all_chats, guard="registration")

    back_to_menu_handler = SuperCallbackQueryHandler(
        back_to_menu, BACK_TO_MENU, guard="none")

    get_referral_link_handler = SuperCallbackQueryHandler(
        get_referral_link, REFERRAL, guard="registration", while_in_chat_behavior="DISABLE"
    )

    about_us_handler = SuperCallbackQueryHandler(
        about_us, ABOUT_US, guard="registration", while_in_chat_behavior="DISABLE"
    )

    register_handler = ConversationHandler(
        per_chat=True,
        per_user=True,
        entry_points=[
            SuperCallbackQueryHandler(
                register_intro, REGISTER, guard="none", while_in_chat_behavior="DISABLE", used_in_conversation=True)
        ],
        states={
            RegisterStates.COLLECT_FIRSTNAME: [SuperMessageHandler(
                filters.TEXT, collect_firstname, guard="none")],
            RegisterStates.COLLECT_LASTNAME: [
                SuperMessageHandler(filters.TEXT, collect_lastname, guard="none", while_in_chat_behavior="DISABLE",
                                    used_in_conversation=True)],
            RegisterStates.COLLECT_NATIONAL_CODE: [
                SuperMessageHandler(filters.TEXT, collect_national_code, guard="none", while_in_chat_behavior="DISABLE",
                                    used_in_conversation=True)],
            RegisterStates.COLLECT_PHONE_NUMBER: [
                SuperMessageHandler(filters.TEXT, collect_phone_number, guard="none", while_in_chat_behavior="DISABLE",
                                    used_in_conversation=True)],
            RegisterStates.COLLECT_DOB: [
                SuperMessageHandler(filters.TEXT, collect_dob, guard="none", while_in_chat_behavior="DISABLE",
                                    used_in_conversation=True)],
            RegisterStates.COLLECT_GRADE: [
                SuperCallbackQueryHandler(collect_grade, REGISTER_GRADE_PREFIX, "prefix", guard="none",
                                          while_in_chat_behavior="DISABLE", used_in_conversation=True)],
            RegisterStates.COLLECT_FIELD: [
                SuperCallbackQueryHandler(collect_field, REGISTER_FIELD_PREFIX, "prefix", guard="none",
                                          while_in_chat_behavior="DISABLE", used_in_conversation=True)],
        },
        fallbacks=[SuperCallbackQueryHandler(
            back_to_menu, BACK_TO_MENU, guard="none", while_in_chat_behavior="DISABLE", used_in_conversation=True)]
    )

    request_advisor_handler = SuperCallbackQueryHandler(
        create_request_advisor(), QA, "exact", guard="registration", while_in_chat_behavior="DISABLE")

    choose_field_handler = ConversationHandler(
        per_chat=True,
        per_user=True,
        per_message=True,
        entry_points=[
            SuperCallbackQueryHandler(choose_field_intro, CHOOSE_FIELD, 'exact',
                                      guard="registration", while_in_chat_behavior="DISABLE", used_in_conversation=True)
        ],
        states={
            ChooseFieldState.COLLECT_CHOOSE_FIELD_PRODUCT: [
                SuperCallbackQueryHandler(
                    collect_choose_field_product, COLLECT_CHOOSE_FIELD_PRODUCT_PREFIX, 'prefix', guard="registration",
                    while_in_chat_behavior="DISABLE", used_in_conversation=True)
            ],
            ChooseFieldState.SHOW_PAYMENT_OPTIONS: [
                SuperCallbackQueryHandler(pay_directly, str(ChooseFieldState.PAY_DIRECTLY),
                                          'exact', guard="registration", while_in_chat_behavior="DISABLE",
                                          used_in_conversation=True),
                SuperCallbackQueryHandler(pay_via_operator, str(ChooseFieldState.PAY_VIA_OPERATOR),
                                          'exact', guard="registration", while_in_chat_behavior="DISABLE",
                                          used_in_conversation=True),
                SuperCallbackQueryHandler(pay_by_referral, str(ChooseFieldState.PAY_BY_REFERRAL),
                                          'exact', guard="registration", while_in_chat_behavior="DISABLE",
                                          used_in_conversation=True),
            ],
            ChooseFieldState.CONFIRM_DIRECT_PAYMENT: [
                SuperCallbackQueryHandler(confirm_direct_payment, DIRECT_PAY_VERIFICATION_PREFIX,
                                          'prefix', guard="registration", while_in_chat_behavior="DISABLE",
                                          used_in_conversation=True)
            ]
        },
        fallbacks=[SuperCallbackQueryHandler(
            back_to_menu, BACK_TO_MENU, guard="none", while_in_chat_behavior="DISABLE", used_in_conversation=True)]
    )

    ######################## Group Related Handlers ########################
    complete_profile_handler = ConversationHandler(
        per_chat=True,
        per_user=True,
        allow_reentry=True,
        entry_points=[
            SuperCommandHandler(
                COMPLETE_PROFILE, complete_profile, guard="registration", while_in_chat_behavior="DISABLE",
                used_in_conversation=True)
        ],
        states={
            CompleteProfileState.COLLECT_PDF_FOR_PROFILE: [
                SuperCallbackQueryHandler(complete_tir_konkur, TIR_KONKUR_COMPLETE_PROFILE,
                                          "exact", guard="registration", while_in_chat_behavior="DISABLE", used_in_conversation=True),
                SuperCallbackQueryHandler(complete_ordibehesht_konkur, ORDIBEHESHT_KONKUR_COMPLETE_PROFILE,
                                          "exact", guard="registration", while_in_chat_behavior="DISABLE", used_in_conversation=True),
                SuperCallbackQueryHandler(complete_choose_field_bias, CHOOSE_FIELD_BIAS_COMPLETE_PROFILE,
                                          "exact", guard="registration", while_in_chat_behavior="DISABLE", used_in_conversation=True),
                SuperCallbackQueryHandler(complete_khordad_grades, KHORDAD_GRADES_COMPLETE_PROFILE,
                                          "exact", guard="registration", while_in_chat_behavior="DISABLE", used_in_conversation=True),
            ],
            CompleteProfileState.COMPLETE_TIR_KONKUR: [
                SuperMessageHandler(filters.Document.PDF, collect_pdf_for_profile_generator(PDFTypes.TIR_KONKUR),
                                    guard="registration", while_in_chat_behavior="DISABLE", used_in_conversation=True)
            ],
            CompleteProfileState.COMPLETE_ORDIBEHESHT_KONKUR: [
                SuperMessageHandler(filters.Document.PDF, collect_pdf_for_profile_generator(PDFTypes.ORDIBEHESHT_KONKUR),
                                    guard="registration", while_in_chat_behavior="DISABLE", used_in_conversation=True)
            ],
            CompleteProfileState.COMPLETE_CHOOSE_FIELD_BIAS: [
                SuperMessageHandler(filters.Document.PDF, collect_pdf_for_profile_generator(PDFTypes.CHOOSE_FIELD_BIAS),
                                    guard="registration", while_in_chat_behavior="DISABLE", used_in_conversation=True)
            ],
            CompleteProfileState.COMPLETE_KHORDAD_GRADES: [
                SuperMessageHandler(filters.Document.PDF, collect_pdf_for_profile_generator(PDFTypes.KHORDAD_GRADES),
                                    guard="registration", while_in_chat_behavior="DISABLE", used_in_conversation=True)
            ]
        },
        fallbacks=[SuperCallbackQueryHandler(
            back_to_menu, BACK_TO_MENU, guard="none", while_in_chat_behavior="DISABLE", used_in_conversation=True)]
    )

    retrieve_student_pdf =  ConversationHandler(
        per_user=True,
        per_chat=True,
        allow_reentry=True,
        entry_points=[
            SuperCallbackQueryHandler(
                retrieve_pdf, ADVISOR_GET_STUDENT_PDF, "exact",
                guard="advisor", while_in_chat_behavior="DISABLE", used_in_conversation=True
            )
        ],
        states={
            RetrieveProfileState.COLLECT_NATIONAL_CODE: [
                SuperCallbackQueryHandler(retrieve_tir_konkur, TIR_KONKUR_RETRIEVE_PDF,
                                          "exact", guard="registration", while_in_chat_behavior="DISABLE", used_in_conversation=True),
                SuperCallbackQueryHandler(retrieve_ordibehesht_konkur, ORDIBEHESHT_KONKUR_RETRIEVE_PDF,
                                          "exact", guard="registration", while_in_chat_behavior="DISABLE", used_in_conversation=True),
                SuperCallbackQueryHandler(retrieve_choose_field_bias, CHOOSE_FIELD_BIAS_RETRIEVE_PDF,
                                          "exact", guard="registration", while_in_chat_behavior="DISABLE", used_in_conversation=True),
                SuperCallbackQueryHandler(retrieve_khordad_grades, KHORDAD_GRADES_RETRIEVE_PDF,
                                          "exact", guard="registration", while_in_chat_behavior="DISABLE", used_in_conversation=True),
            ],
            RetrieveProfileState.RETRIEVE_TIR_KONKUR: [
                SuperMessageHandler(filters.TEXT, retrieve_pdf_generator(PDFTypes.TIR_KONKUR),
                                    guard="registration", while_in_chat_behavior="DISABLE", used_in_conversation=True)
            ],
            RetrieveProfileState.RETRIEVE_ORDIBEHESHT_KONKUR: [
                SuperMessageHandler(filters.TEXT, retrieve_pdf_generator(PDFTypes.ORDIBEHESHT_KONKUR),
                                    guard="registration", while_in_chat_behavior="DISABLE", used_in_conversation=True)
            ],
            RetrieveProfileState.RETRIEVE_CHOOSE_FIELD_BIAS: [
                SuperMessageHandler(filters.TEXT, retrieve_pdf_generator(PDFTypes.CHOOSE_FIELD_BIAS),
                                    guard="registration", while_in_chat_behavior="DISABLE", used_in_conversation=True)
            ],
            RetrieveProfileState.RETRIEVE_KHORDAD_GRADES: [
                SuperMessageHandler(filters.TEXT, retrieve_pdf_generator(PDFTypes.KHORDAD_GRADES),
                                    guard="registration", while_in_chat_behavior="DISABLE", used_in_conversation=True)
            ]
        },
        fallbacks=[SuperCallbackQueryHandler(
            back_to_menu, BACK_TO_MENU, guard="none", while_in_chat_behavior="DISABLE", used_in_conversation=True)]
    )

    ######################## Group Related Handlers ########################
    add_group_handler = ChatMemberHandler(
        add_group, ChatMemberHandler.MY_CHAT_MEMBER)

    add_member_to_advisor_handler = SuperMessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS, add_member_to_advisors, guard="none")

    remove_member_from_advisors_handler = SuperMessageHandler(
        filters.StatusUpdate.LEFT_CHAT_MEMBER, remove_member_from_advisors, guard="none")

    make_primary_group_handler = SuperCommandHandler(
        MAKE_PRIMARY_GROUP, make_primary_group, guard="admin")

    unmake_primary_group_handler = SuperCommandHandler(
        UNMAKE_PRIMARY_GROUP, unmake_primary_group, guard="admin")

    ######################## Admin Panel Handlers ########################
    admin_menu_handler = SuperCallbackQueryHandler(
        show_admin_menu, ADMIN, "exact", guard="admin", while_in_chat_behavior="DISABLE")

    admin_global_notification_handler = ConversationHandler(
        per_chat=True,
        per_user=True,
        entry_points=[
            SuperCallbackQueryHandler(
                ask_global_message, ADMIN_SEND_NOTIFICATION, "exact", guard="admin", while_in_chat_behavior="DISABLE",
                used_in_conversation=True)
        ],
        states={
            GlobalMessageState.COLLECT_GLOBAL_MESSAGE: [
                SuperMessageHandler(filters.TEXT, collect_global_message, guard="admin",
                                    while_in_chat_behavior="DISABLE", used_in_conversation=True)
            ]
        },
        fallbacks=[SuperCallbackQueryHandler(
            show_admin_menu, BACK_TO_ADMIN_MENU, guard="none", used_in_conversation=True)]
    )

    admin_maintenance_handler = ConversationHandler(
        per_chat=True,
        per_user=True,
        entry_points=[
            SuperCallbackQueryHandler(
                ask_maintenance_duration, ADMIN_SEND_MAINTENANCE_NOTIFICATION, "exact", guard="admin",
                while_in_chat_behavior="DISABLE", used_in_conversation=True)
        ],
        states={
            BotMaintenanceState.COLLECT_MAINTENANCE_DURATION: [
                SuperMessageHandler(filters.TEXT, collect_maintenance_duration, guard="admin",
                                    while_in_chat_behavior="DISABLE", used_in_conversation=True)
            ]
        },
        fallbacks=[SuperCallbackQueryHandler(
            show_admin_menu, BACK_TO_ADMIN_MENU, guard="none", used_in_conversation=True)]
    )

    admin_show_student_handler = ConversationHandler(
        per_chat=True,
        per_user=True,
        per_message=True,
        entry_points=[
            SuperCallbackQueryHandler(show_users_list, ADMIN_SHOW_USERS_LIST, "exact",
                                      guard="admin", while_in_chat_behavior="DISABLE", used_in_conversation=True)
        ],
        states={
            GetStudentsState.COLLECT_STUDENT_ID: [
                SuperCallbackQueryHandler(collect_user_id, ADMIN_COLLECT_STUDENT_ID_PREFIX, "prefix",
                                          guard="admin", while_in_chat_behavior="DISABLE", used_in_conversation=True),
                SuperCallbackQueryHandler(
                    show_users_list, ADMIN_SHOW_USERS_LIST_CHANGE_PAGE_PREFIX, "prefix", guard="admin",
                    while_in_chat_behavior="DISABLE",
                    used_in_conversation=True
                )
            ]
        },
        fallbacks=[SuperCallbackQueryHandler(
            show_admin_menu, BACK_TO_ADMIN_MENU, guard="none", used_in_conversation=True)]
    )

    admin_send_product_based_notification_handler = ConversationHandler(
            per_chat=True,
            per_user=True,
            entry_points=[
                SuperCallbackQueryHandler(
                    show_product_list_for_product_notification, ADMIN_SEND_PRODUCT_BASED_NOTIFICATION,
                    "exact", guard="admin", while_in_chat_behavior="DISABLE", used_in_conversation=True)
            ],
            states={
                ProductBasedNotification.COLLECT_PRODUCT_ID_FOR_NOTIFICATION: [
                    SuperCallbackQueryHandler(
                        collect_product_id_for_product_based_notification,
                        ADMIN_SEND_PRODUCT_BASED_NOTIFICATION_PREFIX,
                        "prefix", guard="admin", while_in_chat_behavior="DISABLE", used_in_conversation=True),
                ],
                ProductBasedNotification.COLLECT_NOTIFICATION_MESSAGE_FOR_PRODUCT_BASED: [
                    SuperMessageHandler(filters.TEXT, collect_notification_message_for_product_based,
                        guard="admin", while_in_chat_behavior="DISABLE", used_in_conversation=True)
                ]
            },
            fallbacks=[SuperCallbackQueryHandler(
                show_admin_menu, BACK_TO_ADMIN_MENU, guard="none", used_in_conversation=True)]
        )


    ######################## Advisor Panel Handlers ########################
    advisor_menu_handler = SuperCallbackQueryHandler(
        show_advisor_menu, ADVISOR, "exact", guard="advisor", while_in_chat_behavior="DISABLE")

    export_excel_handler = ConversationHandler(
        per_chat=True,
        per_user=True,
        per_message=True,
        entry_points=[
            SuperCallbackQueryHandler(
                show_product_list_for_export, ADVISOR_EXPORT_CUSTOMER_DETAILS, "exact", guard="advisor",
                while_in_chat_behavior="DISABLE", used_in_conversation=True)
        ],
        states={
            ExportExcelState.COLLECT_PRODUCT_ID_FOR_EXPORT: [
                SuperCallbackQueryHandler(collect_product_id_for_export, ADVISOR_COLLECT_PRODUCT_ID_FOR_EXPORT_PREFIX,
                                          'prefix', guard="advisor", while_in_chat_behavior="DISABLE", used_in_conversation=True)
            ]
        },
        fallbacks=[SuperCallbackQueryHandler(
            show_advisor_menu, BACK_TO_ADVISOR_MENU, guard="advisor", used_in_conversation=True)]
    )

    send_message_to_students_handler = ConversationHandler(
        per_chat=True,
        per_user=True,
        entry_points=[
            SuperCallbackQueryHandler(show_products_list_for_message, ADVISOR_SHOW_PRODUCTS_LIST, "exact",
                                      guard="advisor", while_in_chat_behavior="DISABLE", used_in_conversation=True)
        ],
        states={
            SendMessageToStudentState.COLLECT_PRODUCT_ID_FOR_MESSAGE: [
                SuperCallbackQueryHandler(
                    collect_product_id_for_message, COLLECT_PRODUCT_ID_FOR_MESSAGE_PREFIX, "prefix", guard="advisor",
                    while_in_chat_behavior="DISABLE", used_in_conversation=True),
            ],
            SendMessageToStudentState.COLLECT_STUDENT_ID_FOR_MESSAGE: [
                SuperCallbackQueryHandler(collect_student_id_for_message, COLLECT_STUDENT_ID_FOR_MESSAGE_PREFIX,
                                          "prefix", guard="advisor", while_in_chat_behavior="DISABLE",
                                          used_in_conversation=True),
                SuperCallbackQueryHandler(
                    collect_product_id_for_message, ADVISOR_SHOW_USERS_LIST_CHANGE_PAGE_PREFIX, "prefix",
                    guard="advisor", while_in_chat_behavior="DISABLE", used_in_conversation=True)
            ],
            SendMessageToStudentState.COLLECT_ADVISOR_MESSAGE: [
                SuperMessageHandler(filters.TEXT, collect_advisor_message, guard="advisor",
                                    while_in_chat_behavior="DISABLE", used_in_conversation=True)
            ]
        },
        fallbacks=[SuperCallbackQueryHandler(
            show_advisor_menu, BACK_TO_ADVISOR_MENU, guard="advisor", used_in_conversation=True)]
    )

    ######################## While in Chat Handlers ########################
    exit_chat_handler = SuperMessageHandler(
        filters.Regex(EXIT_CHAT), exit_chat, guard="registration", while_in_chat_behavior="ENABLE")

    create_factor_starter_handler = SuperMessageHandler(
        filters.Regex(CREATE_FACTOR), create_factor, guard="advisor", while_in_chat_behavior="ENABLE"
    )

    confirm_factor_starter_handler = SuperMessageHandler(
        filters.Regex(CONFIRM_FACTOR), confirm_factor, guard="advisor",
        while_in_chat_behavior="ENABLE"
    )

    create_factor_handler = ConversationHandler(
        per_chat=True,
        per_user=True,
        entry_points=[
            SuperCallbackQueryHandler(
                collect_product_for_factor, COLLECT_PRODUCT_FOR_FACTOR_PREFIX, "prefix", guard="advisor",
                while_in_chat_behavior="ENABLE", used_in_conversation=True)
        ],
        states={
            CreateFactorState.CONFIRM: [
                SuperCallbackQueryHandler(
                    confirm_create_factor, CONFIRM_FACTOR_PREFIX, "prefix", guard="advisor",
                    while_in_chat_behavior="ENABLE", used_in_conversation=True)
            ]
        },
        fallbacks=[SuperCallbackQueryHandler(
            back_to_menu, BACK_TO_MENU, guard="none", used_in_conversation=True)]
    )

    confirm_factor_handler = ConversationHandler(
        per_chat=True,
        per_user=True,
        entry_points=[
            SuperCallbackQueryHandler(
                collect_factor, COLLECT_FACTOR_PREFIX, "prefix", guard="advisor", while_in_chat_behavior="ENABLE",
                used_in_conversation=True)
        ],
        states={
            ConfirmFactorState.CONFIRM_FACTOR_COLLECTED: [
                SuperCallbackQueryHandler(
                    confirm_confirm_factor, CONFIRM_CONFIRM_FACTOR_PREFIX, "prefix", guard="advisor",
                    while_in_chat_behavior="ENABLE", used_in_conversation=True)
            ]
        },
        fallbacks=[SuperCallbackQueryHandler(
            back_to_menu, BACK_TO_MENU, guard="none", used_in_conversation=True)]
    )

    chat_message_handler = SuperMessageHandler(filters.TEXT | filters.PHOTO,
                                               chat_message_broker, guard="registration", while_in_chat_behavior="ENABLE")

    ######################## Helper Handlers ########################
    chat_cleaner_handler = SuperMessageHandler(
        filters.ALL, keep_chat_clear, guard="none")

    last_resort_hanlder = TypeHandler(Update, last_resort)

    ######################## Adding All Handlers ########################
    application.add_handler(start_handler)

    application.add_handler(show_menu_handler)

    application.add_handler(exit_all_chats_hanlder)

    application.add_handler(back_to_menu_handler)

    application.add_handler(get_referral_link_handler)

    application.add_handler(about_us_handler)

    application.add_handler(register_handler)

    application.add_handler(choose_field_handler)

    application.add_handler(request_advisor_handler)

    # PDF Handlers
    application.add_handler(complete_profile_handler, group=PDF_HANDLERS_GROUP)

    application.add_handler(retrieve_student_pdf, group=PDF_HANDLERS_GROUP)

    # Group Related Handlers
    application.add_handler(add_group_handler)

    application.add_handler(add_member_to_advisor_handler)

    application.add_handler(remove_member_from_advisors_handler)

    application.add_handler(make_primary_group_handler)

    application.add_handler(unmake_primary_group_handler)

    # Admin Panel Handlers
    application.add_handler(admin_menu_handler)

    application.add_handler(admin_global_notification_handler)

    application.add_handler(admin_maintenance_handler)

    application.add_handler(admin_show_student_handler)

    application.add_handler(admin_send_product_based_notification_handler)

    # Advisor Panel Handlers
    application.add_handler(advisor_menu_handler)

    application.add_handler(export_excel_handler)

    application.add_handler(send_message_to_students_handler)

    application.add_handler(create_factor_starter_handler)

    application.add_handler(confirm_factor_handler)

    # While in Chat Handlers
    application.add_handler(exit_chat_handler, group=CHAT_HANDLERS_GROUP)

    application.add_handler(create_factor_handler, group=CHAT_HANDLERS_GROUP)

    application.add_handler(confirm_factor_starter_handler, group=CHAT_HANDLERS_GROUP)

    application.add_handler(chat_message_handler, group=CHAT_HANDLERS_GROUP)

    application.add_handler(chat_cleaner_handler, group=CHAT_HANDLERS_GROUP)

    # Other Handlers
    application.add_handler(last_resort_hanlder)

    application.add_error_handler(error_handler)

    commands = [
        (START, "استارت ربات و نمایش منوی ربات"),
        (SHOW_MENU, "نمایش منوی ربات"),
        (EXIT_ALL_CHATS, "خروج از تمامی چت های فعال"),
        (COMPLETE_PROFILE, "تکمیل پروفایل انتخاب رشته"),
    ]

    await application.bot.set_my_commands(commands)
