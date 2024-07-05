import json
import os
from datetime import datetime, timedelta

from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

import requests
from flask import Flask, render_template, redirect, url_for, flash, abort, request, current_app, jsonify, make_response, \
    Response, send_from_directory, send_file
from sqlalchemy.orm import joinedload

from werkzeug.security import generate_password_hash, check_password_hash
import logging
from flask_sqlalchemy import SQLAlchemy

from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user

from flask_babel import Babel
from werkzeug.utils import secure_filename
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VideoGrant
from flask import send_from_directory

app = Flask(__name__)
babel = Babel(app)
login_manager = LoginManager()
login_manager.init_app(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


logging.basicConfig(level=logging.DEBUG)

@login_manager.user_loader
def load_user(user_id):
    user = Users.query.get(int(user_id))
    return user


app.config['SECRET_KEY'] = 'any-key-you-choose'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.secret_key = 'your_secret_key'  # Required for session management and flashing

# Initialize the SQLAlchemy part of the app instance
db = SQLAlchemy(app)

with app.app_context():
    class Users(UserMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100))
        password = db.Column(db.String(100))
        email = db.Column(db.String(100), unique=True)
        gender = db.Column(db.String(100))
        religion = db.Column(db.String(100))
        role = db.Column(db.String(100))
        grade = db.Column(db.String(100))
        Class = db.Column(db.String(100))
        teacher = db.relationship('Teacher', backref='user', uselist=False)
        student = db.relationship('Students', backref='user', uselist=False)
        subjects = db.relationship('Subjects', backref='teacher')
        quizzes = db.relationship('Quizzes', backref='user')


    class Subjects(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100))
        teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
        grade = db.Column(db.String(1000))
        teacher_name = db.Column(db.String(1000))
        lessons = db.relationship('Lessons', backref='subject')


    class Lessons(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100))
        subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
        files = db.relationship('Files', backref='lesson')
        video_link = db.relationship('Videos', backref='lesson')
        quizzes = db.relationship('Quizzes', backref='lesson')


    class QuizQuestion(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'))
        question_type = db.Column(db.String(50))  # 'multiple', 'true_false', 'complete'
        question_text = db.Column(db.Text)
        options = db.Column(db.Text)  # Store options as JSON for multiple choice
        correct_answer = db.Column(db.Text)
        score = db.Column(db.Integer)


    class QuizResult(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
        quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'))
        score = db.Column(db.Integer)
        timestamp = db.Column(db.DateTime, default=datetime.utcnow)
        student_email = db.Column(db.String(1000))


    class Files(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100))
        path = db.Column(db.String(200))
        lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))

    class Timetable(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100))
        path = db.Column(db.String(200))
        teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'))  # Foreign key to Teacher
    class Videos(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100))
        url = db.Column(db.String(200))
        lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))


    class Quizzes(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100))
        questions = db.Column(db.Text)  # Assuming questions are stored as JSON or similar format
        lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'))


    class Teacher(UserMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100))
        email = db.Column(db.String(100))
        subject = db.Column(db.String(100))
        grade = db.Column(db.String(100))
        Class = db.Column(db.String(100))
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
        timetable_id = db.Column(db.Integer, db.ForeignKey('timetable.id'))  # Foreign key to Timetable

    class Students(UserMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100))
        email = db.Column(db.String(100))
        grade = db.Column(db.String(100))
        Class = db.Column(db.String(100))
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'))


    class News(UserMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(100))
        content = db.Column(db.String(100))


    class Message(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        teacher_email = db.Column(db.String(100))
        student_email = db.Column(db.String(100))
        message = db.Column(db.Text)
        timestamp = db.Column(db.DateTime, default=datetime.utcnow)
        read = db.Column(db.Boolean, default=False)
        type = db.Column(db.String(50), default="message")
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

        def to_dict(self):
            return {
                'id': self.id,
                'teacher_email': self.teacher_email,
                'student_email': self.student_email,
                'message': self.message,
                'timestamp': self.timestamp.isoformat(),
                'read': self.read,
                'type': self.type,
            }


    # Define the Event model
    class Event(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(100))
        start_date = db.Column(db.DateTime)
        end_date = db.Column(db.DateTime)
        description = db.Column(db.Text)

        def to_dict(self):
            return {
                'id': self.id,
                'title': self.title,
                'start_date': self.start_date.isoformat(),
                'end_date': self.end_date.isoformat(),
                'description': self.description
            }


    db.create_all()


class MyModelView(ModelView):
    def is_accessible(self):
        return True


admin = Admin(app)
admin.add_view(MyModelView(Users, db.session))
admin.add_view(MyModelView(Students, db.session))
admin.add_view(MyModelView(Teacher, db.session))
admin.add_view(MyModelView(Subjects, db.session))
admin.add_view(MyModelView(Event, db.session))
admin.add_view(MyModelView(News, db.session))
admin.add_view(MyModelView(Message, db.session))
admin.add_view(MyModelView(Lessons, db.session))
admin.add_view(MyModelView(Quizzes, db.session))
admin.add_view(MyModelView(QuizResult, db.session))
admin.add_view(MyModelView(QuizQuestion, db.session))
admin.add_view(MyModelView(Files, db.session))
admin.add_view(MyModelView(Timetable, db.session))
admin.add_view(MyModelView(Videos, db.session))



def send_notification(user_id, message_content):
    new_notification = Message(
        teacher_email=None,
        student_email=None,
        message=message_content,
        type="notification",
        read=False
    )
    new_notification.user_id = user_id
    db.session.add(new_notification)
    db.session.commit()


def get_user_notifications(user_id):
    return Message.query.filter_by(user_id=user_id, type="notification").all()


def mark_notification_as_read(notification_id):
    notification = Message.query.get(notification_id)
    if notification:
        notification.read = True
        db.session.commit()


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'png', 'jpg'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=['POST', 'GET'])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = Users.query.filter_by(email=email).first()
        if user and user.password == password:
            login_user(user)
            return redirect("/dashboard")
        else:
            flash("Invalid email or password", "error")
            return redirect(url_for('login'))

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    user = Users.query.all()
    latest_news = News.query.all()
    teachers = Teacher.query.filter_by(grade=current_user.grade).all()
    notifications = get_user_notifications(current_user.id)
    if current_user.role == "student":
        return render_template("student_dashboard.html", latest_news=latest_news, teachers=teachers,
                               notifications=notifications)
    if current_user.role == "teacher":
        return render_template("teacher_dashboard.html", latest_news=latest_news, teachers=teachers,
                               notifications=notifications , user=current_user)
    if current_user.role == "parent":
        return render_template("parent_dashboard.html", notifications=notifications)
    if current_user.role == "admin":
        return render_template("admin_dashboard.html", notifications=notifications)
    else:
        return redirect(url_for('unauthorized'))


