import logging
from typing import Literal, TypeAlias
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, CommandHandler, MessageHandler
from telegram.ext._utils.types import HandlerCallback, CCT, RT
from telegram.ext.filters import BaseFilter
from telegram._utils.types import SCT

# Utils
from src.utils.message import send_message
from src.guards import ignore_none_registered, ignore_none_advisor, ignore_none_admin
from src.utils.chat import get_chat
from src.utils.matchers import exact_matcher

GuardT: TypeAlias = Literal["none", "registration", "advisor", "admin"]
CallbackT = HandlerCallback[Update, CCT, RT]
MatherT: TypeAlias = Literal["exact", "prefix"]
CHAT_BEHAVIOR: TypeAlias = Literal["DISABLE", "ENABLE", "NEUTRAL"]


class SuperBaseHandler:
    _guard: GuardT = None
    _while_in_chat_behavior: CHAT_BEHAVIOR = "NEUTRAL"
    _used_in_conversation = False
    _callback: CallbackT = None

    async def _callback_wrapper(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        should_ignore = False

        logging.info(self._callback.__name__)

        match self._guard:
            case "registration":
                should_ignore = await ignore_none_registered(update, ctx)
            case "advisor":
                should_ignore = await ignore_none_advisor(update, ctx)
            case "admin":
                should_ignore = await ignore_none_admin(update, ctx)

        chat = await get_chat(update, ctx)
        message_sender = send_message(update, ctx)

        match self._while_in_chat_behavior:
            case "DISABLE":
                if chat:
                    if "in_conversation" in ctx.user_data:
                        ctx.user_data["in_conversation"] = False

                    return ConversationHandler.END
            case "ENABLE":
                if not chat:
                    if "in_conversation" in ctx.user_data:
                        ctx.user_data["in_conversation"] = False

                    return ConversationHandler.END

        if should_ignore:
            if "in_conversation" in ctx.user_data:
                ctx.user_data["in_conversation"] = False

            return ConversationHandler.END

        return await self._callback(update, ctx, message_sender)


class SuperCallbackQueryHandler(CallbackQueryHandler, SuperBaseHandler):
    def prefix_matcher(self, data: str):
        def prefix_matcher_action(callback_data: str):
            return callback_data.split(" ")[0] == data

        return prefix_matcher_action

    def __init__(
            self,
            callback: CallbackT,
            matcher: str,
            matcher_type: MatherT = "exact",
            guard: GuardT = "registration",
            while_in_chat_behavior: CHAT_BEHAVIOR = "NEUTRAL",
            used_in_conversation=False
    ) -> None:
        self._callback = callback
        self._guard = guard
        self._while_in_chat_behavior = while_in_chat_behavior
        self._used_in_conversation = used_in_conversation

        super().__init__(self._callback_wrapper, pattern=exact_matcher(matcher)
                         if matcher_type == "exact" else self.prefix_matcher(matcher))


class SuperCommandHandler(CommandHandler, SuperBaseHandler):
    def __init__(
            self,
            command: SCT[str],
            callback: HandlerCallback[Update, CCT, RT],
            guard: GuardT = "registration",
            while_in_chat_behavior: CHAT_BEHAVIOR = "NEUTRAL",
            used_in_conversation=False
    ):
        self._callback = callback
        self._guard = guard
        self._while_in_chat_behavior = while_in_chat_behavior
        self._used_in_conversation = used_in_conversation

        super().__init__(command, self._callback_wrapper)


class SuperMessageHandler(MessageHandler, SuperBaseHandler):
    def __init__(
        self,
        filters: BaseFilter,
        callback: HandlerCallback[Update, CCT, RT],
        guard: GuardT = "registration",
        while_in_chat_behavior: CHAT_BEHAVIOR = "NEUTRAL",
        used_in_conversation=False
    ):
        self._callback = callback
        self._guard = guard
        self._while_in_chat_behavior = while_in_chat_behavior
        self._used_in_conversation = used_in_conversation

        super().__init__(filters, self._callback_wrapper)
