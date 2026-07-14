from telegram import ReplyKeyboardMarkup


EMPLOYEE_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📅 בקשות", "📋 הבקשות שלי"],
        ["🤒 דיווח מחלה", "🔄 החלפת משמרת"],
        ["ℹ️ מידע", "🚪 יציאה"],
    ],
    resize_keyboard=True,
)


def get_employee_keyboard():
    return EMPLOYEE_KEYBOARD