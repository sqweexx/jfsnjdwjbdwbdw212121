"""
Хранилище: сообщения и business-подключения — только RAM;
настройки пользователей — на диск (data/settings.json).

Ключ сообщения: (connection_id, chat_id, message_id) — чтобы два аккаунта
с одним ботом не перезаписывали данные друг друга.
"""
from __future__ import annotations

import json
import logging
from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
SETTINGS_FILE = DATA_DIR / "settings.json"

_messages: dict[tuple[str, int, int], dict[str, Any]] = {}
_settings: dict[int, dict[str, bool]] = {}
_connections: dict[str, int] = {}  # connection_id -> user_id
_lock = Lock()
_settings_loaded = False

DEFAULT_SETTINGS: dict[str, bool] = {
    "deleted": True,
    "edited": True,
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


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_settings(raw: dict[str, Any] | None) -> dict[str, bool]:
    settings = deepcopy(DEFAULT_SETTINGS)
    if not isinstance(raw, dict):
        return settings
    for key in DEFAULT_SETTINGS:
        if key in raw:
            settings[key] = bool(raw[key])
    return settings


def _load_settings_unlocked() -> None:
    """Загрузить настройки с диска. Вызывать только под _lock."""
    global _settings_loaded
    if _settings_loaded:
        return
    _settings_loaded = True
    if not SETTINGS_FILE.exists():
        return
    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, dict):
            return
        for user_key, user_settings in payload.items():
            try:
                user_id = int(user_key)
            except (TypeError, ValueError):
                continue
            _settings[user_id] = _normalize_settings(user_settings)
    except (OSError, json.JSONDecodeError) as e:
        logger.error("Не удалось загрузить настройки: %s", type(e).__name__)


def _save_settings_unlocked() -> None:
    """Сохранить настройки на диск. Вызывать только под _lock."""
    _ensure_data_dir()
    payload = {
        str(user_id): settings
        for user_id, settings in _settings.items()
    }
    tmp_path = SETTINGS_FILE.with_suffix(".tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        tmp_path.replace(SETTINGS_FILE)
    except OSError as e:
        logger.error("Не удалось сохранить настройки: %s", type(e).__name__)
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


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
        _load_settings_unlocked()
        if user_id not in _settings:
            _settings[user_id] = deepcopy(DEFAULT_SETTINGS)
            _save_settings_unlocked()
        return deepcopy(_settings[user_id])


def set_setting(user_id: int, key: str, value: bool) -> dict[str, bool]:
    with _lock:
        _load_settings_unlocked()
        if user_id not in _settings:
            _settings[user_id] = deepcopy(DEFAULT_SETTINGS)
        if key in _settings[user_id]:
            _settings[user_id][key] = value
        _save_settings_unlocked()
        return deepcopy(_settings[user_id])


def is_enabled(user_id: int, key: str) -> bool:
    with _lock:
        _load_settings_unlocked()
        if user_id not in _settings:
            return DEFAULT_SETTINGS.get(key, True)
        return _settings[user_id].get(key, True)
