from telegram import ReplyKeyboardMarkup

MANAGER_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📥 בקשות לשבוע הבא", "👥 עובדים"],
        ["🤒 דיווחי מחלה", "🔄 החלפות"],
        ["📊 מצב השבוע"],
        ["🚪 יציאה"],
    ],
    resize_keyboard=True,
)

def get_manager_keyboard():
    return MANAGER_KEYBOARD