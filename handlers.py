"""Обработчики Telegram Business-бота (единый класс BotHandlers)."""
from __future__ import annotations

import logging
from io import BytesIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import storage
from config import OWNER_ID
from constants import (
    BOT_USERNAME,
    CONNECT_PHOTO_ID,
    EMOJI_BACK,
    EMOJI_CAMERA,
    EMOJI_CHECK,
    EMOJI_CROSS,
    EMOJI_EDIT,
    EMOJI_GEAR,
    EMOJI_INFO,
    EMOJI_LOCK,
    EMOJI_STAR,
    EMOJI_TRASH,
    STICKER_ID,
    VIEW_ONCE_MEDIA_TYPES,
)
from settings import DEFAULT_SETTINGS, UserSettingsStore
from storage import ConnectionStore, MessageStore
from utils import extract_message_data, get_sender_display, is_view_once_media

logger = logging.getLogger(__name__)


class BotHandlers:
    """Все хендлеры бота в одном классе, общий стиль и зависимости."""

    def __init__(
        self,
        messages: MessageStore | None = None,
        connections: ConnectionStore | None = None,
        settings: UserSettingsStore | None = None,
    ) -> None:
        self.messages = messages or storage.messages
        self.connections = connections or storage.connections
        self.settings = settings or storage.user_settings

    # ----- UI -----

    def get_main_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("ℹ️ Как работает бот", callback_data="info_how")],
            [
                InlineKeyboardButton("🗑 Удаления", callback_data="info_delete"),
                InlineKeyboardButton("✏️ Изменения", callback_data="info_edit"),
            ],
            [InlineKeyboardButton("🔒 Приватность", callback_data="info_privacy")],
            [InlineKeyboardButton("⚙️ Общие настройки", callback_data="settings_menu")],
            [InlineKeyboardButton("🔌 Подключение бота", callback_data="info_connect")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_start_text(self) -> str:
        return (
            f"<b>Добро пожаловать в <u>MessageSaver</u> Bot!</b>\n\n"
            f"С <b>MessageSaver</b> вы мгновенно увидите все ключевые события:\n\n"
            f"{EMOJI_EDIT} <b>Редактирование сообщений:</b>\n"
            f"— Показываю <b>старое</b> сообщение и <b>новое</b> (изменённое)\n"
            f"— Указываю автора и его @username\n\n"
            f"{EMOJI_TRASH} <b>Удаление сообщений:</b>\n"
            f"— Пересылаю любые форматы: текст, фото, видео, кружки, стикеры, документы, локации...\n\n"
            f"{EMOJI_CAMERA} <b>Медиафайлы:</b>\n"
            f"— Сохраняю фото, видео, голосовые, документы и стикеры\n"
            f"— Одноразовые (1 просмотр): ответь <b>не открывая</b> — пришлю копию\n"
            f"— Обычные сообщения по ответу <b>не</b> копирую\n"
            f"— Присылаю их вам вместе с информацией об отправителе\n\n"
            f"{EMOJI_LOCK} <b>Приватность:</b>\n"
            f"— Все данные хранятся только в оперативной памяти\n"
            f"— После перезапуска бота ничего не остаётся на сервере\n\n"
            f"{EMOJI_STAR} <b>Telegram Premium не нужен</b>\n"
            f"Базовые функции работают полностью бесплатно"
        )

    def _settings_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        s = self.settings.get(user_id)

        def mark(key: str) -> str:
            return EMOJI_CHECK if s.get(key, True) else EMOJI_CROSS

        keyboard = [
            [InlineKeyboardButton(f"{mark('deleted')} Удалённые сообщения", callback_data="set_deleted")],
            [InlineKeyboardButton(f"{mark('edited')} Изменённые сообщения", callback_data="set_edited")],
            [InlineKeyboardButton(f"{mark('view_once')} Одноразовые медиа", callback_data="set_view_once")],
            [
                InlineKeyboardButton(f"{mark('text')} Текст", callback_data="set_text"),
                InlineKeyboardButton(f"{mark('photo')} Фото", callback_data="set_photo"),
            ],
            [
                InlineKeyboardButton(f"{mark('video')} Видео", callback_data="set_video"),
                InlineKeyboardButton(f"{mark('voice')} Голосовые", callback_data="set_voice"),
            ],
            [
                InlineKeyboardButton(f"{mark('video_note')} Кружки", callback_data="set_video_note"),
                InlineKeyboardButton(f"{mark('sticker')} Стикеры", callback_data="set_sticker"),
            ],
            [
                InlineKeyboardButton(f"{mark('document')} Документы", callback_data="set_document"),
                InlineKeyboardButton(f"{mark('audio')} Аудио", callback_data="set_audio"),
            ],
            [InlineKeyboardButton(f"{mark('animation')} GIF", callback_data="set_animation")],
            [InlineKeyboardButton(f"{EMOJI_BACK} Вернуться назад", callback_data="back_menu")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _settings_text(self) -> str:
        return (
            f"{EMOJI_GEAR} <b>Общие настройки</b>\n\n"
            "<b>Типы уведомлений:</b>\n"
            "• Удалённые — копии удалённых сообщений\n"
            "• Изменённые — уведомления о правках\n"
            "• Одноразовые — копия только для медиа «1 просмотр» (по ответу)\n\n"
            "<b>Форматы</b> (только для удалённых):\n"
            "какие типы медиа присылать при удалении.\n\n"
            f"{EMOJI_CHECK} — включено {EMOJI_CROSS} — выключено\n"
            "Нажмите на пункт, чтобы переключить."
        )

    async def send_start_message(self, bot, chat_id: int) -> None:
        try:
            await bot.send_sticker(chat_id=chat_id, sticker=STICKER_ID)
        except Exception:
            pass

        await bot.send_message(
            chat_id=chat_id,
            text=self.get_start_text(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=self.get_main_keyboard(),
        )

    # ----- connections -----

    async def resolve_connection_user(self, bot, connection_id: str | None) -> int | None:
        if not connection_id:
            return None
        user_id = self.connections.get_user(connection_id)
        if user_id:
            return user_id
        try:
            conn = await bot.get_business_connection(connection_id)
            if conn and conn.user:
                self.connections.save(connection_id, conn.user.id)
                return conn.user.id
        except Exception as e:
            logger.error(
                "get_business_connection(%s) failed: %s",
                connection_id,
                type(e).__name__,
            )
        return None

    # ----- commands / menu -----

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_chat:
            return
        await self.send_start_message(context.bot, update.effective_chat.id)

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query:
            return

        await query.answer()

        data = query.data
        user_id = query.from_user.id if query.from_user else OWNER_ID

        if data and data.startswith("set_"):
            key = data[4:]
            current = self.settings.is_enabled(user_id, key)
            self.settings.set(user_id, key, not current)
            try:
                await query.message.edit_text(
                    text=self._settings_text(),
                    parse_mode=ParseMode.HTML,
                    reply_markup=self._settings_keyboard(user_id),
                )
            except Exception:
                await query.message.reply_text(
                    text=self._settings_text(),
                    parse_mode=ParseMode.HTML,
                    reply_markup=self._settings_keyboard(user_id),
                )
            return

        if data == "settings_menu":
            await query.message.reply_text(
                text=self._settings_text(),
                parse_mode=ParseMode.HTML,
                reply_markup=self._settings_keyboard(user_id),
            )
            return

        if data == "info_how":
            text = (
                f"{EMOJI_INFO} <b>Как работает бот</b>\n\n"
                "1. Подключаешь бота в настройках <b>Автоматизация чатов</b>\n"
                "2. Выбираешь чаты, которые нужно отслеживать\n"
                "3. Бот автоматически сохраняет все сообщения в память\n"
                "4. При удалении или изменении — сразу присылает тебе копию\n\n"
                f"{EMOJI_CAMERA} <b>Одноразовые фото / видео / кружки:</b>\n"
                "Ответь на сообщение с пометкой <b>1 просмотр</b>, <b>не открывая</b> его — "
                "бот скачает медиа и пришлёт постоянную копию сюда.\n"
                "На обычные голосовые/фото ответ <b>не</b> создаёт копию.\n\n"
                "Удаления и правки работают в фоне сами."
            )
        elif data == "info_delete":
            text = (
                f"{EMOJI_TRASH} <b>Уведомления об удалении</b>\n\n"
                "Когда кто-то удаляет сообщение в отслеживаемом чате, "
                "бот присылает тебе его копию:\n\n"
                "• Текст\n"
                "• Фото и видео\n"
                "• Голосовые и кружки\n"
                "• Документы и стикеры\n"
                "• Геолокацию, контакты и опросы\n\n"
                "Вместе с сообщением указывается <b>автор</b>."
            )
        elif data == "info_edit":
            text = (
                f"{EMOJI_EDIT} <b>Уведомления об изменении</b>\n\n"
                "Если сообщение отредактировали, бот покажет:\n\n"
                "• <b>Старое</b> содержимое\n"
                "• <b>Новое</b> (изменённое) содержимое\n"
                "• Кто именно изменил сообщение\n\n"
                "Так ты всегда видишь, что пытались скрыть."
            )
        elif data == "info_privacy":
            text = (
                f"{EMOJI_LOCK} <b>Приватность</b>\n\n"
                "• Все сообщения хранятся <b>только в оперативной памяти</b>\n"
                "• Никаких баз данных и файлов на сервере\n"
                "• После перезапуска бота память полностью очищается\n"
                "• Никто кроме тебя не получает уведомления\n\n"
                "Максимальная приватность."
            )
        elif data == "info_connect":
            text = (
                f"{EMOJI_GEAR} <b>Инструкция по подключению бота</b>\n"
                f"{EMOJI_STAR} <b>Telegram Premium не нужен</b>\n\n"
                "1. Откройте настройки в Telegram → <b>«Изм.»</b> сверху\n"
                "2. Пролистайте до раздела <b>«Автоматизация чатов»</b> и откройте его\n"
                "3. Вставьте в поле юзернейм бота и нажмите <b>«Добавить»</b>\n"
                "4. Выберите чаты, которые нужно отслеживать\n\n"
                "<blockquote>После подключения вам будут автоматически приходить "
                "изменённые и удалённые сообщения.</blockquote>\n\n"
                "<blockquote expandable>"
                "ℹ️ <b>Бот получил доступ к моим чатам и появился в сессиях, это что?</b>\n\n"
                "После добавления Telegram покажет системное уведомление "
                "«Бот получил доступ к вашим чатам» — <b>не пугайтесь</b>, "
                "это стандартное сообщение.\n\n"
                "Бот также появится в разделе активных сессий как "
                "«Бот для автоматизации» — это тоже нормально и полностью безопасно.\n\n"
                "Коротко и понятно, <b>почему это безопасно</b>:\n"
                "• Бот видит только те чаты, которые вы сами выбрали\n"
                "• Он не может писать от вашего имени без вашего ведома\n"
                "• Все данные хранятся только в оперативной памяти и исчезают после перезапуска\n"
                "• Отключить бота можно в любой момент в настройках «Автоматизация чатов»"
                "</blockquote>"
            )
            keyboard = [
                [InlineKeyboardButton(
                    "📋 Скопировать юзернейм",
                    copy_text=CopyTextButton(text=BOT_USERNAME),
                )],
                [InlineKeyboardButton(f"{EMOJI_BACK} Вернуться назад", callback_data="back_menu")],
            ]
            if CONNECT_PHOTO_ID:
                try:
                    await query.message.reply_photo(
                        photo=CONNECT_PHOTO_ID,
                        caption=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                    )
                    return
                except Exception as e:
                    logger.error("Не удалось отправить фото подключения: %s", type(e).__name__)

            await query.message.reply_text(
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        elif data == "back_menu":
            try:
                await query.message.delete()
            except Exception:
                pass
            return
        else:
            text = "Неизвестная команда"

        keyboard = [
            [InlineKeyboardButton(f"{EMOJI_BACK} Вернуться назад", callback_data="back_menu")],
        ]
        await query.message.reply_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    # ----- business messages -----

    async def on_business_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        message = update.business_message
        if not message:
            return

        data = extract_message_data(message)
        notify_user = await self.resolve_connection_user(
            context.bot, message.business_connection_id
        )
        data["notify_user_id"] = notify_user
        data["business_connection_id"] = message.business_connection_id

        self.messages.store(
            message.business_connection_id or "",
            message.chat.id,
            message.message_id,
            data,
        )
        self.messages.cleanup_old(max_size=4000)

        await self.maybe_save_view_once_on_reply(context, message, notify_user)

    async def maybe_save_view_once_on_reply(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        message,
        notify_user: int | None,
    ) -> None:
        if not notify_user or not message.from_user:
            return
        if message.from_user.id != notify_user:
            return
        if not self.settings.is_enabled(notify_user, "view_once"):
            return

        replied = message.reply_to_message
        if not replied:
            return
        if replied.from_user and replied.from_user.id == notify_user:
            return

        data = extract_message_data(replied)
        content_type = data.get("content_type")
        if content_type not in VIEW_ONCE_MEDIA_TYPES or not data.get("file_id"):
            conn_id = message.business_connection_id or ""
            stored = self.messages.get(conn_id, replied.chat.id, replied.message_id)
            if not stored:
                return
            content_type = stored.get("content_type")
            if content_type not in VIEW_ONCE_MEDIA_TYPES or not stored.get("file_id"):
                return
            if not stored.get("is_view_once") and data.get("is_view_once"):
                stored = {**stored, "is_view_once": True, "has_protected_content": True}
            data = stored

        is_view_once = bool(data.get("is_view_once")) or is_view_once_media(replied)
        if not is_view_once:
            return

        data["notify_user_id"] = notify_user
        sender = data.get("sender_name") or get_sender_display(replied)
        header = (
            f"{EMOJI_CAMERA} <b>Сохранено медиа от {sender}</b>\n"
            f"<code>одноразовое / по ответу</code>"
        )
        await self.send_media_copy(context, data, header, reupload=True)

    async def _media_payload(
        self, bot, file_id: str, file_name: str | None, *, reupload: bool
    ):
        if not reupload:
            return file_id
        try:
            tg_file = await bot.get_file(file_id)
            buf = BytesIO()
            await tg_file.download_to_memory(out=buf)
            buf.seek(0)
            name = file_name
            if not name and tg_file.file_path:
                name = tg_file.file_path.rsplit("/", 1)[-1]
            if name:
                buf.name = name
            return buf
        except Exception as e:
            logger.error("Не удалось скачать медиа: %s", type(e).__name__)
            return file_id

    async def send_media_copy(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        data: dict,
        header: str,
        *,
        reupload: bool = False,
        text_label: str = "Текст",
    ) -> None:
        bot = context.bot
        content_type = data.get("content_type")
        file_id = data.get("file_id")
        caption_text = data.get("caption")
        text_content = data.get("text")
        target = data.get("notify_user_id")
        if not target:
            logger.error("send_media_copy: нет notify_user_id")
            return

        try:
            if content_type == "text":
                full_text = f"{header}\n\n<b>{text_label}:</b> {text_content or ''}"
                await bot.send_message(
                    chat_id=target,
                    text=full_text,
                    parse_mode=ParseMode.HTML,
                )
                return

            if not file_id:
                extra = text_content or "[Медиа недоступно]"
                await bot.send_message(
                    chat_id=target,
                    text=f"{header}\n\n{extra}",
                    parse_mode=ParseMode.HTML,
                )
                return

            payload = await self._media_payload(
                bot,
                file_id,
                data.get("file_name"),
                reupload=reupload,
            )
            caption = header
            if caption_text:
                caption += f"\n\n<b>Подпись:</b> {caption_text}"

            if content_type == "photo":
                await bot.send_photo(
                    chat_id=target, photo=payload, caption=caption, parse_mode=ParseMode.HTML
                )
            elif content_type == "video":
                await bot.send_video(
                    chat_id=target, video=payload, caption=caption, parse_mode=ParseMode.HTML
                )
            elif content_type == "document":
                await bot.send_document(
                    chat_id=target, document=payload, caption=caption, parse_mode=ParseMode.HTML
                )
            elif content_type == "voice":
                await bot.send_voice(
                    chat_id=target, voice=payload, caption=caption, parse_mode=ParseMode.HTML
                )
            elif content_type == "audio":
                await bot.send_audio(
                    chat_id=target, audio=payload, caption=caption, parse_mode=ParseMode.HTML
                )
            elif content_type == "animation":
                await bot.send_animation(
                    chat_id=target, animation=payload, caption=caption, parse_mode=ParseMode.HTML
                )
            elif content_type == "sticker":
                info_msg = await bot.send_message(
                    chat_id=target, text=header, parse_mode=ParseMode.HTML
                )
                await bot.send_sticker(
                    chat_id=target,
                    sticker=payload if isinstance(payload, str) else file_id,
                    reply_to_message_id=info_msg.message_id,
                )
            elif content_type == "video_note":
                info_msg = await bot.send_message(
                    chat_id=target, text=header, parse_mode=ParseMode.HTML
                )
                await bot.send_video_note(
                    chat_id=target,
                    video_note=payload,
                    reply_to_message_id=info_msg.message_id,
                )
            else:
                extra = text_content or "[Тип сообщения не удалось полностью восстановить]"
                await bot.send_message(
                    chat_id=target,
                    text=f"{header}\n\n{extra}",
                    parse_mode=ParseMode.HTML,
                )
        except Exception as e:
            logger.error("Ошибка при отправке копии медиа: %s", type(e).__name__)

    async def on_edited_business_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        message = update.edited_business_message
        if not message:
            return

        chat_id = message.chat.id
        msg_id = message.message_id
        conn_id = message.business_connection_id or ""
        old_data = self.messages.get(conn_id, chat_id, msg_id)
        new_data = extract_message_data(message)

        notify_user = await self.resolve_connection_user(
            context.bot, message.business_connection_id
        )
        if notify_user is None and old_data:
            notify_user = old_data.get("notify_user_id")
        new_data["notify_user_id"] = notify_user

        self.messages.store(conn_id, chat_id, msg_id, new_data)

        if not notify_user:
            return
        if not self.settings.is_enabled(notify_user, "edited"):
            return

        sender_id = new_data.get("sender_id") or (
            old_data.get("sender_id") if old_data else None
        )
        if sender_id is not None and sender_id == notify_user:
            return
        if not old_data:
            return

        sender = new_data.get("sender_name") or get_sender_display(message)
        header = f"{EMOJI_EDIT} <b>Изменено сообщение от {sender}</b>"
        old_text = old_data.get("text") or old_data.get("caption") or ""
        new_text = new_data.get("text") or new_data.get("caption") or ""

        if old_text == new_text and old_data.get("file_id") == new_data.get("file_id"):
            return

        try:
            body = (
                f"{header}\n\n"
                f"<b>Старое:</b> {old_text or '—'}\n"
                f"<b>Новое:</b> {new_text or '—'}"
            )
            await context.bot.send_message(
                chat_id=notify_user,
                text=body,
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            logger.error(
                "Ошибка при отправке уведомления об изменении: %s", type(e).__name__
            )

    async def on_deleted_business_messages(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        deleted = update.deleted_business_messages
        if not deleted:
            return

        chat_id = deleted.chat.id
        message_ids = deleted.message_ids
        conn_id = getattr(deleted, "business_connection_id", None)
        notify_from_conn = await self.resolve_connection_user(context.bot, conn_id)

        for msg_id in message_ids:
            data = self.messages.pop(conn_id or "", chat_id, msg_id)
            if not data:
                continue

            notify_user = data.get("notify_user_id") or notify_from_conn
            if not notify_user:
                continue

            sender_id = data.get("sender_id")
            if sender_id is not None and sender_id == notify_user:
                continue
            if not self.settings.is_enabled(notify_user, "deleted"):
                continue

            ctype = data.get("content_type") or "other"
            setting_key = ctype if ctype in DEFAULT_SETTINGS else "other"
            if not self.settings.is_enabled(notify_user, setting_key):
                continue

            data["notify_user_id"] = notify_user
            await self.send_deleted_copy(context, data)

    async def send_deleted_copy(
        self, context: ContextTypes.DEFAULT_TYPE, data: dict
    ) -> None:
        sender = data.get("sender_name", "Неизвестный")
        header = f"{EMOJI_TRASH} <b>Удалено сообщение от {sender}</b>"
        await self.send_media_copy(
            context, data, header, reupload=False, text_label="Удалённый текст"
        )

    async def on_business_connection(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        conn = update.business_connection
        if not conn:
            return

        user_id = conn.user.id if conn.user else None
        if conn.is_enabled and user_id:
            self.connections.save(conn.id, user_id)
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "✅ Бот подключён к вашему аккаунту.\n"
                        "Уведомления об удалении и изменении сообщений будут приходить <b>сюда</b>."
                    ),
                    parse_mode=ParseMode.HTML,
                )
            except Exception as e:
                logger.error(
                    "Не удалось написать user_id=%s: %s", user_id, type(e).__name__
                )
        else:
            self.connections.remove(conn.id)

    async def error_handler(
        self, update: object, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        logger.error("Ошибка: %s", context.error)


# Экземпляр по умолчанию (для main и совместимости)
handlers = BotHandlers()

# Совместимые имена для регистрации / тестов
start_command = handlers.start_command
button_handler = handlers.button_handler
on_business_message = handlers.on_business_message
on_edited_business_message = handlers.on_edited_business_message
on_deleted_business_messages = handlers.on_deleted_business_messages
on_business_connection = handlers.on_business_connection
error_handler = handlers.error_handler
maybe_save_view_once_on_reply = handlers.maybe_save_view_once_on_reply