@app.route('/notifications')
@login_required
def notifications():
    messages = Message.query.filter_by(student_email=current_user.email).all()
    return render_template('notifications.html', messages=messages)


@app.route('/mark_notification_as_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_as_read(notification_id):
    message = Message.query.get(notification_id)
    if message and message.student_email == current_user.email:
        message.read = True
        db.session.commit()
        flash('Notification marked as read.', 'success')
    else:
        flash('Notification not found or access denied.', 'error')
    return redirect(url_for(''))


# API endpoint to get all events for the dashboard
@app.route('/events', methods=['GET'])
def get_events():
    events = Event.query.all()
    return jsonify([event.to_dict() for event in events])


@app.route("/my_teachers")
def my_teachers():
    if not current_user.is_authenticated:
        # Handle case where user is not authenticated (if applicable)
        # Redirect to login page or handle as per your application's logic
        return redirect(url_for('login'))

    if current_user.role == 'student':
        filtered_subjects = Subjects.query.filter_by(grade=current_user.grade).all()
        teachers = [subject.teacher_name for subject in filtered_subjects]

        return render_template("my_teachers.html", teachers=teachers)

    # Handle other roles or scenarios (if applicable)
    return render_template("my_teachers.html", teachers=[])  # Return empty list if no teachers found


@app.route("/students")
def students():
    students = Students.query.all()
    return render_template("my_students.html", students=students)


@app.route("/send-email/<email>", methods=['GET'])
def send_email_page(email):
    return render_template('send_email.html', email=email)


@app.route('/send-email', methods=['POST'])
@login_required
def send_email():
    teacher_email = current_user.email
    student_email = request.form['email']
    message_content = request.form['message']

    new_message = Message(teacher_email=teacher_email, student_email=student_email, message=message_content)
    db.session.add(new_message)
    db.session.commit()

    flash('Message sent successfully!', 'success')
    return redirect(url_for('students'))




@app.route("/my_subjects")
@login_required
def my_subjects():
    print(f"Current User ID: {current_user.id}")  # Debug statement
    print(f"Current User Role: {current_user.role}")  # Debug statement

    if current_user.role == 'student':
        all_subjects = Subjects.query.all()
        current_user_grade = current_user.grade
        filtered_subjects = [subject for subject in all_subjects if subject.grade == current_user_grade]
        return render_template("my_subjects.html", subjects=filtered_subjects)

    elif current_user.role == 'teacher':
        teacher = Users.query.filter_by(id=current_user.id).first()
        teacher_name = teacher.name
        print(teacher_name)
        if teacher:
            filtered_subjects = Subjects.query.filter_by(teacher_name=teacher_name).all()
            return render_template("my_subjects_teacher.html", subjects=filtered_subjects)
        else:
            print("Teacher record not found.")  # Debug statement
            return redirect("/")

    else:
        print("Role not recognized.")  # Debug statement
        return redirect("/")


@app.route("/sessions")
def sessions():
    return render_template("sessions.html")


@app.route("/assessments")
def assessments():
    return render_template("assessments_assignments.html")


@app.route("/quizzes")
@login_required
def quizzes():
    if current_user.role == "student" or "parent":
        return render_template("quizzes_surveys_teacher.html")

    if current_user.role == "teacher" or "admin":
        return render_template("quiz_creation.html")
    else:
        return redirect(url_for('unauthorized'))


@app.route("/unauthorized")
def unauthorized():
    return "You are not authorized to view this page.", 403

@app.route('/view_subject/<int:subject_id>')
def view_subject(subject_id):
    subject = Subjects.query.get(subject_id)
    if current_user.role == "student":
        lessons = Lessons.query.filter_by(subject_id=subject.id).all()
        lesson_videos = {lesson.id: Videos.query.filter_by(lesson_id=lesson.id).all() for lesson in lessons}
        lesson_files = {lesson.id: Files.query.filter_by(lesson_id=lesson.id).all() for lesson in lessons}
        lesson_quiz = {lesson.id: Quizzes.query.filter_by(lesson_id=lesson.id).all() for lesson in lessons}
        return render_template("view_subject.html", subject=subject, lessons=lessons, lesson_videos=lesson_videos, lesson_files=lesson_files , lesson_quiz=lesson_quiz)
    elif current_user.role == "teacher":
        if subject.teacher_id == current_user.id:
            lessons = Lessons.query.filter_by(subject_id=subject.id).all()
            lesson_videos = {lesson.id: Videos.query.filter_by(lesson_id=lesson.id).all() for lesson in lessons}
            lesson_quiz = {lesson.id: Quizzes.query.filter_by(lesson_id=lesson.id).first() for lesson in lessons}  # Get only the first quiz
            lesson_files = {lesson.id: Files.query.filter_by(lesson_id=lesson.id).all() for lesson in lessons}
            return render_template("view_subject_teacher.html", subject=subject, lessons=lessons, lesson_videos=lesson_videos, lesson_files=lesson_files,lesson_quiz=lesson_quiz)
        else:
            flash("You are not assigned to this subject.", "danger")
            return redirect(url_for('dashboard'))
    else:
        flash("You do not have the necessary permissions to view this page.", "danger")
        return redirect(url_for('dashboard'))

@app.route('/video/<int:video_id>')
def show_video(video_id):
    video = Videos.query.get(video_id)
    if not video:
        return "Video not found", 404
    return render_template('video.html', name=video.name,  video_url=video.url)

@app.route('/download/<path:filename>')
def download_file(filename):
    # Construct the absolute file path
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Debugging: Print the constructed file path and verify
    logging.debug(f'Requested filename: {filename}')
    logging.debug(f'Constructed file path: {file_path}')
    print(f'Constructed file path: {file_path}')  # Print to console for debugging

    # Check if the file exists
    if os.path.exists(file_path):
        logging.debug(f'File found: {file_path}')  # File found
        return send_file(file_path, as_attachment=True)
    else:
        logging.error(f'File not found: {file_path}')  # Error logging
        print(f'File not found: {file_path}')  # Print to console for debugging
        return "File not found", 404





@app.route('/view_teacher/<int:id>')
def view_teacher(id):
    teacher = Teacher.query.filter_by(id=id).first()

    if not teacher:
        abort(404)  # If teacher is not found, return a 404

    return render_template("view_teacher.html", teacher_name=teacher.name, teacher=teacher)


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")


@app.route("/setting")
@login_required
def setting():
    return render_template("profile-settings.html")


@app.route("/setting/security")
def security():
    return render_template("profile-security.html")


@app.route("/setting/notification")
def notification():
    return render_template("profile-notification.html")


@app.route('/create_subject', methods=['GET', 'POST'])
@login_required
def create_subject():
    if request.method == 'POST':
        data = request.get_json()
        subject_name = data.get('name')
        grade = data.get('grade')

        if not subject_name or not grade:
            return jsonify({'error': 'Subject name and grade are required'}), 400

        new_subject = Subjects(name=subject_name, grade=grade, teacher_id=current_user.id,teacher_name=current_user.name)
        db.session.add(new_subject)
        db.session.commit()

        return jsonify({'message': 'Subject created successfully'}), 201
    return render_template('create_subject.html')


@app.route('/create_lesson/<int:subject_id>', methods=['GET', 'POST'])
@login_required
def create_lesson(subject_id):
    subject = Subjects.query.get_or_404(subject_id)

    if subject.teacher_id != current_user.id:
        return jsonify({'error': 'You do not have permission to add a lesson to this subject'}), 403

    if request.method == 'POST':

        lesson_name = request.form['lessonName']
        video_link = request.form['videoLink']
        grade = request.form['grade']
        content = request.form['content']


        if not lesson_name or not grade or not content:
            return jsonify({'error': 'Lesson name, grade, and content are required'}), 400

        # Create a new lesson
        new_lesson = Lessons(name=lesson_name, subject_id=subject_id)
        db.session.add(new_lesson)
        db.session.commit()

        # Handle file upload

        # Create a new video record in the database
        if video_link:
            new_video = Videos(name=lesson_name, url=video_link, lesson_id=new_lesson.id)
            db.session.add(new_video)
            db.session.commit()

        # Return success message
        return jsonify({'message': 'Lesson created successfully'}), 201

    return render_template('create_lesson.html', subject=subject)


@app.route('/create_file/<int:lesson_id>', methods=['GET', 'POST'])
@login_required
def create_file(lesson_id):
    lesson = Lessons.query.get_or_404(lesson_id)
    subject = Subjects.query.get(lesson.subject_id)

    if subject.teacher_id != current_user.id:
        return jsonify({'error': 'You do not have permi ssion to add a file to this lesson'}), 403

    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            new_file = Files(name=filename, path=filename, lesson_id=lesson_id)
            db.session.add(new_file)
            db.session.commit()

            return jsonify({'message': 'File created successfully'}), 201

    return render_template('create_file.html', lesson=lesson)
@app.route('/create_quiz/<int:lesson_id>', methods=['GET', 'POST'])
@login_required
def create_quiz(lesson_id):
    if current_user.role == "teacher":
        lesson = Lessons.query.get_or_404(lesson_id)

        if request.method == 'POST':
            quiz_title = request.form['quizTitle']
            quiz_description = request.form['quizDescription']

            # Create new quiz
            new_quiz = Quizzes(name=quiz_title, lesson_id=lesson_id, user_id=current_user.id)
            db.session.add(new_quiz)
            db.session.commit()

            # Extract all question data
            questions_data = []
            for key in request.form.keys():
                if key.startswith('question') and key[len('question'):].isdigit():
                    question_index = key[len('question'):]
                    question_data = {
                        'question_text': request.form[f'question{question_index}'],
                        'question_type': request.form[f'questionType{question_index}'],
                        'choices': [
                            request.form.get(f'choice{question_index}_1', ''),
                            request.form.get(f'choice{question_index}_2', ''),
                            request.form.get(f'choice{question_index}_3', ''),
                            request.form.get(f'choice{question_index}_4', '')
                        ],
                        'correct_answer': request.form[f'answer{question_index}']
                    }
                    questions_data.append(question_data)

            # Add all questions to the quiz
            for question_data in questions_data:
                question_text = question_data['question_text']
                question_type = question_data['question_type']
                choices = question_data['choices']
                correct_answer = question_data['correct_answer']

                if question_type == 'multiple':
                    correct_choice = choices[int(correct_answer) - 1]
                elif question_type == 'true_false':
                    correct_choice = correct_answer
                elif question_type == 'complete':
                    correct_choice = correct_answer

                new_question = QuizQuestion(
                    quiz_id=new_quiz.id,
                    question_type=question_type,
                    question_text=question_text,
                    options=json.dumps([choice for choice in choices if choice]) if choices else None,
                    correct_answer=correct_choice,
                    score=1  # Modify if needed
                )
                db.session.add(new_question)

            db.session.commit()

            flash("Quiz created successfully!", "success")
            return redirect(url_for('my_subjects'))

        return render_template('create_quiz.html', lesson=lesson)


@app.route('/take_quiz/<int:quiz_id>', methods=['GET'])
@login_required
def take_quiz(quiz_id):
    quiz = Quizzes.query.get_or_404(quiz_id)
    questions = QuizQuestion.query.filter_by(quiz_id=quiz_id).all()
    for question in questions:
        if question.options:
            question.options = json.loads(question.options)
    return render_template('take_quiz.html', quiz=quiz, questions=questions)


@app.route('/submit_quiz/<int:quiz_id>', methods=['POST'])
@login_required
def submit_quiz(quiz_id):
    quiz = Quizzes.query.get_or_404(quiz_id)
    questions = QuizQuestion.query.filter_by(quiz_id=quiz_id).all()
    total_score = 0

    for question in questions:
        user_answer = request.form.get(str(question.id))
        if user_answer is not None:
            if question.question_type == 'multiple' or question.question_type == 'true_false':
                if user_answer == question.correct_answer:
                    total_score += question.score
            elif question.question_type == 'complete':
                if user_answer.strip().lower() == question.correct_answer.strip().lower():
                    total_score += question.score

    quiz_result = QuizResult(user_id=current_user.id, quiz_id=quiz_id, score=total_score,
                             student_email=current_user.email)
    db.session.add(quiz_result)
    db.session.commit()

    return redirect(url_for('quiz_result', quiz_id=quiz_id))


@app.route('/quiz_result/<int:quiz_id>', methods=['GET'])
@login_required
def quiz_result(quiz_id):
    quiz_result = QuizResult.query.filter_by(user_id=current_user.id, quiz_id=quiz_id).first_or_404()
    return render_template('quiz_result.html', score=quiz_result.score)


@app.route('/results/<int:user_id>')
@login_required
def results(user_id):
    if current_user.role == "teacher" and current_user.id == user_id:
        teacher = Users.query.get_or_404(user_id)
        quizzes = Quizzes.query.filter_by(user_id=user_id).all()
        return render_template('quizzes_surveys_teacher.html', teacher_name=teacher.name, quizzes=quizzes)
    else:
        # Handle unauthorized access
        return redirect(url_for('index'))

@app.route('/all_results/<int:quiz_id>')
@login_required
def all_results(quiz_id):
    if current_user.role == "teacher":
        quiz = Quizzes.query.get_or_404(quiz_id)
        results = QuizResult.query.filter_by(quiz_id=quiz_id).all()
        return render_template('all_results.html', quiz_name=quiz.name, results=results, teacher_id=current_user.id)
    else:
        # Handle unauthorized access
        return redirect(url_for('index'))


@app.route('/quizzes_surveys', methods=['GET', 'POST'])
@login_required  # Ensure only logged-in users can access
def quizzes_surveys():
    if request.method == 'POST':
        quiz_id = request.form.get('quiz_id')
        # Handle the quiz form submission logic here
        # For example, redirect the user to the quiz taking page
        return redirect(url_for('take_quiz', quiz_id=quiz_id))
    if current_user.role == "student":
        quizzes = Quizzes.query.all()  # Fetch all quizzes from the database
        return render_template('quizzes_surveys.html', quizzes=quizzes)
    elif current_user.role == "teacher":
        quizzes = Quizzes.query.all()  # Fetch all quizzes from the database
        return render_template('quizzes_surveys_teacher.html', quizzes=quizzes)


# Replace the Twilio credentials with your actual credentials
account_sid = 'ACdebb3c6c4846b66c07a02cb795f33934'
api_key = 'SK1a7e538ed35fe90977890fdef5bf89e9'
api_secret = '6sE6ABJZuT1Gndron4Mv0ZYApZsTeick'

def generate_twilio_access_token(identity, room_name):
    # Create access token
    token = AccessToken(account_sid, api_key, api_secret, identity=identity)

    # Create video grant and add to token
    video_grant = VideoGrant(room=room_name)  # Specify the room name
    token.add_grant(video_grant)

    # Generate token as a JWT string
    return token.to_jwt()

@app.route('/generate-token')
def generate_token():
    # Generate access token for a participant with identity 'example_identity' and room name 'example_room'
    access_token = generate_twilio_access_token('example_identity', 'example_room')
    return jsonify({'access_token': access_token})

@app.route('/zoom')
def index():
    return render_template('zoom.html')


@app.route('/timetable', methods=['GET', 'POST'])
@login_required
def timetable(): # Assuming a function to get the current user

    # Check if a timetable already exists for the teacher
    existing_timetable = Timetable.query.filter_by(teacher_id=current_user.id).first()

    if existing_timetable:
        # Timetable already exists, display it or offer options
        file_url = url_for('uploaded_file', filename=existing_timetable.path)
        return render_template('timetable.html', file_url=file_url, existing=True)
    else:
        # No existing timetable, handle upload
        file_url = None
        if request.method == 'POST':
            if 'file' not in request.files:
                flash('No file part', 'error')
                return redirect(request.url)

            file = request.files['file']

            if file.filename == '':
                flash('No selected file', 'error')
                return redirect(request.url)

            if file:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

                # Create new timetable and associate with teacher
                new_timetable = Timetable(name=filename, path=filename, teacher_id=current_user.id)
                db.session.add(new_timetable)
                db.session.commit()

                flash('File uploaded successfully', 'success')
                file_url = url_for('uploaded_file', filename=filename)

        return render_template('timetable.html', file_url=file_url)

@app.route("/print_timetable")
@login_required
def print_timetable():
    # Logic to access or format existing timetable for printing (adapt based on needs)
    return render_template('print_timetable.html')


# Ensure the uploads folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == "__main__":
     app.run(debug=True)