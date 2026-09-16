import logging
import sys
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

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)


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

    logger.info("Бот запущен. Ожидание бизнес-сообщений...")
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
