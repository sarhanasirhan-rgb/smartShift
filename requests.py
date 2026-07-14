from telegram import ReplyKeyboardMarkup


REQUESTS_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["➕ בקשת משמרת"],
        ["📋 הבקשות שלי", "🗑️ מחק בקשה"],
        ["⬅️ חזרה"],
    ],
    resize_keyboard=True,
)


DAYS_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["ראשון", "שני"],
        ["שלישי", "רביעי"],
        ["חמישי", "שישי"],
        ["שבת"],
        ["⬅️ חזרה"],
    ],
    resize_keyboard=True,
)


SHIFT_TYPE_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🌅 בוקר", "🌆 ערב"],
        ["🌙 לילה", "🚫 לא יכול"],
        ["⬅️ חזרה"],
    ],
    resize_keyboard=True,
)


def get_requests_keyboard():
    return REQUESTS_KEYBOARD


def get_days_keyboard():
    return DAYS_KEYBOARD


def get_shift_type_keyboard():
    return SHIFT_TYPE_KEYBOARD