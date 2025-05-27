# Student Management System (SMS)

A custom Flask-based Student Management System designed to streamline
academic management and internal communication.

It supports multiple user roles (students, professors, staff),
centralized student records, messaging, scheduling,
assignment uploads, grade management, and exporting student data.

## Features

- Centralized storage of student records, academic files, and grades
- Role-based access control: students, professors, staff
- Messaging system between students, professors, and staff
- Flexible scheduling and calendar integration (basic placeholder)
- File uploads for assignments
- Export student records as PDF and CSV
- Bulk CSV upload of grades
- Notifications and reminders for events (basic support)
- Secure login with Flask-Login

## Requirements

- Python 3.8+
- Flask
- Flask-Login
- Flask-SQLAlchemy
- ReportLab (for PDF export)

## Installation

1. Clone the repository or download the project files.

2. Create and activate a virtual environment (optional but recommended):

   python -m venv venv
   source venv/bin/activate # On Windows: venv\Scripts\activate

3. Install dependencies:

   pip install flask flask-login flask_sqlalchemy reportlab

## Usage

1. Ensure the `templates` folder contains all required
   HTML template files (`login.html`, `student_record.html`, etc.).

2. Run the Flask application:

   python app.py

3. Access the app at [http://localhost:5000](http://localhost:5000).

4. Use sample credentials to log in:

   - Student: `student1` / `pass`
   - Professor: `prof1` / `pass`
   - Staff: `staff1` / `pass`

## Project Structure

```
your-project-folder/
├── app.py
├── templates/
│   ├── login.html
│   ├── student_record.html
│   ├── students.html
│   ├── edit_grades.html
│   ├── upload_grades.html
│   ├── upload_assignment.html
│   ├── assignment_list.html
│   └── calendar.html
├── static/         # (optional) for CSS, JS, images
├── README.md
└── requirements.txt (optional)
```

## Extending the Project

- Add full calendar and reminder functionality
- Implement real-time notifications (e.g., with WebSockets)
- Add more granular permissions and auditing
- Integrate external APIs for email or SMS notifications
