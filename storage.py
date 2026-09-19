"""
Временное хранилище сообщений, настроек и business-подключений (только RAM).
Ключ сообщения: (connection_id, chat_id, message_id) — чтобы два аккаунта
с одним ботом не перезаписывали данные друг друга.
"""
from typing import Any
from threading import Lock
from copy import deepcopy

_messages: dict[tuple[str, int, int], dict[str, Any]] = {}
_settings: dict[int, dict[str, bool]] = {}
_connections: dict[str, int] = {}  # connection_id -> user_id
_lock = Lock()

DEFAULT_SETTINGS: dict[str, bool] = {
    "deleted": True,
    "edited": True,
    "view_once": True,
    "text": True,
    "photo": True,
    "video": True,
    "voice": True,
    "video_note": True,
    "document": True,
    "sticker": True,
    "audio": True,
    "animation": True,
    "other": True,
}


def store(connection_id: str, chat_id: int, message_id: int, data: dict[str, Any]) -> None:
    with _lock:
        _messages[(connection_id or "", chat_id, message_id)] = data


def get(connection_id: str, chat_id: int, message_id: int) -> dict[str, Any] | None:
    with _lock:
        return _messages.get((connection_id or "", chat_id, message_id))


def pop(connection_id: str, chat_id: int, message_id: int) -> dict[str, Any] | None:
    with _lock:
        return _messages.pop((connection_id or "", chat_id, message_id), None)


def cleanup_old(max_size: int = 5000) -> int:
    with _lock:
        if len(_messages) <= max_size:
            return 0
        to_remove = len(_messages) - max_size
        keys = list(_messages.keys())[:to_remove]
        for k in keys:
            del _messages[k]
        return to_remove


def size() -> int:
    with _lock:
        return len(_messages)


def save_connection(connection_id: str, user_id: int) -> None:
    with _lock:
        _connections[connection_id] = user_id


def remove_connection(connection_id: str) -> None:
    with _lock:
        _connections.pop(connection_id, None)


def get_connection_user(connection_id: str | None) -> int | None:
    if not connection_id:
        return None
    with _lock:
        return _connections.get(connection_id)


def get_settings(user_id: int) -> dict[str, bool]:
    with _lock:
        if user_id not in _settings:
            _settings[user_id] = deepcopy(DEFAULT_SETTINGS)
        return deepcopy(_settings[user_id])


def set_setting(user_id: int, key: str, value: bool) -> dict[str, bool]:
    with _lock:
        if user_id not in _settings:
            _settings[user_id] = deepcopy(DEFAULT_SETTINGS)
        if key in _settings[user_id]:
            _settings[user_id][key] = value
        return deepcopy(_settings[user_id])


def is_enabled(user_id: int, key: str) -> bool:
    with _lock:
        if user_id not in _settings:
            return DEFAULT_SETTINGS.get(key, True)
        return _settings[user_id].get(key, True)
