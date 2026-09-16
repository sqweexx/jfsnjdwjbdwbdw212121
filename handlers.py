import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton, InputMediaPhoto
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import storage
from utils import extract_message_data, get_sender_display
from config import OWNER_ID

logger = logging.getLogger(__name__)

# ===== НАСТРОЙКИ =====
# Стикер приветствия
STICKER_ID = "CAACAgIAAxkBAAER5nNqp6RsqLUnkBXIXNm3_WuXCkRkzwACLgADJHFiGojoNkNqQEMUPQQ"

BOT_USERNAME = "@delete_message_monitor_bot"

# Фото для раздела «Подключение» (file_id картинки с инструкцией)
# Получить file_id: отправь фото боту @idstickerbot / @getidsbot или своему боту в лог
CONNECT_PHOTO_ID = "AgACAgIAAxkBAAIBHmqqho0TJpCxQaqqREhn9eiYbH61AAJwHmsbYMJQSSfCRgRs6gm7AQADAgADeQADPQQ"

# Фото для раздела «Бот получил доступ к чатам» (можно несколько)
SESSION_PHOTO_IDS: list[str] = [
    # "AgACAgIAAxkBAAI...",  # ← file_id фото 1
    # "AgACAgIAAxkBAAI...",  # ← file_id фото 2
]

# Premium-эмодзи для текста (HTML)
# Формат: <tg-emoji emoji-id="ID">fallback</tg-emoji>
EMOJI_EDIT = '<tg-emoji emoji-id="5334882760735598374">✏️</tg-emoji>'
EMOJI_TRASH = '<tg-emoji emoji-id="5445267414562389170">🗑</tg-emoji>'
EMOJI_CAMERA = '<tg-emoji emoji-id="5429365504307383204">📷</tg-emoji>'
EMOJI_LOCK = '<tg-emoji emoji-id="5296369303661067030">🔒</tg-emoji>'
EMOJI_STAR = '<tg-emoji emoji-id="5348570868752595928">⭐</tg-emoji>'
EMOJI_GEAR = '<tg-emoji emoji-id="5341715473882955310">⚙️</tg-emoji>'
EMOJI_INFO = '<tg-emoji emoji-id="5334544901428229844">ℹ️</tg-emoji>'
EMOJI_BACK = "↩️"
EMOJI_CHECK = "✅"
EMOJI_CROSS = "❌"

# Premium-эмодзи для кнопок (icon_custom_emoji_id)
BTN_EMOJI_HOW = "6021618194228187816"
BTN_EMOJI_DELETE = "5879896690210639947"
BTN_EMOJI_EDIT = "5879841310902324730"
BTN_EMOJI_PRIVACY = "5778570255555105942"
BTN_EMOJI_CONNECT = "5429295556469999475"
BTN_EMOJI_SETTINGS = "5904258298764334001"



