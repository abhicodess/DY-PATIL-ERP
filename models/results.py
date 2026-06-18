from extensions import db
from datetime import datetime

class Mark(db.Model):
    __tablename__ = 'marks'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    student_name = db.Column(db.String(100))
    subject = db.Column(db.String(100), nullable=False)
    exam_type = db.Column(db.String(50)) # Unit Test, End Sem, etc.
    marks = db.Column(db.Float)
    total = db.Column(db.Float)
    term = db.Column(db.String(20))
    # FIX: Add missing fields used in marks routes to avoid SQLite errors during tests
    faculty_id = db.Column(db.Integer, nullable=True)
    roll = db.Column(db.String(50))
    department = db.Column(db.String(100))
    date = db.Column(db.String(20))
    assignment_marks = db.Column(db.Float, default=0.0)
    attendance_marks = db.Column(db.Float, default=0.0)
    teaching_assessment = db.Column(db.Float, default=0.0)
    ut_marks = db.Column(db.Float, default=0.0)
    mse_marks = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ResultSummary(db.Model):
    __tablename__ = 'result_summary'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    semester = db.Column(db.String(10))
    sgpa = db.Column(db.Float)
    cgpa = db.Column(db.Float)
    result_status = db.Column(db.String(20)) # Pass, Fail, ATKT
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
