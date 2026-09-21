"""UI-константы бота (общий стиль)."""

# Медиа, которое можно сохранить по ответу (одноразовые фото/видео/кружки и т.п.)
VIEW_ONCE_MEDIA_TYPES = frozenset({
    "photo",
    "video",
    "video_note",
    "voice",
    "audio",
    "document",
    "animation",
})

# Стикер приветствия
STICKER_ID = "CAACAgIAAxkBAAER5nNqp6RsqLUnkBXIXNm3_WuXCkRkzwACLgADJHFiGojoNkNqQEMUPQQ"

BOT_USERNAME = "@delete_message_monitor_bot"

# Фото для раздела «Подключение» (file_id картинки с инструкцией)
CONNECT_PHOTO_ID = "AgACAgIAAxkBAAIBHmqqho0TJpCxQaqqREhn9eiYbH61AAJwHmsbYMJQSSfCRgRs6gm7AQADAgADeQADPQQ"

# Фото для раздела «Бот получил доступ к чатам» (можно несколько)
SESSION_PHOTO_IDS: list[str] = [
    # "AgACAgIAAxkBAAI...",
]

# Premium-эмодзи для текста (HTML)
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

# Premium-эмодзи для кнопок (icon_custom_emoji_id) — на будущее
BTN_EMOJI_HOW = "6021618194228187816"
BTN_EMOJI_DELETE = "5879896690210639947"
BTN_EMOJI_EDIT = "5879841310902324730"
BTN_EMOJI_PRIVACY = "5778570255555105942"
BTN_EMOJI_CONNECT = "5429295556469999475"
BTN_EMOJI_SETTINGS = "5904258298764334001"
