import sqlite3

DB_NAME = "shiftmaster.db"


def get_connection():
    connection = sqlite3.connect(DB_NAME)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()

    return any(column[1] == column_name for column in columns)


def create_tables():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            employee_number TEXT,
            pin_code TEXT
        )
        """
    )

    # התאמה למסד הנתונים הישן בלי למחוק עובדים קיימים
    if not column_exists(cursor, "employees", "employee_number"):
        cursor.execute(
            """
            ALTER TABLE employees
            ADD COLUMN employee_number TEXT
            """
        )

    if not column_exists(cursor, "employees", "pin_code"):
        cursor.execute(
            """
            ALTER TABLE employees
            ADD COLUMN pin_code TEXT
            """
        )

    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_employees_employee_number
        ON employees(employee_number)
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS shift_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            week_start TEXT NOT NULL,
            day_name TEXT NOT NULL,
            request_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id)
                REFERENCES employees(id)
                ON DELETE CASCADE
        )
        """
    )

    connection.commit()
    connection.close()


def add_employee(name):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO employees (name)
            VALUES (?)
            """,
            (name.strip(),),
        )

        connection.commit()
        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        connection.close()


def get_employees():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            employee_number
        FROM employees
        ORDER BY id
        """
    )

    employees = cursor.fetchall()
    connection.close()

    return employees


def get_employee(employee_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            employee_number
        FROM employees
        WHERE id = ?
        """,
        (employee_id,),
    )

    employee = cursor.fetchone()
    connection.close()

    return employee


def get_employee_by_number(employee_number):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            employee_number
        FROM employees
        WHERE employee_number = ?
        """,
        (employee_number.strip(),),
    )

    employee = cursor.fetchone()
    connection.close()

    return employee


def set_employee_credentials(
    employee_id,
    employee_number,
    pin_code,
):
    employee_number = employee_number.strip()
    pin_code = pin_code.strip()

    if not employee_number:
        return "invalid_number"

    if not pin_code.isdigit() or len(pin_code) != 4:
        return "invalid_pin"

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            UPDATE employees
            SET
                employee_number = ?,
                pin_code = ?
            WHERE id = ?
            """,
            (
                employee_number,
                pin_code,
                employee_id,
            ),
        )

        if cursor.rowcount == 0:
            return "not_found"

        connection.commit()
        return "updated"

    except sqlite3.IntegrityError:
        return "number_exists"

    finally:
        connection.close()


def authenticate_employee(employee_number, pin_code):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            employee_number
        FROM employees
        WHERE employee_number = ?
          AND pin_code = ?
        """,
        (
            employee_number.strip(),
            pin_code.strip(),
        ),
    )

    employee = cursor.fetchone()
    connection.close()

    return employee


def update_employee(employee_id, new_name):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            UPDATE employees
            SET name = ?
            WHERE id = ?
            """,
            (
                new_name.strip(),
                employee_id,
            ),
        )

        updated = cursor.rowcount > 0
        connection.commit()

        return updated

    except sqlite3.IntegrityError:
        return False

    finally:
        connection.close()


def delete_employee(employee_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM employees
        WHERE id = ?
        """,
        (employee_id,),
    )

    deleted = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return deleted


def count_employee_requests(employee_id, week_start):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM shift_requests
        WHERE employee_id = ?
          AND week_start = ?
        """,
        (
            employee_id,
            week_start,
        ),
    )

    count = cursor.fetchone()[0]
    connection.close()

    return count


def request_exists_for_day(
    employee_id,
    week_start,
    day_name,
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM shift_requests
        WHERE employee_id = ?
          AND week_start = ?
          AND day_name = ?
        """,
        (
            employee_id,
            week_start,
            day_name,
        ),
    )

    exists = cursor.fetchone() is not None
    connection.close()

    return exists


def add_shift_request(
    employee_id,
    week_start,
    day_name,
    request_type,
):
    if count_employee_requests(employee_id, week_start) >= 3:
        return "limit"

    if request_exists_for_day(
        employee_id,
        week_start,
        day_name,
    ):
        return "day_exists"

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO shift_requests (
            employee_id,
            week_start,
            day_name,
            request_type
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            employee_id,
            week_start,
            day_name,
            request_type,
        ),
    )

    connection.commit()
    connection.close()

    return "added"


def get_employee_requests(employee_id, week_start):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            day_name,
            request_type,
            status
        FROM shift_requests
        WHERE employee_id = ?
          AND week_start = ?
        ORDER BY id
        """,
        (
            employee_id,
            week_start,
        ),
    )

    requests = cursor.fetchall()
    connection.close()

    return requests


def delete_shift_request(request_id, employee_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM shift_requests
        WHERE id = ?
          AND employee_id = ?
        """,
        (
            request_id,
            employee_id,
        ),
    )

    deleted = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return deleted


def get_week_requests(week_start):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            shift_requests.id,
            employees.name,
            shift_requests.day_name,
            shift_requests.request_type,
            shift_requests.status
        FROM shift_requests
        JOIN employees
          ON employees.id = shift_requests.employee_id
        WHERE shift_requests.week_start = ?
        ORDER BY
            employees.name,
            shift_requests.id
        """,
        (week_start,),
    )

    requests = cursor.fetchall()
    connection.close()

    return requests