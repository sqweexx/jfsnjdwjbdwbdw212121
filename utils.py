from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Message, User
from config import TIMEZONE

# В MTProto одноразовое медиа: ttl_seconds == 0x7FFFFFFF.
# Bot API официально поле не документирует, но если оно приходит —
# python-telegram-bot кладёт его в api_kwargs.
VIEW_ONCE_TTL = 0x7FFFFFFF  # 2147483647


def format_time(ts: int | None) -> str:
    if ts is None:
        return "неизвестно"
    tz = ZoneInfo(TIMEZONE)
    dt = datetime.fromtimestamp(ts, tz=tz)
    return dt.strftime("%H:%M")


def get_sender_display(message: Message) -> str:
    """Возвращает: Имя (@username) или просто Имя"""
    if not message.from_user:
        if message.chat:
            return message.chat.title or message.chat.full_name or str(message.chat.id)
        return "Неизвестный"

    user: User = message.from_user
    name = user.full_name or "Без имени"
    if user.username:
        return f"{name} (@{user.username})"
    return name


def get_media_ttl_seconds(message: Message) -> int | None:
    """Достаёт ttl_seconds из сырого update (api_kwargs), если Telegram его прислал."""
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


def is_view_once_media(message: Message) -> bool:
    """True только для одноразового / самоуничтожающегося медиа (не обычного)."""
    ttl = get_media_ttl_seconds(message)
    if ttl is None:
        return False
    # view-once (0x7FFFFFFF) или медиа с таймером самоуничтожения
    return ttl > 0


def extract_message_data(message: Message) -> dict:
    ttl = get_media_ttl_seconds(message)
    data = {
        "message_id": message.message_id,
        "chat_id": message.chat.id,
        "date": message.date.timestamp() if message.date else None,
        "sender_name": get_sender_display(message),
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
        "is_view_once": bool(ttl and ttl > 0),
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
        data["text"] = f"Контакт: {message.contact.first_name or ''} {message.contact.last_name or ''}\nТелефон: {message.contact.phone_number or ''}"
    elif message.location:
        data["content_type"] = "location"
        data["text"] = f"Геолокация: {message.location.latitude}, {message.location.longitude}"
    elif message.venue:
        data["content_type"] = "venue"
        data["text"] = f"Место: {message.venue.title}\nАдрес: {message.venue.address}"
    elif message.poll:
        data["content_type"] = "poll"
        data["text"] = f"Опрос: {message.poll.question}"
    else:
        data["content_type"] = "unknown"
        data["text"] = "[Неподдерживаемый тип]"

    return data
