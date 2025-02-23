from datetime import datetime
from . import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    lectures = db.relationship('Lecture', backref='user', lazy=True)
    question_sets = db.relationship('QuestionSet', backref='user', lazy=True)

class Lecture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    summaries = db.relationship('Summary', backref='lecture', lazy=True)

class Summary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lecture_id = db.Column(db.Integer, db.ForeignKey('lecture.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    page_number = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class QuestionSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    questions = db.relationship('Question', backref='question_set', cascade='all, delete-orphan', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.String(500), nullable=False)
    options = db.Column(db.String(500), nullable=False)  # Stored as JSON string
    correct_answer = db.Column(db.String(500), nullable=False)
    set_id = db.Column(db.Integer, db.ForeignKey('question_set.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
