from datetime import date, timedelta

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import TOKEN
from auth import is_manager_code, normalize_code
from employee import get_employee_keyboard
from requests import (
    get_requests_keyboard,
    get_days_keyboard,
    get_shift_type_keyboard,
)

from database import (
    create_tables,
    get_employees,
    get_employee,
    authenticate_employee,
    set_employee_credentials,
    add_shift_request,
    get_employee_requests,
    delete_shift_request,
    get_week_requests,
)


create_tables()


START_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["👨‍💼 כניסת מנהל"],
        ["👷 כניסת עובד"],
    ],
    resize_keyboard=True,
)


MANAGER_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📥 בקשות לשבוע הבא", "👥 רשימת עובדים"],
        ["🔐 הגדרת כניסה לעובד"],
        ["🤒 דיווחי מחלה", "🔄 החלפות"],
        ["📊 מצב השבוע"],
        ["🚪 יציאה"],
    ],
    resize_keyboard=True,
)


DAYS = [
    "ראשון",
    "שני",
    "שלישי",
    "רביעי",
    "חמישי",
    "שישי",
    "שבת",
]


REQUEST_TYPES = {
    "🌅 בוקר": "בוקר",
    "🌆 ערב": "ערב",
    "🌙 לילה": "לילה",
    "🚫 לא יכול": "לא יכול לעבוד",
}


def get_next_week_start():
    today = date.today()

    # בפייתון יום ראשון הוא 6
    days_until_sunday = (6 - today.weekday()) % 7

    if days_until_sunday == 0:
        days_until_sunday = 7

    next_sunday = today + timedelta(
        days=days_until_sunday
    )

    return next_sunday.isoformat()


def format_date(date_text):
    year, month, day = date_text.split("-")
    return f"{day}/{month}/{year}"


async def show_employee_list(update: Update):
    employees = get_employees()

    if not employees:
        await update.message.reply_text(
            "עדיין אין עובדים במערכת."
        )
        return False

    lines = []

    for employee_id, name, employee_number in employees:
        number_text = (
            employee_number
            if employee_number
            else "טרם הוגדר"
        )

        lines.append(
            f"{employee_id}. {name}\n"
            f"מספר עובד: {number_text}"
        )

    await update.message.reply_text(
        "👥 רשימת עובדים:\n\n"
        + "\n\n".join(lines)
    )

    return True


async def show_my_requests(
    update: Update,
    employee_id: int,
):
    week_start = get_next_week_start()

    employee_requests = get_employee_requests(
        employee_id,
        week_start,
    )

    if not employee_requests:
        await update.message.reply_text(
            "עדיין אין לך בקשות לשבוע הבא."
        )
        return False

    lines = []

    for (
        request_id,
        day_name,
        request_type,
        status,
    ) in employee_requests:
        lines.append(
            f"{request_id}. {day_name} — {request_type}"
        )

    remaining = 3 - len(employee_requests)

    await update.message.reply_text(
        "הבקשות שלך לשבוע שמתחיל ב־"
        f"{format_date(week_start)}:\n\n"
        + "\n".join(lines)
        + f"\n\nנותרו לך {remaining} מתוך 3 בקשות."
    )

    return True


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    await update.message.reply_text(
        "ברוך הבא למערכת שינוע.\n"
        "בחר סוג כניסה:",
        reply_markup=START_KEYBOARD,
    )


