"use strict";

let students = [];
let selectedStudent = null;

document.addEventListener("DOMContentLoaded", () => {
    if (document.querySelector(".dashboard-page")) {
        requireLogin();
        applyRoleAccess();
        loadDashboardSummary();
    }

    if (document.querySelector(".attendance-page")) {
        requireLogin();
        applyRoleAccess();
        requireLecturerPage();
        loadStudents();
        setupStudentSearch();
    }
});

function requireLogin() {
    const user = localStorage.getItem("loggedInUser");
    if (!user) {
        window.location.href = "login.html";
    }
}

function logout() {
    localStorage.removeItem("loggedInUser");
    localStorage.removeItem("role");
}

function getRole() {
    return localStorage.getItem("role") || "student";
}

function applyRoleAccess() {
    const role = getRole();

    if (role === "student") {
        document.querySelectorAll(".lecturer-only").forEach(el => {
            el.style.display = "none";
        });
        document.querySelectorAll(".student-only").forEach(el => {
            el.style.display = "block";
        });
    } else {
        document.querySelectorAll(".lecturer-only").forEach(el => {
            el.style.display = "";
        });
        document.querySelectorAll(".student-only").forEach(el => {
            el.style.display = "none";
        });
    }
}

function requireLecturerPage() {
    const role = getRole();
    if (role === "student") {
        alert("Students cannot access lecturer attendance management. Please use Student Check-In.");
        window.location.href = "checkin.html";
    }
}

async function loadDashboardSummary() {
    try {
        const response = await fetch("/attendance-summary");
        const data = await response.json();

        setText("total-count", data.total_students);
        setText("present-count", data.present_today);
        setText("absent-count", data.absent_today);
    } catch (error) {
        console.error("Could not load dashboard summary", error);
    }
}

async function loadStudents() {
    try {
        const response = await fetch("/students");
        students = await response.json();
        renderStudents(students);
    } catch (error) {
        alert("Could not load students. Make sure Flask is running.");
    }
}

function setupStudentSearch() {
    const search = document.getElementById("student-search");
    if (!search) return;

    search.addEventListener("input", () => {
        const keyword = search.value.toLowerCase();
        const filtered = students.filter(student =>
            student.name.toLowerCase().includes(keyword) ||
            student.number.toLowerCase().includes(keyword)
        );
        renderStudents(filtered);
    });
}

