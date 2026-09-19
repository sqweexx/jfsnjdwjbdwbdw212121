import logging
import sys
from pathlib import Path

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    BusinessMessagesDeletedHandler,
    BusinessConnectionHandler,
    filters,
)

from config import BOT_TOKEN
from handlers import (
    start_command,
    button_handler,
    on_business_message,
    on_edited_business_message,
    on_deleted_business_messages,
    on_business_connection,
    error_handler,
)

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

# Библиотеки — только ошибки, без INFO/WARNING-спама
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("telegram").setLevel(logging.ERROR)
logging.getLogger("telegram.ext").setLevel(logging.ERROR)


def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    # Команда /start
    application.add_handler(CommandHandler("start", start_command))

    # Кнопки меню
    application.add_handler(CallbackQueryHandler(button_handler))

    # Новые бизнес-сообщения
    application.add_handler(
        MessageHandler(filters.UpdateType.BUSINESS_MESSAGE, on_business_message)
    )

    # Редактирование
    application.add_handler(
        MessageHandler(filters.UpdateType.EDITED_BUSINESS_MESSAGE, on_edited_business_message)
    )

    # Удаление
    application.add_handler(
        BusinessMessagesDeletedHandler(on_deleted_business_messages)
    )

    # Подключение Business
    application.add_handler(
        BusinessConnectionHandler(on_business_connection)
    )

    application.add_error_handler(error_handler)

    application.run_polling(
        allowed_updates=[
            "message",                    # нужно для /start
            "callback_query",             # нужно для кнопок
            "business_connection",
            "business_message",
            "edited_business_message",
            "deleted_business_messages",
        ],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
