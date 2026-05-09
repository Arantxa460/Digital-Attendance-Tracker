from flask import Flask, request, jsonify, send_from_directory, Response
import sqlite3
import os
from datetime import datetime, timedelta
import random
import string
import csv
import io

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")
UI_DIR = os.path.join(FRONTEND_DIR, "arantxa_ui")
DB = os.path.join(PROJECT_DIR, "database", "attendance.db")


def get_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'student',
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        number TEXT UNIQUE NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        number TEXT NOT NULL,
        status TEXT NOT NULL,
        method TEXT NOT NULL DEFAULT 'Manual',
        marked_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module_name TEXT NOT NULL,
        pin_code TEXT NOT NULL,
        qr_token TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        details TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_action(action, details):
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_logs (action, details, created_at) VALUES (?, ?, ?)",
        (action, details, now_text())
    )
    conn.commit()
    conn.close()


init_db()


# ---------------- FRONTEND ROUTES ----------------

@app.route("/")
def home():
    return send_from_directory(UI_DIR, "login.html")


@app.route("/rejoice_script.js")
def serve_rejoice_script():
    return send_from_directory(FRONTEND_DIR, "rejoice_script.js")


@app.route("/kuze_display.js")
def serve_kuze_script():
    return send_from_directory(FRONTEND_DIR, "kuze_display.js")


@app.route("/<path:path>")
def serve_ui_file(path):
    return send_from_directory(UI_DIR, path)


# ---------------- AUTH ROUTES ----------------

@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    role = (data.get("role") or "student").strip().lower()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400

    if role not in ["student", "lecturer", "admin"]:
        role = "student"

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
            (username, password, role, now_text())
        )
        conn.commit()
        log_action("SIGNUP", f"New {role} user signed up: {username}")
        return jsonify({"success": True, "message": "Account created successfully"})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Username already exists"}), 409
    finally:
        conn.close()


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400

    conn = get_db()
    user = conn.execute(
        "SELECT id, username, role FROM users WHERE username=? AND password=?",
        (username, password)
    ).fetchone()
    conn.close()

    if user:
        log_action("LOGIN", f"{username} logged in")
        return jsonify({"success": True, "user": dict(user)})

    return jsonify({"success": False, "message": "Invalid username or password"}), 401


# ---------------- STUDENT ROUTES ----------------

@app.route("/students", methods=["GET"])
def get_students():
    conn = get_db()
    rows = conn.execute("SELECT id, name, number FROM students ORDER BY name").fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route("/add-student", methods=["POST"])
def add_student():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    number = (data.get("number") or "").strip()

    if not name or not number:
        return jsonify({"success": False, "message": "Student name and student number are required"}), 400

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO students (name, number, created_at) VALUES (?, ?, ?)",
            (name, number, now_text())
        )
        conn.commit()
        log_action("ADD_STUDENT", f"Added student {name} ({number})")
        return jsonify({"success": True, "message": "Student added successfully"})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "That student number already exists"}), 409
    finally:
        conn.close()


@app.route("/delete-student", methods=["POST"])
def delete_student():
    data = request.get_json(silent=True) or {}
    number = (data.get("number") or "").strip()

    if not number:
        return jsonify({"success": False, "message": "Student number is required"}), 400

    conn = get_db()
    conn.execute("DELETE FROM students WHERE number=?", (number,))
    conn.commit()
    conn.close()
    log_action("DELETE_STUDENT", f"Deleted student number {number}")
    return jsonify({"success": True, "message": "Student deleted"})


# ---------------- ATTENDANCE ROUTES ----------------

@app.route("/mark-attendance", methods=["POST"])
def mark_attendance():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    number = (data.get("number") or "").strip()
    status = (data.get("status") or "").strip()

    if status not in ["Present", "Absent"]:
        return jsonify({"success": False, "message": "Status must be Present or Absent"}), 400

    if not name or not number:
        return jsonify({"success": False, "message": "Missing student details"}), 400

    conn = get_db()
    conn.execute(
        "INSERT INTO attendance (name, number, status, method, marked_at) VALUES (?, ?, ?, ?, ?)",
        (name, number, status, "Manual", now_text())
    )
    conn.commit()
    conn.close()

    log_action("MARK_ATTENDANCE", f"{name} ({number}) marked {status}")
    return jsonify({"success": True, "message": f"{name} marked as {status}"})


@app.route("/get-attendance", methods=["GET"])
def get_attendance():
    conn = get_db()
    rows = conn.execute("SELECT * FROM attendance ORDER BY marked_at DESC").fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route("/attendance-summary", methods=["GET"])
