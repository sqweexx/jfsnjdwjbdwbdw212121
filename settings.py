"""Персистентное хранилище настроек пользователей (data/settings.json)."""
from __future__ import annotations

import json
import logging
from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

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


class UserSettingsStore:
    """Настройки уведомлений пользователей с сохранением на диск."""

    def __init__(self, path: Path | str = Path("data") / "settings.json") -> None:
        self.path = Path(path)
        self._settings: dict[int, dict[str, bool]] = {}
        self._lock = Lock()
        self._loaded = False

    def _ensure_dir(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _normalize(raw: dict[str, Any] | None) -> dict[str, bool]:
        settings = deepcopy(DEFAULT_SETTINGS)
        if not isinstance(raw, dict):
            return settings
        for key in DEFAULT_SETTINGS:
            if key in raw:
                settings[key] = bool(raw[key])
        return settings

    def _load_unlocked(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self.path.exists():
            return
        try:
            with self.path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            if not isinstance(payload, dict):
                return
            for user_key, user_settings in payload.items():
                try:
                    user_id = int(user_key)
                except (TypeError, ValueError):
                    continue
                self._settings[user_id] = self._normalize(user_settings)
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Не удалось загрузить настройки: %s", type(e).__name__)

    def _save_unlocked(self) -> None:
        self._ensure_dir()
        payload = {
            str(user_id): settings
            for user_id, settings in self._settings.items()
        }
        tmp_path = self.path.with_suffix(".tmp")
        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            tmp_path.replace(self.path)
        except OSError as e:
            logger.error("Не удалось сохранить настройки: %s", type(e).__name__)
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass

    def get(self, user_id: int) -> dict[str, bool]:
        with self._lock:
            self._load_unlocked()
            if user_id not in self._settings:
                self._settings[user_id] = deepcopy(DEFAULT_SETTINGS)
                self._save_unlocked()
            return deepcopy(self._settings[user_id])

    def set(self, user_id: int, key: str, value: bool) -> dict[str, bool]:
        with self._lock:
            self._load_unlocked()
            if user_id not in self._settings:
                self._settings[user_id] = deepcopy(DEFAULT_SETTINGS)
            if key in self._settings[user_id]:
                self._settings[user_id][key] = value
            self._save_unlocked()
            return deepcopy(self._settings[user_id])

    def is_enabled(self, user_id: int, key: str) -> bool:
        with self._lock:
            self._load_unlocked()
            if user_id not in self._settings:
                return DEFAULT_SETTINGS.get(key, True)
            return self._settings[user_id].get(key, True)
