"""Парсинг Telegram Message в словарь данных."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Message, User

from config import config

# В MTProto одноразовое медиа: ttl_seconds == 0x7FFFFFFF.
VIEW_ONCE_TTL = 0x7FFFFFFF  # 2147483647

# В RAM только метаданные — без текста, caption, file_id и прочего содержимого.
RAM_METADATA_KEYS = (
    "message_id",
    "chat_id",
    "date",
    "sender_name",
    "sender_id",
    "business_connection_id",
    "notify_user_id",
    "content_type",
    "ttl_seconds",
    "has_protected_content",
    "is_view_once",
)


class MessageParser:
    """Хелперы для извлечения данных и определения одноразового медиа."""

    def __init__(self, timezone: str | None = None) -> None:
        self.timezone = timezone or config.timezone

    def format_time(self, ts: int | None) -> str:
        if ts is None:
            return "неизвестно"
        tz = ZoneInfo(self.timezone)
        dt = datetime.fromtimestamp(ts, tz=tz)
        return dt.strftime("%H:%M")

    def get_sender_display(self, message: Message) -> str:
        if not message.from_user:
            if message.chat:
                return message.chat.title or message.chat.full_name or str(message.chat.id)
            return "Неизвестный"

        user: User = message.from_user
        name = user.full_name or "Без имени"
        if user.username:
            return f"{name} (@{user.username})"
        return name

    def get_media_ttl_seconds(self, message: Message) -> int | None:
        if message.api_kwargs:
            ttl = message.api_kwargs.get("ttl_seconds")
            if isinstance(ttl, int):
                return ttl

        for attr in ("video", "voice", "video_note", "audio", "document", "animation"):
            media = getattr(message, attr, None)
            if media is None:
                continue
            kwargs = getattr(media, "api_kwargs", None) or {}
            ttl = kwargs.get("ttl_seconds")
            if isinstance(ttl, int):
                return ttl
        return None

    def is_view_once_media(self, message: Message) -> bool:
        """
        True для одноразового / таймерного медиа.
        Telegram обычно помечает его has_protected_content;
        дополнительно смотрим ttl_seconds в api_kwargs.
        """
        ttl = self.get_media_ttl_seconds(message)
        if isinstance(ttl, int) and ttl > 0:
            return True
        return bool(message.has_protected_content)

    def extract_message_data(self, message: Message) -> dict:
        ttl = self.get_media_ttl_seconds(message)
        protected = bool(message.has_protected_content)
        is_view_once = (isinstance(ttl, int) and ttl > 0) or protected
        data = {
            "message_id": message.message_id,
            "chat_id": message.chat.id,
            "date": message.date.timestamp() if message.date else None,
            "sender_name": self.get_sender_display(message),
            "sender_id": message.from_user.id if message.from_user else None,
            "business_connection_id": message.business_connection_id,
            "content_type": None,
            "text": None,
            "caption": None,
            "file_id": None,
            "file_unique_id": None,
            "mime_type": None,
            "file_name": None,
            "duration": None,
            "width": None,
            "height": None,
            "emoji": None,
            "set_name": None,
            "is_animated": None,
            "is_video": None,
            "ttl_seconds": ttl,
            "has_protected_content": protected,
            "is_view_once": is_view_once,
        }

        if message.text:
            data["content_type"] = "text"
            data["text"] = message.text
        elif message.photo:
            data["content_type"] = "photo"
            photo = message.photo[-1]
            data["file_id"] = photo.file_id
            data["file_unique_id"] = photo.file_unique_id
            data["caption"] = message.caption
            data["width"] = photo.width
            data["height"] = photo.height
        elif message.video:
            data["content_type"] = "video"
            data["file_id"] = message.video.file_id
            data["caption"] = message.caption
            data["duration"] = message.video.duration
            data["width"] = message.video.width
            data["height"] = message.video.height
            data["mime_type"] = message.video.mime_type
            data["file_name"] = message.video.file_name
        elif message.document:
            data["content_type"] = "document"
            data["file_id"] = message.document.file_id
            data["caption"] = message.caption
            data["mime_type"] = message.document.mime_type
            data["file_name"] = message.document.file_name
        elif message.voice:
            data["content_type"] = "voice"
            data["file_id"] = message.voice.file_id
            data["duration"] = message.voice.duration
            data["mime_type"] = message.voice.mime_type
            data["caption"] = message.caption
        elif message.audio:
            data["content_type"] = "audio"
            data["file_id"] = message.audio.file_id
            data["duration"] = message.audio.duration
            data["mime_type"] = message.audio.mime_type
            data["file_name"] = message.audio.file_name
            data["caption"] = message.caption
        elif message.sticker:
            data["content_type"] = "sticker"
            data["file_id"] = message.sticker.file_id
            data["emoji"] = message.sticker.emoji
            data["set_name"] = message.sticker.set_name
            data["is_animated"] = message.sticker.is_animated
            data["is_video"] = message.sticker.is_video
            data["width"] = message.sticker.width
            data["height"] = message.sticker.height
        elif message.animation:
            data["content_type"] = "animation"
            data["file_id"] = message.animation.file_id
            data["caption"] = message.caption
            data["duration"] = message.animation.duration
            data["width"] = message.animation.width
            data["height"] = message.animation.height
            data["mime_type"] = message.animation.mime_type
            data["file_name"] = message.animation.file_name
        elif message.video_note:
            data["content_type"] = "video_note"
            data["file_id"] = message.video_note.file_id
            data["duration"] = message.video_note.duration
        elif message.contact:
            data["content_type"] = "contact"
            data["text"] = (
                f"Контакт: {message.contact.first_name or ''} "
                f"{message.contact.last_name or ''}\n"
                f"Телефон: {message.contact.phone_number or ''}"
            )
        elif message.location:
            data["content_type"] = "location"
            data["text"] = (
                f"Геолокация: {message.location.latitude}, {message.location.longitude}"
            )
        elif message.venue:
            data["content_type"] = "venue"
            data["text"] = (
                f"Место: {message.venue.title}\nАдрес: {message.venue.address}"
            )
        elif message.poll:
            data["content_type"] = "poll"
            data["text"] = f"Опрос: {message.poll.question}"
        else:
            data["content_type"] = "unknown"
            data["text"] = "[Неподдерживаемый тип]"

        return data

    def to_ram_record(self, data: dict) -> dict:
        """Урезанная запись для RAM: тип и служебные id, без содержимого сообщения."""
        return {key: data.get(key) for key in RAM_METADATA_KEYS}


# Синглтон + совместимые функции
message_parser = MessageParser()


def format_time(ts: int | None) -> str:
    return message_parser.format_time(ts)


def get_sender_display(message: Message) -> str:
    return message_parser.get_sender_display(message)


def get_media_ttl_seconds(message: Message) -> int | None:
    return message_parser.get_media_ttl_seconds(message)


def is_view_once_media(message: Message) -> bool:
    return message_parser.is_view_once_media(message)


def extract_message_data(message: Message) -> dict:
    return message_parser.extract_message_data(message)


def to_ram_record(data: dict) -> dict:
    return message_parser.to_ram_record(data)
