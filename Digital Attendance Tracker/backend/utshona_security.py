def validate_attendance(cursor, student_id, course, qr_code):
    
    # 1. Check if student exists
    cursor.execute("SELECT id FROM users WHERE id=%s", (student_id,))
    if not cursor.fetchone():
        return {"status": "error", "message": "Invalid student"}

    # 2. Prevent duplicate attendance
    cursor.execute(
        "SELECT id FROM attendance WHERE student_id=%s AND course=%s",
        (student_id, course),
    )
    if cursor.fetchone():
        return {"status": "error", "message": "Attendance already marked"}

    # 3. Validate QR code
    cursor.execute(
        "SELECT qr_code FROM qr_sessions WHERE course=%s",
        (course,),
    )
    qr = cursor.fetchone()

    if not qr:
        return {"status": "error", "message": "No active QR session"}

    if qr_code != qr["qr_code"]:
        return {"status": "error", "message": "Invalid QR code"}

    return {"status": "success"}
