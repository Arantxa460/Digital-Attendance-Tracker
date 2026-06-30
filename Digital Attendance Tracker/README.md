# Digital Class Attendance Tracking System
A digital class attendance tracking system provides a solution to a real-life challenge at The Namibia University of Science and Technology. By replacing the paper-based system used at the university, it improves accuracy, efficiency and accessibility to attendance records. It will reduce errors and make administrative tasks much easier

# Overview
Lectures can sign in, check attendance, create sessions, view attencance and see auto generated reports.
Students can check in using PIN or by scanning a QR Code, view personal attendance and be alerted if their attendance is below 80%.

# Features
- HTML
- CSS
- JavaScript
- Python
- Flask
  
## How To Run
In the terminal:
python -m pip install -r requirements.txt
cd backend
python elsabackend.py


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

No default users or students are hardcoded. The database is created automatically in database/attendance.db.
