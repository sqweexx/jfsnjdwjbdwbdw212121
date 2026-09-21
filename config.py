"""Конфигурация бота из .env."""
from __future__ import annotations

import os

from dotenv import load_dotenv


class Config:
    """Настройки окружения приложения."""

    def __init__(self) -> None:
        load_dotenv()
        self.bot_token = os.getenv("BOT_TOKEN")
        self.owner_id = int(os.getenv("OWNER_ID", "0"))
        self.timezone = os.getenv("TIMEZONE", "Europe/Prague")
        # Сообщения в RAM: хранить 3 часа, чистить раз в 2 минуты
        self.message_ttl_seconds = int(os.getenv("MESSAGE_TTL_SECONDS", str(3 * 3600)))
        self.cleanup_interval_seconds = int(os.getenv("CLEANUP_INTERVAL_SECONDS", "120"))
        self.validate()

    def validate(self) -> None:
        if not self.bot_token:
            raise ValueError("BOT_TOKEN is required")
        if not self.owner_id:
            raise ValueError("OWNER_ID is required")
        if self.message_ttl_seconds <= 0:
            raise ValueError("MESSAGE_TTL_SECONDS must be > 0")
        if self.cleanup_interval_seconds <= 0:
            raise ValueError("CLEANUP_INTERVAL_SECONDS must be > 0")


config = Config()

# Совместимость со старыми импортами
BOT_TOKEN = config.bot_token
OWNER_ID = config.owner_id
TIMEZONE = config.timezone
MESSAGE_TTL_SECONDS = config.message_ttl_seconds
CLEANUP_INTERVAL_SECONDS = config.cleanup_interval_seconds