function renderStudents(list) {
    const table = document.getElementById("attendance-body");
    if (!table) return;

    table.innerHTML = "";

    if (list.length === 0) {
        table.innerHTML = `<tr><td colspan="3">No students yet. Add a student first.</td></tr>`;
        return;
    }

    list.forEach(student => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${escapeHtml(student.name)}</td>
            <td>${escapeHtml(student.number)}</td>
            <td>${student.status || "Not marked"}</td>
        `;

        row.addEventListener("click", () => {
            selectedStudent = student;
            document.querySelectorAll("#attendance-body tr").forEach(r => r.classList.remove("selected-row"));
            row.classList.add("selected-row");
        });

        table.appendChild(row);
    });
}

async function addStudent() {
    const nameInput = document.getElementById("new-student-name");
    const numberInput = document.getElementById("new-student-number");

    const name = nameInput.value.trim();
    const number = numberInput.value.trim();

    if (!name || !number) {
        alert("Please enter student name and student number");
        return;
    }

    const response = await fetch("/add-student", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({name, number})
    });

    const data = await response.json();

    if (data.success) {
        alert("Student added successfully");
        nameInput.value = "";
        numberInput.value = "";
        selectedStudent = null;
        await loadStudents();
    } else {
        alert(data.message || "Could not add student");
    }
}

async function markSelected(status) {
    if (!selectedStudent) {
        alert("Please select a student from the table first");
        return;
    }

    const response = await fetch("/mark-attendance", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            name: selectedStudent.name,
            number: selectedStudent.number,
            status
        })
    });

    const data = await response.json();

    if (data.success) {
        alert(data.message || `Marked as ${status}`);
        selectedStudent.status = status;
        renderStudents(students);
        selectedStudent = null;
    } else {
        alert(data.message || "Could not mark attendance");
    }
}

async function deleteSelectedStudent() {
    if (!selectedStudent) {
        alert("Please select a student first");
        return;
    }

    const yes = confirm(`Delete ${selectedStudent.name}?`);
    if (!yes) return;

    const response = await fetch("/delete-student", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({number: selectedStudent.number})
    });

    const data = await response.json();

    if (data.success) {
        alert("Student deleted");
        selectedStudent = null;
        await loadStudents();
    } else {
        alert(data.message || "Could not delete student");
    }
}

async function createSession() {
    const input = document.getElementById("module-name");
    const moduleName = input.value.trim() || "Software Processes";

    const response = await fetch("/create-session", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({module_name: moduleName})
    });

    const data = await response.json();

    if (data.success) {
        const box = document.getElementById("session-box");
        box.innerHTML = `
            <p><strong>Module:</strong> ${escapeHtml(data.module_name)}</p>
            <p><strong>PIN Code:</strong> <span class="pin-code">${data.pin_code}</span></p>
            <p><strong>QR Link:</strong> <a href="${data.qr_url}" target="_blank">${data.qr_url}</a></p>
            <p><strong>Expires:</strong> ${data.expires_at}</p>
            <p class="hint">For the demo, this QR link represents the QR code that students scan.</p>
        `;
    } else {
        alert(data.message || "Could not create session");
    }
}

async function studentCheckIn() {
    const params = new URLSearchParams(window.location.search);
    const qrToken = params.get("token") || "";

    const name = document.getElementById("checkin-name").value.trim();
    const number = document.getElementById("checkin-number").value.trim();
    const pin = document.getElementById("checkin-pin").value.trim();

    if (!name || !number) {
        alert("Please enter your name and student number");
        return;
    }

    if (!pin && !qrToken) {
        alert("Please enter a PIN or use a QR link from the dashboard");
        return;
    }

    const response = await fetch("/check-in", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            name,
            number,
            pin_code: pin,
            qr_token: qrToken
        })
    });

    const data = await response.json();

    if (data.success) {
        alert("Attendance recorded successfully");
    } else {
        alert(data.message || "Check-in failed");
    }
}


async function loadStudentAttendance() {
    const numberInput = document.getElementById("student-view-number");
    const resultBox = document.getElementById("student-attendance-result");

    if (!numberInput || !resultBox) return;

    const number = numberInput.value.trim();
    if (!number) {
        alert("Please enter your student number");
        return;
    }

    const response = await fetch(`/student-attendance?number=${encodeURIComponent(number)}`);
    const data = await response.json();

    if (!data.success) {
        alert(data.message || "Could not load attendance");
        return;
    }

    const alertClass = data.below_threshold ? "alert-danger" : "alert-good";

    const rows = data.records.length
        ? data.records.map(record => `
            <tr>
                <td>${escapeHtml(record.status)}</td>
                <td>${escapeHtml(record.method)}</td>
                <td>${escapeHtml(record.marked_at)}</td>
            </tr>
        `).join("")
        : `<tr><td colspan="3">No attendance records yet.</td></tr>`;

    resultBox.innerHTML = `
        <div class="student-status-card">
            <h3>Attendance Summary</h3>
            <p><strong>Student Number:</strong> ${escapeHtml(number)}</p>
            <p><strong>Total Sessions Recorded:</strong> ${data.total_sessions}</p>
            <p><strong>Present:</strong> ${data.present}</p>
            <p><strong>Absent:</strong> ${data.absent}</p>
            <p><strong>Attendance Percentage:</strong> ${data.attendance_percentage}%</p>
            <p class="${alertClass}"><strong>Status:</strong> ${escapeHtml(data.alert)}</p>

            <table class="attendance-table">
                <thead>
                    <tr>
                        <th>Status</th>
                        <th>Method</th>
                        <th>Date/Time</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `;
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}
