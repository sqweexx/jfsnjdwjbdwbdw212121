"""Рефералы и уровни доступа (SQLite)."""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

# Пороги уровней по числу приглашённых
LEVEL_THRESHOLDS = (
    (3, 3),  # 3+ → уровень 3
    (1, 2),  # 1–2 → уровень 2
    (0, 1),  # 0 → уровень 1
)

# Какие фичи доступны на каждом уровне (ключи настроек / возможностей)
LEVEL_FEATURES: dict[int, frozenset[str]] = {
    1: frozenset({"deleted", "text", "photo"}),
    2: frozenset({
        "deleted",
        "edited",
        "text",
        "photo",
        "video",
        "voice",
        "video_note",
        "document",
        "sticker",
        "audio",
        "animation",
        "other",
        # view_once намеренно нет
    }),
    3: frozenset({
        "deleted",
        "edited",
        "view_once",
        "text",
        "photo",
        "video",
        "voice",
        "video_note",
        "document",
        "sticker",
        "audio",
        "animation",
        "other",
    }),
}

LEVEL_TITLES = {
    1: "Уровень 1 — базовый",
    2: "Уровень 2 — расширенный",
    3: "Уровень 3 — полный доступ",
}


def level_from_count(count: int) -> int:
    for threshold, level in LEVEL_THRESHOLDS:
        if count >= threshold:
            return level
    return 1


def features_for_level(level: int) -> frozenset[str]:
    return LEVEL_FEATURES.get(level, LEVEL_FEATURES[1])


