import logging
import sys
from pathlib import Path

from telegram.ext import (
    Application,
    BusinessConnectionHandler,
    BusinessMessagesDeletedHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN
from handlers import BotHandlers
from settings import UserSettingsStore
from storage import ConnectionStore, MessageStore

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

_log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_file_handler = logging.FileHandler(DATA_DIR / "bot.log", encoding="utf-8")
_file_handler.setLevel(logging.ERROR)
_file_handler.setFormatter(logging.Formatter(_log_format))

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.ERROR)
_console_handler.setFormatter(logging.Formatter(_log_format))

logging.basicConfig(
    level=logging.ERROR,
    handlers=[_file_handler, _console_handler],
)

logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("telegram").setLevel(logging.ERROR)
logging.getLogger("telegram.ext").setLevel(logging.ERROR)


def build_handlers() -> BotHandlers:
    return BotHandlers(
        messages=MessageStore(),
        connections=ConnectionStore(),
        settings=UserSettingsStore(DATA_DIR / "settings.json"),
    )


def main() -> None:
    bot_handlers = build_handlers()
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", bot_handlers.start_command))
    application.add_handler(CallbackQueryHandler(bot_handlers.button_handler))
    application.add_handler(
        MessageHandler(filters.UpdateType.BUSINESS_MESSAGE, bot_handlers.on_business_message)
    )
    application.add_handler(
        MessageHandler(
            filters.UpdateType.EDITED_BUSINESS_MESSAGE,
            bot_handlers.on_edited_business_message,
        )
    )
    application.add_handler(
        BusinessMessagesDeletedHandler(bot_handlers.on_deleted_business_messages)
    )
    application.add_handler(
        BusinessConnectionHandler(bot_handlers.on_business_connection)
    )
    application.add_error_handler(bot_handlers.error_handler)

    application.run_polling(
        allowed_updates=[
            "message",
            "callback_query",
            "business_connection",
            "business_message",
            "edited_business_message",
            "deleted_business_messages",
        ],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
