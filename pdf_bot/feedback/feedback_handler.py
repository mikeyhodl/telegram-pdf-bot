from telegram import Message, Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
)

from pdf_bot.consts import CANCEL, TEXT_FILTER
from pdf_bot.language import LanguageService
from pdf_bot.telegram_internal.telegram_service import TelegramService

from .exceptions import FeedbackInvalidLanguageError
from .feedback_service import FeedbackService


class FeedbackHandler:
    _FEEDBACK_COMMAND = "feedback"
    _WAIT_FEEDBACK = 0

    def __init__(
        self,
        feedback_service: FeedbackService,
        language_service: LanguageService,
        telegram_service: TelegramService,
    ) -> None:
        self.feedback_service = feedback_service
        self.language_service = language_service
        self.telegram_service = telegram_service

    def conversation_handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[CommandHandler(self._FEEDBACK_COMMAND, self.ask_feedback)],
            states={
                self._WAIT_FEEDBACK: [MessageHandler(TEXT_FILTER, self.check_text)]
            },
            fallbacks=[
                CommandHandler("cancel", self.telegram_service.cancel_conversation)
            ],
        )

    async def ask_feedback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        await self.telegram_service.reply_with_cancel_markup(
            update, context, _("Send me your feedback in English")
        )

        return self._WAIT_FEEDBACK

    async def check_text(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        if update.message.text == _(CANCEL):
            return await self.telegram_service.cancel_conversation(update, context)

        return await self._save_feedback(update, context)

    async def _save_feedback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.message
        try:
            self.feedback_service.save_feedback(
                message.chat.id, message.from_user.username, message.text
            )
            await message.reply_text(
                _("Thank you for your feedback, I've forwarded it to my developer")
            )
        except FeedbackInvalidLanguageError as e:
            await message.reply_text(_(str(e)))
            return self._WAIT_FEEDBACK

        return ConversationHandler.END
