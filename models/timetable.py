from extensions import db
from datetime import datetime

class Timetable(db.Model):
    __tablename__ = 'timetable'
    
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(50), nullable=False)  # Legacy string time
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    subject_id = db.Column(db.Integer)
    subject = db.Column(db.String(100), nullable=False)
    teacher = db.Column(db.String(100))
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'))
    room = db.Column(db.String(50))
    division = db.Column(db.String(10))
    branch = db.Column(db.String(50))
    year = db.Column(db.String(10))
    semester = db.Column(db.String(10))
    slot_type = db.Column(db.String(20), default='Theory')
    color = db.Column(db.String(20))
    published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FacultySubjectAssignment(db.Model):
    __tablename__ = 'faculty_subject_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id', ondelete='CASCADE'))
    subject_id = db.Column(db.Integer)
    subject_name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    semester = db.Column(db.String(10), nullable=False)
    class_name = db.Column(db.String(50), nullable=False)
    division = db.Column(db.String(10), nullable=False)
    academic_year = db.Column(db.String(20), default='2025-26')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('faculty_id', 'subject_id', 'division', name='_fac_sub_div_uc'),)