class ReferralStore:
    """Хранение пользователей и рефералов в SQLite (+ JSON-бэкап известных user_id)."""

    def __init__(self, path: Path | str = Path("data") / "referrals.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.known_path = self.path.parent / "known_users.json"
        self._lock = Lock()
        self._init_db()
        self._restore_known_users()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        referrer_id INTEGER,
                        created_at REAL NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS referrals (
                        referrer_id INTEGER NOT NULL,
                        referred_id INTEGER NOT NULL UNIQUE,
                        created_at REAL NOT NULL,
                        PRIMARY KEY (referrer_id, referred_id)
                    );
                    CREATE INDEX IF NOT EXISTS idx_referrals_referrer
                        ON referrals(referrer_id);
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def _read_known_file(self) -> set[int]:
        if not self.known_path.exists():
            return set()
        try:
            with self.known_path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            if not isinstance(payload, list):
                return set()
            result: set[int] = set()
            for item in payload:
                try:
                    result.add(int(item))
                except (TypeError, ValueError):
                    continue
            return result
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Не удалось прочитать known_users: %s", type(e).__name__)
            return set()

    def _write_known_file(self, ids: set[int]) -> None:
        tmp_path = self.known_path.with_suffix(".tmp")
        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(sorted(ids), f, ensure_ascii=False)
            tmp_path.replace(self.known_path)
        except OSError as e:
            logger.error("Не удалось сохранить known_users: %s", type(e).__name__)
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass

    def _remember_user(self, user_id: int) -> None:
        """Добавить user_id в JSON-бэкап (вызывать под self._lock)."""
        known = self._read_known_file()
        if user_id in known:
            return
        known.add(user_id)
        self._write_known_file(known)

    def _restore_known_users(self) -> None:
        """Восстановить users из JSON, если SQLite был очищен/пересоздан."""
        known = self._read_known_file()
        if not known:
            # Первичная синхронизация: выгрузить уже известных из SQLite в JSON
            with self._lock:
                conn = self._connect()
                try:
                    rows = conn.execute("SELECT user_id FROM users").fetchall()
                    ids = {int(r["user_id"]) for r in rows}
                finally:
                    conn.close()
                if ids:
                    self._write_known_file(ids)
            return

        with self._lock:
            conn = self._connect()
            try:
                now = time.time()
                conn.executemany(
                    "INSERT OR IGNORE INTO users (user_id, referrer_id, created_at) "
                    "VALUES (?, NULL, ?)",
                    [(uid, now) for uid in known],
                )
                conn.commit()
            finally:
                conn.close()

    def import_user_ids(self, user_ids: list[int] | set[int]) -> None:
        """Пометить пользователей как уже известных (например из settings.json)."""
        ids = {int(uid) for uid in user_ids}
        if not ids:
            return
        with self._lock:
            conn = self._connect()
            try:
                now = time.time()
                conn.executemany(
                    "INSERT OR IGNORE INTO users (user_id, referrer_id, created_at) "
                    "VALUES (?, NULL, ?)",
                    [(uid, now) for uid in ids],
                )
                conn.commit()
            finally:
                conn.close()
            known = self._read_known_file()
            known |= ids
            self._write_known_file(known)

    def ensure_user(self, user_id: int) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO users (user_id, referrer_id, created_at) "
                    "VALUES (?, NULL, ?)",
                    (user_id, time.time()),
                )
                conn.commit()
            finally:
                conn.close()
            self._remember_user(user_id)

    def user_exists(self, user_id: int) -> bool:
        """True, если пользователь уже когда-либо запускал бота (/start)."""
        with self._lock:
            if user_id in self._read_known_file():
                return True
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT 1 FROM users WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                return row is not None
            finally:
                conn.close()

    def register_referral(self, referred_id: int, referrer_id: int) -> bool:
        """
        Засчитать переход по реферальной ссылке только для нового пользователя.
        Если человек уже писал /start раньше — приглашение не засчитывается.
        Возвращает True, если реферал записан.
        """
        if referred_id == referrer_id:
            return False

        with self._lock:
            conn = self._connect()
            try:
                now = time.time()
                # Уже знакомый пользователь (SQLite или JSON-бэкап) — не считаем
                if referred_id in self._read_known_file():
                    return False
                existing = conn.execute(
                    "SELECT 1 FROM users WHERE user_id = ?",
                    (referred_id,),
                ).fetchone()
                if existing:
                    return False

                conn.execute(
                    "INSERT OR IGNORE INTO users (user_id, referrer_id, created_at) "
                    "VALUES (?, NULL, ?)",
                    (referrer_id, now),
                )
                conn.execute(
                    "INSERT INTO users (user_id, referrer_id, created_at) "
                    "VALUES (?, ?, ?)",
                    (referred_id, referrer_id, now),
                )
                conn.execute(
                    "INSERT INTO referrals (referrer_id, referred_id, created_at) "
                    "VALUES (?, ?, ?)",
                    (referrer_id, referred_id, now),
                )
                conn.commit()
                # Оба пользователя теперь известны боту
                known = self._read_known_file()
                known.add(referred_id)
                known.add(referrer_id)
                self._write_known_file(known)
                return True
            except sqlite3.IntegrityError:
                try:
                    conn.rollback()
                except Exception:
                    pass
                return False
            except Exception as e:
                logger.error("register_referral failed: %s", type(e).__name__)
                try:
                    conn.rollback()
                except Exception:
                    pass
                return False
            finally:
                conn.close()

    def count_referrals(self, user_id: int) -> int:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT COUNT(*) AS c FROM referrals WHERE referrer_id = ?",
                    (user_id,),
                ).fetchone()
                return int(row["c"] if row else 0)
            finally:
                conn.close()

    def get_level(self, user_id: int) -> int:
        return level_from_count(self.count_referrals(user_id))

    def get_referrer(self, user_id: int) -> int | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT referrer_id FROM users WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                if not row:
                    return None
                return row["referrer_id"]
            finally:
                conn.close()

    def referral_link(self, user_id: int, bot_username: str) -> str:
        username = bot_username.lstrip("@")
        return f"https://t.me/{username}?start=ref_{user_id}"

    def can_use(self, user_id: int, feature: str) -> bool:
        level = self.get_level(user_id)
        return feature in features_for_level(level)

    def level_info(self, user_id: int) -> dict:
        count = self.count_referrals(user_id)
        level = level_from_count(count)
        return {
            "count": count,
            "level": level,
            "title": LEVEL_TITLES.get(level, LEVEL_TITLES[1]),
            "features": sorted(features_for_level(level)),
        }