async def resolve_connection_user(bot, connection_id: str | None) -> int | None:
    """user_id владельца business-подключения. Тянет из кэша или через API."""
    if not connection_id:
        return None
    user_id = storage.get_connection_user(connection_id)
    if user_id:
        return user_id
    try:
        conn = await bot.get_business_connection(connection_id)
        if conn and conn.user:
            storage.save_connection(connection_id, conn.user.id)
            logger.info(
                "Connection восстановлен через API: id=%s user_id=%s",
                connection_id,
                conn.user.id,
            )
            return conn.user.id
    except Exception as e:
        logger.error(
            "get_business_connection(%s) failed: %s",
            connection_id,
            type(e).__name__,
        )
    return None


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню кнопок"""
    # icon_custom_emoji_id не поддерживается в текущей версии PTB —
    # на кнопках используем обычные эмодзи, premium — в тексте сообщений
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


def get_start_text() -> str:
    return (
        f"<b>!!!Добро пожаловать в <u>MessageSaver</u> Bot!</b>\n\n"
        f"С <b>MessageSaver</b> вы мгновенно увидите все ключевые события:\n\n"
        
        f"{EMOJI_EDIT} <b>Редактирование сообщений:</b>\n"
        f"— Показываю <b>старое</b> сообщение и <b>новое</b> (изменённое)\n"
        f"— Указываю автора и его @username\n\n"
        
        f"{EMOJI_TRASH} <b>Удаление сообщений:</b>\n"
        f"— Пересылаю любые форматы: текст, фото, видео, кружки, стикеры, документы, локации...\n\n"
        
        f"{EMOJI_CAMERA} <b>Медиафайлы:</b>\n"
        f"— Сохраняю фото, видео, голосовые, документы и стикеры\n"
        f"— Присылаю их вам вместе с информацией об отправителе\n\n"
        
        f"{EMOJI_LOCK} <b>Приватность:</b>\n"
        f"— Все данные хранятся только в оперативной памяти\n"
        f"— После перезапуска бота ничего не остаётся на сервере\n\n"
        
        f"{EMOJI_STAR} <b>Telegram Premium не нужен</b>\n"
        f"Базовые функции работают полностью бесплатно"
    )


async def send_start_message(bot, chat_id: int) -> None:
    """Отправляет стикер + приветствие + меню (как при /start)"""
    try:
        await bot.send_sticker(chat_id=chat_id, sticker=STICKER_ID)
    except Exception:
        pass

    await bot.send_message(
        chat_id=chat_id,
        text=get_start_text(),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=get_main_keyboard(),
    )



async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Красивое приветствие при /start"""
    if not update.message or not update.effective_chat:
        return

    await send_start_message(context.bot, update.effective_chat.id)


