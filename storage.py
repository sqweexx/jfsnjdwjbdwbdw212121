"""
Хранилище в RAM: сообщения и business-подключения.
Настройки пользователей — в settings.UserSettingsStore (диск).

Ключ сообщения: (connection_id, chat_id, message_id).
"""
from __future__ import annotations

from threading import Lock
from typing import Any

from settings import DEFAULT_SETTINGS, UserSettingsStore

# Реэкспорт для совместимости импортов
__all__ = [
    "DEFAULT_SETTINGS",
    "MessageStore",
    "ConnectionStore",
    "messages",
    "connections",
    "user_settings",
    "store",
    "get",
    "pop",
    "cleanup_old",
    "size",
    "save_connection",
    "remove_connection",
    "get_connection_user",
    "get_settings",
    "set_setting",
    "is_enabled",
]


class MessageStore:
    """Временное хранилище business-сообщений (только RAM)."""

    def __init__(self) -> None:
        self._messages: dict[tuple[str, int, int], dict[str, Any]] = {}
        self._lock = Lock()

    def store(
        self, connection_id: str, chat_id: int, message_id: int, data: dict[str, Any]
    ) -> None:
        with self._lock:
            self._messages[(connection_id or "", chat_id, message_id)] = data

    def get(
        self, connection_id: str, chat_id: int, message_id: int
    ) -> dict[str, Any] | None:
        with self._lock:
            return self._messages.get((connection_id or "", chat_id, message_id))

    def pop(
        self, connection_id: str, chat_id: int, message_id: int
    ) -> dict[str, Any] | None:
        with self._lock:
            return self._messages.pop((connection_id or "", chat_id, message_id), None)

    def cleanup_old(self, max_size: int = 5000) -> int:
        with self._lock:
            if len(self._messages) <= max_size:
                return 0
            to_remove = len(self._messages) - max_size
            keys = list(self._messages.keys())[:to_remove]
            for key in keys:
                del self._messages[key]
            return to_remove

    def size(self) -> int:
        with self._lock:
            return len(self._messages)


class ConnectionStore:
    """Кэш business-подключений: connection_id -> user_id (только RAM)."""

    def __init__(self) -> None:
        self._connections: dict[str, int] = {}
        self._lock = Lock()

    def save(self, connection_id: str, user_id: int) -> None:
        with self._lock:
            self._connections[connection_id] = user_id

    def remove(self, connection_id: str) -> None:
        with self._lock:
            self._connections.pop(connection_id, None)

    def get_user(self, connection_id: str | None) -> int | None:
        if not connection_id:
            return None
        with self._lock:
            return self._connections.get(connection_id)


# Синглтоны приложения
messages = MessageStore()
connections = ConnectionStore()
user_settings = UserSettingsStore()


# --- Совместимый модульный API (thin wrappers) ---

def store(connection_id: str, chat_id: int, message_id: int, data: dict[str, Any]) -> None:
    messages.store(connection_id, chat_id, message_id, data)


def get(connection_id: str, chat_id: int, message_id: int) -> dict[str, Any] | None:
    return messages.get(connection_id, chat_id, message_id)


def pop(connection_id: str, chat_id: int, message_id: int) -> dict[str, Any] | None:
    return messages.pop(connection_id, chat_id, message_id)


def cleanup_old(max_size: int = 5000) -> int:
    return messages.cleanup_old(max_size)


def size() -> int:
    return messages.size()


def save_connection(connection_id: str, user_id: int) -> None:
    connections.save(connection_id, user_id)


def remove_connection(connection_id: str) -> None:
    connections.remove(connection_id)


def get_connection_user(connection_id: str | None) -> int | None:
    return connections.get_user(connection_id)


def get_settings(user_id: int) -> dict[str, bool]:
    return user_settings.get(user_id)


def set_setting(user_id: int, key: str, value: bool) -> dict[str, bool]:
    return user_settings.set(user_id, key, value)


def is_enabled(user_id: int, key: str) -> bool:
    return user_settings.is_enabled(user_id, key)
