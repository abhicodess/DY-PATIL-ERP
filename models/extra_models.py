from extensions import db
from datetime import datetime

class Subject(db.Model):
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subject_code = db.Column(db.String(20), unique=True, nullable=True)
    dept = db.Column(db.String(50), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    semester = db.Column(db.String(10), nullable=True)
    teacher = db.Column(db.String(100), nullable=True)
    division = db.Column(db.String(10), nullable=True)
    credits = db.Column(db.Integer)

    @property
    def code(self):
        return self.subject_code

    @code.setter
    def code(self, value):
        self.subject_code = value

class Result(db.Model):
    __tablename__ = 'results'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    student_name = db.Column(db.String(100))
    subject = db.Column(db.String(100), nullable=False)
    exam_type = db.Column(db.String(50))
    marks = db.Column(db.Float)
    total = db.Column(db.Float)
    term = db.Column(db.String(20))
    faculty_id = db.Column(db.Integer, nullable=True)
    roll = db.Column(db.String(50))
    department = db.Column(db.String(100))
    semester = db.Column(db.String(50))
    year = db.Column(db.String(50))
    date = db.Column(db.String(20))
    assignment_marks = db.Column(db.Float, default=0.0)
    attendance_marks = db.Column(db.Float, default=0.0)
    teaching_assessment = db.Column(db.Float, default=0.0)
    ut_marks = db.Column(db.Float, default=0.0)
    mse_marks = db.Column(db.Float, default=0.0)
    tw_marks = db.Column(db.Float, default=0.0)
    pr_or_marks = db.Column(db.Float, default=0.0)
    published = db.Column(db.Integer, default=0)
    result = db.Column(db.String(50))
    grade = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FacultyNotice(db.Model):
    __tablename__ = 'faculty_notices'
    
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FacultyNote(db.Model):
    __tablename__ = 'faculty_notes'
    
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    note_type = db.Column(db.String(50), default='Lecture')
    attachment_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
