
from flask import jsonify
from mysql.connector import Error
 
 #reigisters the /api/get-attendance route to the shared Flask app, and defines the logic to fetch attendance data joined with student names from the database.
def get_attendance_data(get_db_connection):
    """
    Fetches attendance rows joined with the students table so we get the
    student name alongside their id and status.
 
    Returns a list of dicts with keys:
        - number  → student_id   (matches student.number in kuze_display.js)
        - name    → student name (matches student.name   in kuze_display.js)
        - status  → Present / Absent / Pending
 
    Assumes the database has a `students` table with at least:
        students(student_id, name)
    If your students table uses a different column name, adjust the JOIN below.
    """
    conn   = None
    cursor = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
 
        cursor.execute(
            """
            SELECT
                a.student_id  AS number,
                s.name        AS name,
                a.status      AS status
            FROM attendance a
            JOIN students   s ON s.student_id = a.student_id
            ORDER BY a.id DESC
            """
        )
        rows = cursor.fetchall()
        return rows
 
    except Error as e:
        raise RuntimeError(f"Database error: {str(e)}")
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()
 
 
def register_routes(app):
    """
    Call this in elsabackend.py to attach Kuze's route to the shared Flask app:
 
        from kuze_backend_helper import register_routes
        register_routes(app)
    """
    from elsabackend import get_db_connection
 
    @app.route('/api/get-attendance', methods=['GET'])
    def api_get_attendance():
        """
        Called by: fetch('/api/get-attendance') in kuze_display.js
        Returns:   JSON array of { number, name, status }
        """
        try:
            data = get_attendance_data(get_db_connection)
            return jsonify(data), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 500