def _settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    s = storage.get_settings(user_id)

    def mark(key: str) -> str:
        return EMOJI_CHECK if s.get(key, True) else EMOJI_CROSS

    keyboard = [
        [InlineKeyboardButton(f"{mark('deleted')} Удалённые сообщения", callback_data="set_deleted")],
        [InlineKeyboardButton(f"{mark('edited')} Изменённые сообщения", callback_data="set_edited")],
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


def _settings_text() -> str:
    return (
        f"{EMOJI_GEAR} <b>Общие настройки</b>\n\n"
        "<b>Типы уведомлений:</b>\n"
        "• Удалённые — копии удалённых сообщений\n"
        "• Изменённые — уведомления о правках\n\n"
        "<b>Форматы</b> (только для удалённых):\n"
        "какие типы медиа присылать при удалении.\n\n"
        f"{EMOJI_CHECK} — включено {EMOJI_CROSS} — выключено\n"
        "Нажмите на пункт, чтобы переключить."
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка нажатий на кнопки меню"""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    data = query.data
    chat_id = query.message.chat_id if query.message else None
    user_id = query.from_user.id if query.from_user else OWNER_ID

    # --- Настройки: переключение ---
    if data and data.startswith("set_"):
        key = data[4:]  # set_deleted -> deleted
        current = storage.is_enabled(user_id, key)
        storage.set_setting(user_id, key, not current)
        try:
            await query.message.edit_text(
                text=_settings_text(),
                parse_mode=ParseMode.HTML,
                reply_markup=_settings_keyboard(user_id),
            )
        except Exception:
            await query.message.reply_text(
                text=_settings_text(),
                parse_mode=ParseMode.HTML,
                reply_markup=_settings_keyboard(user_id),
            )
        return

    if data == "settings_menu":
        await query.message.reply_text(
            text=_settings_text(),
            parse_mode=ParseMode.HTML,
            reply_markup=_settings_keyboard(user_id),
        )
        return

    if data == "info_how":
        text = (
            f"{EMOJI_INFO} <b>Как работает бот</b>\n\n"
            "1. Подключаешь бота в настройках <b>Автоматизация чатов</b>\n"
            "2. Выбираешь чаты, которые нужно отслеживать\n"
            "3. Бот автоматически сохраняет все сообщения в память\n"
            "4. При удалении или изменении — сразу присылает тебе копию\n\n"
            "Всё работает в фоне, ничего дополнительно нажимать не нужно."
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
            "<blockquote>После подключения вам будут автоматически приходить изменённые и удалённые сообщения.</blockquote>\n\n"
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

        # Если есть фото инструкции — отправляем с подписью
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
        # Удаляем только сообщение раздела, основное меню остаётся
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


async def on_business_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.business_message
    if not message:
        return

    logger.info(
        "Получено бизнес-сообщение: chat_id=%s message_id=%s conn=%s",
        message.chat.id,
        message.message_id,
        message.business_connection_id,
    )

    data = extract_message_data(message)

    # Уведомления только владельцу business-подключения
    notify_user = await resolve_connection_user(context.bot, message.business_connection_id)
    data["notify_user_id"] = notify_user
    data["business_connection_id"] = message.business_connection_id

    if notify_user is None:
        logger.warning(
            "Нет user_id для connection_id=%s",
            message.business_connection_id,
        )

    storage.store(message.business_connection_id or "", message.chat.id, message.message_id, data)
    storage.cleanup_old(max_size=4000)


async def on_edited_business_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.edited_business_message
    if not message:
        return

    chat_id = message.chat.id
    msg_id = message.message_id

    conn_id = message.business_connection_id or ""
    old_data = storage.get(conn_id, chat_id, msg_id)
    new_data = extract_message_data(message)

    notify_user = await resolve_connection_user(context.bot, message.business_connection_id)
    if notify_user is None and old_data:
        notify_user = old_data.get("notify_user_id")
    new_data["notify_user_id"] = notify_user

    storage.store(conn_id, chat_id, msg_id, new_data)

    if not notify_user:
        logger.info("Нет получателя для edited message_id=%s", msg_id)
        return

    if not storage.is_enabled(notify_user, "edited"):
        return

    # Не уведомлять о своих правках
    sender_id = new_data.get("sender_id") or (old_data.get("sender_id") if old_data else None)
    if sender_id is not None and sender_id == notify_user:
        logger.info("Пропуск своего редактирования message_id=%s user=%s", msg_id, notify_user)
        return

    if not old_data:
        logger.info("Отредактированное сообщение %s не найдено в RAM", msg_id)
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
        logger.info("Уведомление об изменении отправлено user=%s message_id=%s", notify_user, msg_id)
    except Exception as e:
        logger.error("Ошибка при отправке уведомления об изменении: %s", type(e).__name__)


async def on_deleted_business_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    deleted = update.deleted_business_messages
    if not deleted:
        return

    chat_id = deleted.chat.id
    message_ids = deleted.message_ids

    # Получатель: из connection_id удаления (если есть) или из сохранённого сообщения
    conn_id = getattr(deleted, "business_connection_id", None)
    notify_from_conn = await resolve_connection_user(context.bot, conn_id)

    logger.info(
        "Удалены бизнес-сообщения: chat_id=%s count=%s conn=%s",
        chat_id,
        len(message_ids),
        conn_id,
    )

    for msg_id in message_ids:
        data = storage.pop(conn_id or "", chat_id, msg_id)
        if not data:
            logger.info("Сообщение %s не найдено в RAM", msg_id)
            continue

        notify_user = data.get("notify_user_id") or notify_from_conn
        if not notify_user:
            logger.info("Нет получателя для deleted message_id=%s — пропуск", msg_id)
            continue

        # Не уведомлять о своих же сообщениях — только когда удалил собеседник
        sender_id = data.get("sender_id")
        if sender_id is not None and sender_id == notify_user:
            logger.info("Пропуск своего сообщения message_id=%s user=%s", msg_id, notify_user)
            continue

        if not storage.is_enabled(notify_user, "deleted"):
            continue

        ctype = data.get("content_type") or "other"
        setting_key = ctype if ctype in storage.DEFAULT_SETTINGS else "other"
        if not storage.is_enabled(notify_user, setting_key):
            continue

        data["notify_user_id"] = notify_user
        await send_deleted_copy(context, data)


async def send_deleted_copy(context: ContextTypes.DEFAULT_TYPE, data: dict) -> None:
    bot = context.bot
    sender = data.get("sender_name", "Неизвестный")
    content_type = data.get("content_type")
    file_id = data.get("file_id")
    caption_text = data.get("caption")
    text_content = data.get("text")
    target = data.get("notify_user_id")
    if not target:
        logger.error("send_deleted_copy: нет notify_user_id")
        return

    header = f"{EMOJI_TRASH} <b>Удалено сообщение от {sender}</b>"

    try:
        if content_type == "text":
            full_text = f"{header}\n\n<b>Удалённый текст:</b> {text_content or ''}"
            await bot.send_message(
                chat_id=target,
                text=full_text,
                parse_mode=ParseMode.HTML,
            )

        elif content_type == "photo" and file_id:
            caption = header
            if caption_text:
                caption += f"\n\n<b>Подпись:</b> {caption_text}"
            await bot.send_photo(chat_id=target, photo=file_id, caption=caption, parse_mode=ParseMode.HTML)

        elif content_type == "video" and file_id:
            caption = header
            if caption_text:
                caption += f"\n\n<b>Подпись:</b> {caption_text}"
            await bot.send_video(chat_id=target, video=file_id, caption=caption, parse_mode=ParseMode.HTML)

        elif content_type == "document" and file_id:
            caption = header
            if caption_text:
                caption += f"\n\n<b>Подпись:</b> {caption_text}"
            await bot.send_document(chat_id=target, document=file_id, caption=caption, parse_mode=ParseMode.HTML)

        elif content_type == "voice" and file_id:
            caption = header
            if caption_text:
                caption += f"\n\n<b>Подпись:</b> {caption_text}"
            await bot.send_voice(chat_id=target, voice=file_id, caption=caption, parse_mode=ParseMode.HTML)

        elif content_type == "audio" and file_id:
            caption = header
            if caption_text:
                caption += f"\n\n<b>Подпись:</b> {caption_text}"
            await bot.send_audio(chat_id=target, audio=file_id, caption=caption, parse_mode=ParseMode.HTML)

        elif content_type == "animation" and file_id:
            caption = header
            if caption_text:
                caption += f"\n\n<b>Подпись:</b> {caption_text}"
            await bot.send_animation(chat_id=target, animation=file_id, caption=caption, parse_mode=ParseMode.HTML)

        elif content_type == "sticker" and file_id:
            info_msg = await bot.send_message(chat_id=target, text=header, parse_mode=ParseMode.HTML)
            await bot.send_sticker(
                chat_id=target,
                sticker=file_id,
                reply_to_message_id=info_msg.message_id,
            )

        elif content_type == "video_note" and file_id:
            info_msg = await bot.send_message(chat_id=target, text=header, parse_mode=ParseMode.HTML)
            await bot.send_video_note(
                chat_id=target,
                video_note=file_id,
                reply_to_message_id=info_msg.message_id,
            )

        else:
            extra = text_content or "[Тип сообщения не удалось полностью восстановить]"
            await bot.send_message(
                chat_id=target,
                text=f"{header}\n\n{extra}",
                parse_mode=ParseMode.HTML,
            )

        logger.info("Копия удалённого сообщения отправлена (тип: %s)", content_type)

    except Exception as e:
        logger.error("Ошибка при отправке копии: %s", type(e).__name__)


async def on_business_connection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = update.business_connection
    if not conn:
        return

    user_id = conn.user.id if conn.user else None
    if conn.is_enabled and user_id:
        storage.save_connection(conn.id, user_id)
        logger.info("Business connection включено: id=%s user_id=%s", conn.id, user_id)
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
            logger.error("Не удалось написать user_id=%s: %s", user_id, type(e).__name__)
    else:
        storage.remove_connection(conn.id)
        logger.info("Business connection отключено: id=%s", conn.id)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Ошибка: %s", context.error)
