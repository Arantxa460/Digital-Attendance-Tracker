# Digital Class Attendance Tracking System

Fixed project using the original structure.

## Run
```powershell
python -m pip install -r requirements.txt
cd backend
python elsabackend.py
```

Open: http://127.0.0.1:5000

## Demo flow
1. Sign up as Lecturer.
2. Login as Lecturer.
3. Add students and mark attendance manually.
4. Create QR/PIN session.
5. Sign up as Student.
6. Login as Student.
7. Use Student Check-In or view attendance percentage/status.
8. Export CSV report from lecturer dashboard.

No default users or students are hardcoded. The database is created automatically in `database/attendance.db`.
