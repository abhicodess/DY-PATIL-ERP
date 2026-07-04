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
    status = db.Column(db.String(20), default='pending')
    admin_note = db.Column(db.Text, default='')
    requested_at = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('faculty_id', 'subject_id', 'division', name='_fac_sub_div_uc'),)

class FacultyTimetable(db.Model):
    __tablename__ = 'faculty_timetable'
    
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, nullable=False)
    faculty_name = db.Column(db.String(100), nullable=False)
    day = db.Column(db.String(20), nullable=False)
    time_slot = db.Column(db.String(50), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    division = db.Column(db.String(10), nullable=False)
    room = db.Column(db.String(50), default='')
    slot_type = db.Column(db.String(20), default='Theory')
    semester = db.Column(db.String(10), default='')
    academic_year = db.Column(db.String(20), default='')
    status = db.Column(db.String(20), default='draft')
    admin_note = db.Column(db.Text, default='')
    resubmission_count = db.Column(db.Integer, default=0)
    last_rejected_note = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class AdminNotification(db.Model):
    __tablename__ = 'admin_notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False)
    faculty_id = db.Column(db.Integer)
    faculty_name = db.Column(db.String(100))
    message = db.Column(db.Text, nullable=False)
    payload = db.Column(db.Text, default='{}')
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

