from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import io
import csv
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas

# Initialize Flask app
app = Flask(__name__)

# Configuration settings
app.config['SECRET_KEY'] = 'your-secret-key'  # Used for session management and CSRF protection
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'  # SQLite DB file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable tracking modifications for performance
app.config['UPLOAD_FOLDER'] = 'uploads'  # Directory to store uploaded files

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database and login manager extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirect unauthorized users to login page

# ----- Models -----

# User model represents all users (students, staff, professors)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Unique ID
    username = db.Column(db.String(64), unique=True, nullable=False)  # Username/login name
    password_hash = db.Column(db.String(128))  # Hashed password storage
    role = db.Column(db.String(20))  # Role type: student, professor, or staff

    # Set password and store hashed version
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Verify password against stored hash
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Student record model stores academic grades linked to a User
class StudentRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)  # One-to-one with User
    grades = db.Column(db.Text)  # Store grades as text (could be JSON or CSV format)

# Assignment uploads model, links uploaded files to students
class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # The student who uploaded
    filename = db.Column(db.String(200))  # Original file name
    filepath = db.Column(db.String(300))  # Server path where file is saved

# Schedule/events model for calendar and reminders
class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Owner of event
    event = db.Column(db.String(255))  # Event description/title
    time = db.Column(db.String(255))  # Event time stored as ISO8601 string

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Return user by ID or None

# ----- Routes -----

# Home route redirects logged in users to their dashboard or login otherwise
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('student_view'))
    return redirect(url_for('login'))

# Login route handles GET (show form) and POST (process login)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get username and password from form
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        # Verify user exists and password matches
        if user and user.check_password(password):
            login_user(user)  # Log in user
            return redirect(url_for('student_view'))
        flash('Invalid username or password')  # Show error if failed
    return render_template('login.html')

# Logout route ends user session
@app.route('/logout')
@login_required  # Only logged-in users can logout
def logout():
    logout_user()
    return redirect(url_for('login'))

# Student list view with optional search/filter, requires login
@app.route('/students')
@login_required
def student_view():
    query = User.query.filter_by(role='student')  # Query all students
    search = request.args.get('search', '')  # Get search term if any
    if search:
        query = query.filter(User.username.contains(search))  # Filter by username substring
    students = query.all()
    return render_template('students.html', students=students, search=search)

# View a student's detailed record
@app.route('/student/<int:id>')
@login_required
def student_record(id):
    student = User.query.filter_by(id=id, role='student').first_or_404()
    # Students can only view their own record; staff/professors can view all
    if current_user.role == 'student' and current_user.id != student.id:
        return "Access denied", 403
    record = StudentRecord.query.filter_by(user_id=student.id).first()
    assignments = Assignment.query.filter_by(student_id=student.id).all()
    return render_template('student_record.html', student=student, record=record, assignments=assignments)

# Edit grades form - only accessible to staff/professor
@app.route('/edit-grades', methods=['GET', 'POST'])
@login_required
def edit_grades():
    if current_user.role not in ['staff', 'professor']:
        return "Access denied", 403
    if request.method == 'POST':
        student_id = int(request.form['student_id'])
        grades = request.form['grades']
        record = StudentRecord.query.filter_by(user_id=student_id).first()
        if record:
            record.grades = grades  # Update existing
        else:
            record = StudentRecord(user_id=student_id, grades=grades)
            db.session.add(record)  # Add new record if none exists
        db.session.commit()
        flash('Grades updated.')
        return redirect(url_for('student_view'))
    students = User.query.filter_by(role='student').all()
    return render_template('edit_grades.html', students=students)

# Bulk CSV upload of grades for staff/professor
@app.route('/upload-grades', methods=['GET', 'POST'])
@login_required
def upload_grades_csv():
    if current_user.role not in ['staff', 'professor']:
        return "Access denied", 403
    if request.method == 'POST':
        file = request.files['csv_file']
        if not file:
            flash('No file uploaded')
            return redirect(request.url)
        # Read CSV from uploaded file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        reader = csv.DictReader(stream)
        for row in reader:
            try:
                student_id = int(row['student_id'])
                grades = row['grades']
            except (KeyError, ValueError):
                continue  # Skip malformed rows
            record = StudentRecord.query.filter_by(user_id=student_id).first()
            if record:
                record.grades = grades
            else:
                db.session.add(StudentRecord(user_id=student_id, grades=grades))
        db.session.commit()
        flash('CSV Grades uploaded.')
        return redirect(url_for('student_view'))
    return render_template('upload_grades.html')