async def handle_manager(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
):
    action = context.user_data.get("action")

    if text == "📥 בקשות לשבוע הבא":
        week_start = get_next_week_start()
        week_requests = get_week_requests(week_start)

        if not week_requests:
            await update.message.reply_text(
                "אין עדיין בקשות לשבוע הבא."
            )
            return

        lines = []

        for (
            request_id,
            employee_name,
            day_name,
            request_type,
            status,
        ) in week_requests:
            lines.append(
                f"{request_id}. {employee_name} — "
                f"{day_name} — {request_type}"
            )

        await update.message.reply_text(
            "📥 בקשות לשבוע שמתחיל ב־"
            f"{format_date(week_start)}:\n\n"
            + "\n".join(lines)
        )
        return

    if text == "👥 רשימת עובדים":
        context.user_data["action"] = None
        await show_employee_list(update)
        return

    if text == "🔐 הגדרת כניסה לעובד":
        has_employees = await show_employee_list(update)

        if not has_employees:
            return

        context.user_data["action"] = (
            "choose_employee_credentials"
        )

        await update.message.reply_text(
            "שלח את המספר שמופיע לפני שם העובד.\n"
            "לדוגמה: 3"
        )
        return

    if action == "choose_employee_credentials":
        try:
            employee_id = int(text)
        except ValueError:
            await update.message.reply_text(
                "יש לשלוח מספר בלבד."
            )
            return

        employee = get_employee(employee_id)

        if employee is None:
            await update.message.reply_text(
                "לא נמצא עובד עם המספר הזה."
            )
            return

        context.user_data["credentials_employee_id"] = (
            employee_id
        )
        context.user_data["action"] = (
            "enter_employee_number"
        )

        await update.message.reply_text(
            f"בחרת בעובד: {employee[1]}\n\n"
            "שלח עכשיו את מספר העובד האישי שלו.\n"
            "לדוגמה: 1001"
        )
        return

    if action == "enter_employee_number":
        employee_number = text.strip()

        if len(employee_number) < 2:
            await update.message.reply_text(
                "מספר העובד קצר מדי. נסה שוב."
            )
            return

        context.user_data["new_employee_number"] = (
            employee_number
        )
        context.user_data["action"] = "enter_employee_pin"

        await update.message.reply_text(
            "שלח קוד אישי בן 4 ספרות לעובד."
        )
        return

    if action == "enter_employee_pin":
        pin_code = text.strip()

        if not pin_code.isdigit() or len(pin_code) != 4:
            await update.message.reply_text(
                "הקוד חייב להכיל בדיוק 4 ספרות."
            )
            return

        employee_id = context.user_data.get(
            "credentials_employee_id"
        )
        employee_number = context.user_data.get(
            "new_employee_number"
        )

        result = set_employee_credentials(
            employee_id,
            employee_number,
            pin_code,
        )

        context.user_data["action"] = None
        context.user_data.pop(
            "credentials_employee_id",
            None,
        )
        context.user_data.pop(
            "new_employee_number",
            None,
        )

        if result == "updated":
            employee = get_employee(employee_id)

            await update.message.reply_text(
                "✅ פרטי הכניסה נשמרו.\n\n"
                f"עובד: {employee[1]}\n"
                f"מספר עובד: {employee_number}\n"
                f"קוד אישי: {pin_code}\n\n"
                "שלח את הפרטים לעובד באופן פרטי.",
                reply_markup=MANAGER_KEYBOARD,
            )

        elif result == "number_exists":
            await update.message.reply_text(
                "מספר העובד כבר משויך לעובד אחר.",
                reply_markup=MANAGER_KEYBOARD,
            )

        else:
            await update.message.reply_text(
                "לא ניתן לשמור את פרטי הכניסה.",
                reply_markup=MANAGER_KEYBOARD,
            )

        return

    if text == "🤒 דיווחי מחלה":
        await update.message.reply_text(
            "מערכת דיווחי המחלה תתווסף בשלב הבא."
        )
        return

    if text == "🔄 החלפות":
        await update.message.reply_text(
            "מערכת החלפת המשמרות תתווסף בהמשך."
        )
        return

    if text == "📊 מצב השבוע":
        await update.message.reply_text(
            "מסך מצב השבוע יתווסף בהמשך."
        )
        return

    await update.message.reply_text(
        "בחר פעולה מתפריט המנהל.",
        reply_markup=MANAGER_KEYBOARD,
    )


