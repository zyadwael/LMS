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
from django.shortcuts import render

from flask import send_from_directory
from datetime import datetime

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
        phone_number = db.Column(db.String(1000), unique=True)
        gender = db.Column(db.String(100))
        religion = db.Column(db.String(100))
        role = db.Column(db.String(100))
        grade = db.Column(db.String(100))
        Class = db.Column(db.String(100))
        teacher = db.relationship('Teacher', backref='user', uselist=False)
        student = db.relationship('Students', backref='user', uselist=False)
        subjects = db.relationship('Subjects', backref='teacher')
        quizzes = db.relationship('Quizzes', backref='user')
        parents = db.relationship('Parents', backref='user')
        grades = db.relationship('Grades', backref='student')


    class Subjects(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100))
        teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
        grade = db.Column(db.String(1000))
        Class = db.Column(db.String(1000))
        teacher_name = db.Column(db.String(1000))
        teacher_email = db.Column(db.String(100))
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
        subject_name = db.Column(db.String(100))
        day_of_week = db.Column(db.String(10))
        time_of_day = db.Column(db.String(5))
        grade = db.Column(db.String(100))
        Class = db.Column(db.String(100))
        teacher_email = db.Column(db.String(100))
        teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'))
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
        start_date = db.Column(db.DateTime, nullable=False)
        end_date = db.Column(db.DateTime, nullable=False)

    class Teacher(UserMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100))
        email = db.Column(db.String(100))
        subject = db.Column(db.String(100))
        grade = db.Column(db.String(100))
        Class = db.Column(db.String(100))
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
        timetable_id = db.Column(db.Integer, db.ForeignKey('timetable.id'))  # Foreign key to Timetable

    class Parents(UserMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100))
        email = db.Column(db.String(100), unique=True)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'))


    class Students(UserMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100))
        email = db.Column(db.String(100))
        grade = db.Column(db.String(100))
        Class = db.Column(db.String(100))
        parent_email = db.Column(db.String(1000))
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'))



    class News(UserMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(100))
        content = db.Column(db.String(100))


    class Grades(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
        behavior = db.Column(db.String(100))
        oral_exam = db.Column(db.String(100))
        written_exam = db.Column(db.String(100))
        comments = db.Column(db.String(255))
        attendance = db.Column(db.String(100))
        assignments = db.Column(db.String(100))
        class_projects = db.Column(db.String(100))
        subject_projects = db.Column(db.String(100))
        participation = db.Column(db.String(100))
        class_work = db.Column(db.String(100))


    class Messages(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
        receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
        content = db.Column(db.Text, nullable=False)
        timestamp = db.Column(db.DateTime, default=datetime.utcnow)

        sender = db.relationship('Users', foreign_keys=[sender_id], backref='sent_messages')
        receiver = db.relationship('Users', foreign_keys=[receiver_id], backref='received_messages')

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
admin.add_view(MyModelView(Parents, db.session))
admin.add_view(MyModelView(Subjects, db.session))
admin.add_view(MyModelView(Event, db.session))
admin.add_view(MyModelView(News, db.session))
admin.add_view(MyModelView(Messages, db.session))
admin.add_view(MyModelView(Lessons, db.session))
admin.add_view(MyModelView(Quizzes, db.session))
admin.add_view(MyModelView(QuizResult, db.session))
admin.add_view(MyModelView(QuizQuestion, db.session))
admin.add_view(MyModelView(Files, db.session))
admin.add_view(MyModelView(Timetable, db.session))
admin.add_view(MyModelView(Videos, db.session))
admin.add_view(MyModelView(Grades, db.session))





def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'png', 'jpg'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.template_filter('json_loads')
def json_loads_filter(s):
    return json.loads(s)

@app.context_processor
def utility_processor():
    return dict(enumerate=enumerate)
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
    if current_user.role == "student":
        return render_template("student_dashboard.html", latest_news=latest_news, teachers=teachers)
    if current_user.role == "teacher":
        return render_template("teacher_dashboard.html", latest_news=latest_news, teachers=teachers,
                              user=current_user)
    if current_user.role == "parent":
        my_students = Students.query.filter_by(parent_email=current_user.email).all()
        return render_template("parent_dashboard.html", children=my_students)
    if current_user.role == "admin":
        return render_template("admin_dashboard.html")
    else:
        return redirect(url_for('unauthorized'))









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
        teacher_email = teacher.email
        print(teacher_email)
        if teacher:
            filtered_subjects = Subjects.query.filter_by(teacher_email=teacher_email).all()
            print(f"Number of subjects found: {len(filtered_subjects)}")

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




@app.route("/edit_lesson/<int:lesson_id>", methods=["GET", "POST"])
@login_required
def edit_lesson(lesson_id):
    lesson = Lessons.query.get(lesson_id)
    video = Videos.query.filter_by(lesson_id=lesson_id).first()
    if lesson is None:
        flash("Lesson not found!", "danger")
        return redirect(url_for("view_subject", subject_id=lesson.subject_id))  # Adjust URL based on your logic

    if request.method == "POST":
        lesson.name = request.form["name"]
        video.url = request.form['video']


        try:
            db.session.commit()
            flash("Lesson edited successfully!", "success")
            return redirect(url_for("view_subject", subject_id=lesson.subject_id))  # Adjust URL based on your logic
        except Exception as e:
            db.session.rollback()
            flash(f"Error editing lesson: {e}", "danger")

    return render_template("edit_lesson.html", lesson=lesson,video=video)

@app.route('/edit_quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def edit_quiz(quiz_id):
    if current_user.role != "teacher":
        abort(403)

    quiz = Quizzes.query.get_or_404(quiz_id)
    quiz_questions = QuizQuestion.query.filter_by(quiz_id=quiz.id).all()

    if request.method == 'POST':
        # Update quiz details
        quiz.name = request.form['name']
        quiz.description = request.form['description']
        db.session.commit()

        # Process each question
        for question in quiz_questions:
            question_text = request.form.get(f'questionText{question.id}', '')
            question_type = request.form.get(f'questionType{question.id}', '')

            # Update question attributes
            question.question_text = question_text
            question.question_type = question_type

            if question_type == 'multiple':
                choices = [
                    request.form.get(f'choice{question.id}_{i + 1}', '')
                    for i in range(4)  # Assuming maximum 4 choices
                ]
                question.options = json.dumps(choices) if choices else json.dumps([])
                correct_answer_index = request.form.get(f'correct_answer{question.id}', '1')
                question.correct_answer = choices[int(correct_answer_index) - 1]

            elif question_type == 'true_false':
                question.options = json.dumps(['True', 'False'])
                question.correct_answer = request.form.get(f'trueFalse{question.id}', 'true')

            elif question_type == 'short_answer':
                question.options = json.dumps([])
                question.correct_answer = request.form.get(f'short_answer{question.id}', '')

        db.session.commit()
        flash("Quiz updated successfully!", "success")
        return redirect(url_for('edit_quiz', quiz_id=quiz_id))

    return render_template('edit_quiz.html', quiz=quiz, quiz_questions=quiz_questions)



@app.route('/delete_question/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    try:
        # Retrieve the question to be deleted
        question = QuizQuestion.query.get_or_404(question_id)

        # Delete the question from the database
        db.session.delete(question)
        db.session.commit()

        return jsonify({'message': f'Question {question_id} deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



@app.route('/add_question', methods=['POST'])
def add_question():
    # Extract form data
    quiz_id = request.form.get('quiz_id')
    question_id = request.form.get('question_id')  # Get question ID from the form (if applicable)
    question_text = request.form.get('questionText')
    question_type = request.form.get('questionType')


    try:
        options = [choice for choice in request.form.getlist(f'choices_{question_id}')] if question_id else []  # Access options with question ID (if present)
        options_json = json.dumps(options)  # Convert options list to JSON string

        correct_answer = request.form.get(f'correct_answer_{question_id}')  # Access correct answer with question ID (if present)

        # Create and save QuizQuestion object
        new_question = QuizQuestion(
            quiz_id=quiz_id,
            question_text=question_text,
            question_type=question_type,
            options=options_json,  # Use options_json string
            correct_answer=correct_answer,
            score=1  # Assuming score is not used yet
        )
        db.session.add(new_question)
        db.session.commit()

        return jsonify({'message': 'Question added successfully'})
    except Exception as e:
        print(f"Error adding question: {e}")
        return jsonify({'error': 'An error occurred while adding the question.'}), 500



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
        teacher = Users.query.filter_by(id=current_user.id).first()
        teacher_email = teacher.email
        data = request.get_json()
        subject_name = data.get('name')
        grade = data.get('grade')

        if not subject_name or not grade:
            return jsonify({'error': 'Subject name and grade are required'}), 400

        new_subject = Subjects(name=subject_name, grade=grade, teacher_id=current_user.id,teacher_name=current_user.name,teacher_email=teacher_email)
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
            start_date_str = request.form['startDate'] + ' ' + request.form['startTime']
            end_date_str = request.form['endDate'] + ' ' + request.form['endTime']
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M')

            # Create new quiz
            new_quiz = Quizzes(
                name=quiz_title,
                lesson_id=lesson_id,
                user_id=current_user.id,
                start_date=start_date,
                end_date=end_date
            )
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

    # Check if the quiz has already been submitted by the student
    result = QuizResult.query.filter_by(quiz_id=quiz_id, student_email=current_user.email).first()
    if result:
        flash('You have already submitted this quiz.', 'warning')
        return redirect(url_for('quizzes_surveys'))

    # Check if the current time is within the quiz's start and end dates
    current_time = datetime.now()
    print(f"Current Time: {current_time}, Quiz Start: {quiz.start_date}, Quiz End: {quiz.end_date}")

    if current_time < quiz.start_date or current_time > quiz.end_date:
        flash('The quiz is not available at this time.', 'warning')
        return redirect(url_for('quizzes_surveys'))

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
        return render_template('results.html', teacher_name=teacher.name, quizzes=quizzes)
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

    quizzes = Quizzes.query.all()  # Fetch all quizzes from the database
    return render_template('quizzes_surveys.html', quizzes=quizzes)




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
def timetable():
    if request.method == 'POST':

        subject_name = request.form.get('subject_name')
        day_of_week = request.form.get('day_of_week')
        time_of_day = request.form.get('time_of_day')
        grade = request.form.get('grade')
        Class = request.form.get('Class')
        teacher_email = request.form.get('teacher_email')

        new_timetable = Timetable(
            subject_name=subject_name,
            day_of_week=day_of_week,
            time_of_day=time_of_day,
            grade=grade,
            Class=Class,
            teacher_email=teacher_email
        )

        db.session.add(new_timetable)
        db.session.commit()

        flash('Timetable created successfully!', category='success')
        return redirect(url_for('timetable'))
    else:
        teachers = Teacher.query.all()
        return render_template('create_timetable.html', teachers=teachers)

@app.route("/view_timetable")
@login_required
def view_timetable():
    if current_user.role == "teacher":
        teacher_email = current_user.email
        timetables = Timetable.query.filter_by(teacher_email=teacher_email).all()
    elif current_user.role == "student":
        grade = current_user.grade
        Class = current_user.Class
        timetables = Timetable.query.filter_by(grade=grade, Class=Class).all()

    schedule = {day: {} for day in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]}

    for entry in timetables:
        day = entry.day_of_week
        time = entry.time_of_day
        if time not in schedule[day]:
            schedule[day][time] = []
        schedule[day][time].append(entry)

    return render_template('view_timetable.html', schedule=schedule)


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

@app.route('/send_message', methods=['GET', 'POST'])
@login_required
def send_message():
    if request.method == 'POST':
        receiver_email = request.form['receiver_email']
        content = request.form['content']

        receiver = Users.query.filter_by(email=receiver_email).first()
        if not receiver:
            flash('Receiver not found', 'danger')
            return redirect(url_for('send_message'))

        message = Messages(sender_id=current_user.id, receiver_id=receiver.id, content=content)
        db.session.add(message)
        db.session.commit()

        flash('Message sent successfully!', 'success')
        return redirect(url_for('send_message'))

    return render_template('send_message.html')

@app.route('/messages')
@login_required
def view_messages():
    received_messages = Messages.query.filter_by(receiver_id=current_user.id).all()
    sent_messages = Messages.query.filter_by(sender_id=current_user.id).all()
    return render_template('view_messages.html', received_messages=received_messages, sent_messages=sent_messages)

@app.route("/test")
def test():
    s=1
    subject = Subjects.query.get(s)
    print(subject)


@app.route('/update_grades', methods=['POST'])
def update_grades():
    data = request.form
    for student_id in data.keys():
        grade = Grades.query.filter_by(student_id=student_id).first()
        if grade:
            grade.behavior = data.get(f'behavior{student_id}')
            grade.oral_exam = data.get(f'oral_exam{student_id}')
            grade.written_exam = data.get(f'written_exam{student_id}')
            grade.comments = data.get(f'comments{student_id}')
            grade.attendance = data.get(f'attendance{student_id}')
            grade.assignments = data.get(f'assignments{student_id}')
            grade.class_projects = data.get(f'class_projects{student_id}')
            grade.subject_projects = data.get(f'subject_projects{student_id}')
            grade.participation = data.get(f'participation{student_id}')
            grade.class_work = data.get(f'class_work{student_id}')
            db.session.commit()
    return redirect(url_for('index'))

@app.route('/save_term_marks', methods=['GET', 'POST'])
def save_term_marks():
    if request.method == 'POST':
        student_ids = request.form.getlist('student_id')
        for student_id in student_ids:
            behavior = request.form.get(f'behavior{student_id}')
            oral_exam = request.form.get(f'oral_exam{student_id}')
            written_exam = request.form.get(f'written_exam{student_id}')
            comments = request.form.get(f'comments{student_id}')
            attendance = request.form.get(f'attendance{student_id}')
            assignments = request.form.get(f'assignments{student_id}')
            class_projects = request.form.get(f'class_projects{student_id}')
            subject_projects = request.form.get(f'subject_projects{student_id}')
            participation = request.form.get(f'participation{student_id}')
            class_work = request.form.get(f'class_work{student_id}')

            grade = Grades.query.filter_by(student_id=student_id).first()
            if grade:
                grade.behavior = behavior
                grade.oral_exam = oral_exam
                grade.written_exam = written_exam
                grade.comments = comments
                grade.attendance = attendance
                grade.assignments = assignments
                grade.class_projects = class_projects
                grade.subject_projects = subject_projects
                grade.participation = participation
                grade.class_work = class_work
            else:
                new_grade = Grades(
                    student_id=student_id,
                    behavior=behavior,
                    oral_exam=oral_exam,
                    written_exam=written_exam,
                    comments=comments,
                    attendance=attendance,
                    assignments=assignments,
                    class_projects=class_projects,
                    subject_projects=subject_projects,
                    participation=participation,
                    class_work=class_work
                )
                db.session.add(new_grade)
        db.session.commit()
        return redirect(url_for('save_term_marks'))
    else:
        grade = request.args.get('grade')
        if grade:
            students = Students.query.filter_by(grade=grade).all()
            student_ids = [student.id for student in students]
            grades = {g.student_id: g for g in Grades.query.filter(Grades.student_id.in_(student_ids)).all()}
        else:
            students = []
            grades = {}
        return render_template('grade_marks_teacher.html', students=students, grades=grades)



if __name__ == "__main__":
     app.run(debug=True)