# Assignment upload for students only
@app.route('/upload-assignment', methods=['GET', 'POST'])
@login_required
def upload_assignment():
    if current_user.role != 'student':
        return "Access denied", 403
    if request.method == 'POST':
        if 'assignment' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['assignment']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        filename = secure_filename(file.filename)  # Secure the filename before saving
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)  # Save the file
        assignment = Assignment(student_id=current_user.id, filename=filename, filepath=filepath)
        db.session.add(assignment)
        db.session.commit()
        flash('Assignment uploaded.')
        return redirect(url_for('student_record', id=current_user.id))
    return render_template('upload_assignment.html')

# Staff/professor can view all assignments
@app.route('/assignments')
@login_required
def list_assignments():
    if current_user.role not in ['staff', 'professor']:
        return "Access denied", 403
    assignments = Assignment.query.all()
    return render_template('assignment_list.html', assignments=assignments)

# Download a specific assignment file (staff/professor only)
@app.route('/download-assignment/<int:id>')
@login_required
def download_assignment(id):
    if current_user.role not in ['staff', 'professor']:
        return "Access denied", 403
    assignment = Assignment.query.get_or_404(id)
    return send_file(assignment.filepath, as_attachment=True)

# Calendar page
@app.route('/calendar')
@login_required
def calendar_view():
    return render_template('calendar.html')

# Provide events for the logged-in user's calendar in JSON format
@app.route('/events')
@login_required
def get_events():
    events = Schedule.query.filter_by(user_id=current_user.id).all()
    data = [{'title': e.event, 'start': e.time} for e in events]
    return jsonify(data)

# Get reminders for events in the next 3 days for the logged-in user
@app.route('/reminders')
@login_required
def reminders():
    upcoming = datetime.utcnow() + timedelta(days=3)
    events = Schedule.query.filter(Schedule.user_id == current_user.id,
                                   Schedule.time <= upcoming.isoformat()).all()
    data = [{'event': e.event, 'time': e.time} for e in events]
    return jsonify(data)

# Export a student's record as a PDF
@app.route('/export/pdf/<int:id>')
@login_required
def export_pdf(id):
    student = User.query.filter_by(id=id, role='student').first_or_404()
    # Students can only export their own record; staff/professors can export any
    if current_user.role == 'student' and current_user.id != student.id:
        return "Access denied", 403
    record = StudentRecord.query.filter_by(user_id=student.id).first()
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)  # Create PDF canvas in memory
    p.drawString(100, 800, f"Student Record for {student.username}")
    p.drawString(100, 780, f"Grades: {record.grades if record else 'N/A'}")
    p.showPage()
    p.save()
    buffer.seek(0)
    # Send PDF file to user for download
    return send_file(buffer, as_attachment=True, download_name=f"{student.username}_record.pdf", mimetype='application/pdf')

# Export a student's record as CSV
@app.route('/export/csv/<int:id>')
@login_required
def export_csv(id):
    student = User.query.filter_by(id=id, role='student').first_or_404()
    if current_user.role == 'student' and current_user.id != student.id:
        return "Access denied", 403
    record = StudentRecord.query.filter_by(user_id=student.id).first()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Username', 'Grades'])
    cw.writerow([student.username, record.grades if record else 'N/A'])
    output = io.BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    return send_file(output, as_attachment=True, download_name=f"{student.username}_record.csv", mimetype='text/csv')

# Run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables if not exist
        # Create sample users if DB is empty
        if not User.query.first():
            u1 = User(username='student1', role='student')
            u1.set_password('pass')
            u2 = User(username='staff1', role='staff')
            u2.set_password('pass')
            u3 = User(username='prof1', role='professor')
            u3.set_password('pass')
            db.session.add_all([u1,u2,u3])
            db.session.commit()
    app.run(debug=True)
