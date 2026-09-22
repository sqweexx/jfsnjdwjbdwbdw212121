import asyncio
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

from config import Config, config
from handlers import BotHandlers
from storage import BotStorage
from utils import MessageParser

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

logger = logging.getLogger(__name__)


async def _ram_cleanup_loop(
    messages_store,
    ttl_seconds: int,
    interval_seconds: int,
) -> None:
    """Фоновая очистка просроченных сообщений из RAM."""
    while True:
        try:
            messages_store.cleanup_expired(ttl_seconds)
        except Exception as e:
            logger.error("Ошибка TTL-очистки RAM: %s", type(e).__name__)
        await asyncio.sleep(interval_seconds)


def build_app(
    app_config: Config | None = None,
) -> tuple[Application, BotHandlers]:
    cfg = app_config or config
    bot_storage = BotStorage(
        settings_path=DATA_DIR / "settings.json",
        referrals_path=DATA_DIR / "referrals.db",
    )
    parser = MessageParser(timezone=cfg.timezone)
    bot_handlers = BotHandlers(bot_storage=bot_storage, parser=parser)

    async def post_init(app: Application) -> None:
        app.create_task(
            _ram_cleanup_loop(
                bot_storage.messages,
                cfg.message_ttl_seconds,
                cfg.cleanup_interval_seconds,
            )
        )

    application = (
        Application.builder()
        .token(cfg.bot_token)
        .post_init(post_init)
        .build()
    )
    application.bot_data["bot_storage"] = bot_storage
    application.bot_data["config"] = cfg

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
    return application, bot_handlers


def build_handlers() -> BotHandlers:
    _, bot_handlers = build_app()
    return bot_handlers


def main() -> None:
    application, _ = build_app()
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
