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
    semester = db.Column(db.String(50))
    date = db.Column(db.String(20))
    assignment_marks = db.Column(db.Float, default=0.0)
    attendance_marks = db.Column(db.Float, default=0.0)
    teaching_assessment = db.Column(db.Float, default=0.0)
    ut_marks = db.Column(db.Float, default=0.0)
    mse_marks = db.Column(db.Float, default=0.0)
    remarks = db.Column(db.String(255), default='')
    subject_code = db.Column(db.String(50), default='')
    prn_number = db.Column(db.String(50), default='')
    ut_published = db.Column(db.Boolean, default=False)
    mse_published = db.Column(db.Boolean, default=False)
    result_published = db.Column(db.Boolean, default=False)
    grade = db.Column(db.String(10), default='')
    result = db.Column(db.String(50), default='')
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

class SubjectMaster(db.Model):
    __tablename__ = 'subjects_master'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_code = db.Column(db.String(50), unique=True, nullable=False)
    subject_name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50))
    semester = db.Column(db.String(50))
    max_assignment = db.Column(db.Integer, default=5)
    max_attendance = db.Column(db.Integer, default=5)
    max_teaching = db.Column(db.Integer, default=10)
    max_ut = db.Column(db.Integer, default=20)
    max_mse = db.Column(db.Integer, default=20)
    max_tw = db.Column(db.Integer, default=0)
    max_pr_or = db.Column(db.Integer, default=0)
    max_total = db.Column(db.Integer, default=60)


class MarksComponents(db.Model):
    __tablename__ = 'marks_components'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'))
    semester = db.Column(db.String(50), nullable=False)
    component_type = db.Column(db.String(100), nullable=False)
    max_marks = db.Column(db.Float, default=100.0)
    obtained_marks = db.Column(db.Float, nullable=True)
    is_absent = db.Column(db.Boolean, default=False)
    entered_by = db.Column(db.Integer, db.ForeignKey('faculty.id', ondelete='SET NULL'), nullable=True)
    is_overridden = db.Column(db.Boolean, default=False)
    reason_for_override = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