def attendance_summary():
    conn = get_db()

    total_students = conn.execute("SELECT COUNT(*) AS count FROM students").fetchone()["count"]
    present = conn.execute(
        "SELECT COUNT(DISTINCT number) AS count FROM attendance WHERE status='Present'"
    ).fetchone()["count"]
    absent = conn.execute(
        "SELECT COUNT(DISTINCT number) AS count FROM attendance WHERE status='Absent'"
    ).fetchone()["count"]

    conn.close()

    return jsonify({
        "total_students": total_students,
        "present_today": present,
        "absent_today": absent
    })


# ---------------- QR / PIN ROUTES ----------------

@app.route("/create-session", methods=["POST"])
def create_session():
    data = request.get_json(silent=True) or {}
    module_name = (data.get("module_name") or "Software Processes").strip()

    pin_code = "".join(random.choices(string.digits, k=6))
    qr_token = "".join(random.choices(string.ascii_letters + string.digits, k=24))
    created_at = datetime.now()
    expires_at = created_at + timedelta(minutes=10)

    conn = get_db()
    conn.execute(
        """
        INSERT INTO sessions (module_name, pin_code, qr_token, expires_at, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            module_name,
            pin_code,
            qr_token,
            expires_at.strftime("%Y-%m-%d %H:%M:%S"),
            created_at.strftime("%Y-%m-%d %H:%M:%S")
        )
    )
    conn.commit()
    conn.close()

    log_action("CREATE_SESSION", f"Session created for {module_name}")

    return jsonify({
        "success": True,
        "module_name": module_name,
        "pin_code": pin_code,
        "qr_token": qr_token,
        "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
        "qr_url": f"http://127.0.0.1:5000/checkin.html?token={qr_token}"
    })


@app.route("/check-in", methods=["POST"])
def check_in():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    number = (data.get("number") or "").strip()
    pin_code = (data.get("pin_code") or "").strip()
    qr_token = (data.get("qr_token") or "").strip()

    if not name or not number:
        return jsonify({"success": False, "message": "Name and student number are required"}), 400

    conn = get_db()
    if pin_code:
        session = conn.execute(
            "SELECT * FROM sessions WHERE pin_code=? ORDER BY id DESC LIMIT 1",
            (pin_code,)
        ).fetchone()
    elif qr_token:
        session = conn.execute(
            "SELECT * FROM sessions WHERE qr_token=? ORDER BY id DESC LIMIT 1",
            (qr_token,)
        ).fetchone()
    else:
        session = None

    if not session:
        conn.close()
        return jsonify({"success": False, "message": "Invalid PIN or QR code"}), 404

    expires_at = datetime.strptime(session["expires_at"], "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expires_at:
        conn.close()
        return jsonify({"success": False, "message": "This attendance session has expired"}), 400

    # Auto-add the student if they do not exist yet.
    conn.execute(
        "INSERT OR IGNORE INTO students (name, number, created_at) VALUES (?, ?, ?)",
        (name, number, now_text())
    )
    conn.execute(
        "INSERT INTO attendance (name, number, status, method, marked_at) VALUES (?, ?, ?, ?, ?)",
        (name, number, "Present", "QR/PIN", now_text())
    )
    conn.commit()
    conn.close()

    log_action("CHECK_IN", f"{name} ({number}) checked in via QR/PIN")
    return jsonify({"success": True, "message": "Attendance recorded successfully"})




@app.route("/student-attendance", methods=["GET"])
def student_attendance():
    number = (request.args.get("number") or "").strip()

    if not number:
        return jsonify({"success": False, "message": "Student number is required"}), 400

    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE number=?", (number,)).fetchone()
    records = conn.execute(
        "SELECT * FROM attendance WHERE number=? ORDER BY marked_at DESC",
        (number,)
    ).fetchall()
    conn.close()

    total = len(records)
    present = sum(1 for row in records if row["status"] == "Present")
    absent = sum(1 for row in records if row["status"] == "Absent")
    percentage = round((present / total) * 100, 1) if total else 0
    below_threshold = total > 0 and percentage < 80

    return jsonify({
        "success": True,
        "student_found": student is not None,
        "student": dict(student) if student else {"name": "", "number": number},
        "total_sessions": total,
        "present": present,
        "absent": absent,
        "attendance_percentage": percentage,
        "below_threshold": below_threshold,
        "alert": "Attendance below 80%. Please attend upcoming classes." if below_threshold else "Attendance is currently acceptable.",
        "records": [dict(row) for row in records]
    })


# ---------------- REPORTS / AUDIT ----------------

@app.route("/export-attendance", methods=["GET"])
def export_attendance():
    conn = get_db()
    rows = conn.execute("SELECT * FROM attendance ORDER BY marked_at DESC").fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Student Number", "Status", "Method", "Marked At"])
    for row in rows:
        writer.writerow([row["name"], row["number"], row["status"], row["method"], row["marked_at"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_report.csv"}
    )


@app.route("/audit-logs", methods=["GET"])
def audit_logs():
    conn = get_db()
    rows = conn.execute("SELECT * FROM audit_logs ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


if __name__ == "__main__":
    app.run(debug=True)