async def handle_employee(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
):
    action = context.user_data.get("action")
    employee_id = context.user_data.get("employee_id")

    if text == "📅 בקשות":
        context.user_data["action"] = None

        await update.message.reply_text(
            "בקשות לשבוע הבא.\n"
            "אפשר לשלוח עד 3 בקשות.",
            reply_markup=get_requests_keyboard(),
        )
        return

    if text == "➕ בקשת משמרת":
        week_start = get_next_week_start()

        current_requests = get_employee_requests(
            employee_id,
            week_start,
        )

        if len(current_requests) >= 3:
            await update.message.reply_text(
                "כבר שלחת 3 בקשות לשבוע הבא.\n"
                "אפשר למחוק בקשה ולהוסיף אחרת.",
                reply_markup=get_requests_keyboard(),
            )
            return

        context.user_data["action"] = (
            "choose_request_day"
        )

        await update.message.reply_text(
            "לאיזה יום הבקשה?",
            reply_markup=get_days_keyboard(),
        )
        return

    if text == "📋 הבקשות שלי":
        await show_my_requests(
            update,
            employee_id,
        )
        return

    if text == "🗑️ מחק בקשה":
        has_requests = await show_my_requests(
            update,
            employee_id,
        )

        if not has_requests:
            return

        context.user_data["action"] = "delete_request"

        await update.message.reply_text(
            "שלח את מספר הבקשה שברצונך למחוק."
        )
        return

    if action == "choose_request_day":
        if text not in DAYS:
            await update.message.reply_text(
                "יש לבחור יום באמצעות הכפתורים."
            )
            return

        context.user_data["request_day"] = text
        context.user_data["action"] = (
            "choose_request_type"
        )

        await update.message.reply_text(
            f"מה הבקשה ליום {text}?",
            reply_markup=get_shift_type_keyboard(),
        )
        return

    if action == "choose_request_type":
        if text not in REQUEST_TYPES:
            await update.message.reply_text(
                "יש לבחור סוג בקשה מהכפתורים."
            )
            return

        request_day = context.user_data.get(
            "request_day"
        )
        request_type = REQUEST_TYPES[text]
        week_start = get_next_week_start()

        result = add_shift_request(
            employee_id,
            week_start,
            request_day,
            request_type,
        )

        context.user_data["action"] = None
        context.user_data.pop("request_day", None)

        if result == "added":
            employee_requests = get_employee_requests(
                employee_id,
                week_start,
            )

            remaining = 3 - len(employee_requests)

            await update.message.reply_text(
                "✅ הבקשה נשמרה:\n"
                f"{request_day} — {request_type}\n\n"
                f"נותרו לך {remaining} בקשות.",
                reply_markup=get_requests_keyboard(),
            )

        elif result == "limit":
            await update.message.reply_text(
                "הגעת למקסימום של 3 בקשות.",
                reply_markup=get_requests_keyboard(),
            )

        elif result == "day_exists":
            await update.message.reply_text(
                "כבר קיימת בקשה ליום הזה.\n"
                "מחק אותה כדי להוסיף אחרת.",
                reply_markup=get_requests_keyboard(),
            )

        return

    if action == "delete_request":
        try:
            request_id = int(text)
        except ValueError:
            await update.message.reply_text(
                "יש לשלוח מספר בקשה בלבד."
            )
            return

        deleted = delete_shift_request(
            request_id,
            employee_id,
        )

        context.user_data["action"] = None

        if deleted:
            await update.message.reply_text(
                "הבקשה נמחקה בהצלחה.",
                reply_markup=get_requests_keyboard(),
            )
        else:
            await update.message.reply_text(
                "לא נמצאה בקשה עם המספר הזה.",
                reply_markup=get_requests_keyboard(),
            )

        return

    if text == "🤒 דיווח מחלה":
        await update.message.reply_text(
            "מערכת דיווח המחלה תתווסף בשלב הבא."
        )
        return

    if text == "🔄 החלפת משמרת":
        await update.message.reply_text(
            "מערכת החלפת המשמרות תתווסף בהמשך."
        )
        return

    if text == "ℹ️ מידע":
        await update.message.reply_text(
            "SmartShift — מערכת בקשות וסידור עבודה.\n\n"
            "כל עובד יכול לשלוח עד 3 בקשות "
            "לשבוע הבא."
        )
        return

    await update.message.reply_text(
        "בחר פעולה מתפריט העובד.",
        reply_markup=get_employee_keyboard(),
    )


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = update.message.text.strip()
    action = context.user_data.get("action")
    role = context.user_data.get("role")

    if text == "🚪 יציאה":
        context.user_data.clear()

        await update.message.reply_text(
            "יצאת מהמערכת.",
            reply_markup=START_KEYBOARD,
        )
        return

    if text == "⬅️ חזרה":
        context.user_data["action"] = None
        context.user_data.pop("request_day", None)

        if role == "employee":
            await update.message.reply_text(
                "חזרת לתפריט העובד.",
                reply_markup=get_employee_keyboard(),
            )
        elif role == "manager":
            await update.message.reply_text(
                "חזרת לתפריט המנהל.",
                reply_markup=MANAGER_KEYBOARD,
            )
        else:
            await update.message.reply_text(
                "חזרת למסך הכניסה.",
                reply_markup=START_KEYBOARD,
            )

        return

    # כניסת מנהל

    if text == "👨‍💼 כניסת מנהל":
        context.user_data.clear()
        context.user_data["action"] = "manager_login"

        await update.message.reply_text(
            "הכנס קוד מנהל:"
        )
        return

    if action == "manager_login":
        code = normalize_code(text)

        if is_manager_code(code):
            context.user_data.clear()
            context.user_data["role"] = "manager"

            await update.message.reply_text(
                "✅ הכניסה כמנהל הצליחה.",
                reply_markup=MANAGER_KEYBOARD,
            )
        else:
            await update.message.reply_text(
                "קוד מנהל שגוי. נסה שוב."
            )

        return

    # כניסת עובד

    if text == "👷 כניסת עובד":
        context.user_data.clear()
        context.user_data["action"] = (
            "employee_number_login"
        )

        await update.message.reply_text(
            "שלח את מספר העובד שלך."
        )
        return

    if action == "employee_number_login":
        context.user_data["login_employee_number"] = text
        context.user_data["action"] = "employee_pin_login"

        await update.message.reply_text(
            "שלח את הקוד האישי בן 4 הספרות."
        )
        return

    if action == "employee_pin_login":
        employee_number = context.user_data.get(
            "login_employee_number"
        )
        pin_code = text

        employee = authenticate_employee(
            employee_number,
            pin_code,
        )

        if employee is None:
            context.user_data.clear()

            await update.message.reply_text(
                "מספר העובד או הקוד האישי שגויים.",
                reply_markup=START_KEYBOARD,
            )
            return

        context.user_data.clear()
        context.user_data["role"] = "employee"
        context.user_data["employee_id"] = employee[0]
        context.user_data["employee_name"] = employee[1]

        await update.message.reply_text(
            f"שלום {employee[1]} 👋",
            reply_markup=get_employee_keyboard(),
        )
        return

    if role == "manager":
        await handle_manager(
            update,
            context,
            text,
        )
        return

    if role == "employee":
        await handle_employee(
            update,
            context,
            text,
        )
        return

    await update.message.reply_text(
        "יש להתחיל באמצעות /start.",
        reply_markup=START_KEYBOARD,
    )


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    print("הבוט פועל...")
    app.run_polling()


if __name__ == "__main__":
    main()