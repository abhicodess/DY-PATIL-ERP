from extensions import db
from datetime import datetime

class Assessment(db.Model):
    __tablename__ = 'assessments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=True)
    
    # Assignments
    assignment_1 = db.Column(db.String(255), default='')
    assignment_2 = db.Column(db.String(255), default='')
    assignment_3 = db.Column(db.String(255), default='')
    assignment_4 = db.Column(db.String(255), default='')
    assignment_5 = db.Column(db.String(255), default='')
    
    # Research & Publications
    paper_q1 = db.Column(db.String(255), default='')
    paper_q2 = db.Column(db.String(255), default='')
    paper_q3 = db.Column(db.String(255), default='')
    paper_q4 = db.Column(db.String(255), default='')
    patent_publication = db.Column(db.String(255), default='')
    copyright = db.Column(db.String(255), default='')
    
    # Projects & Documentation
    project_review_1 = db.Column(db.String(255), default='')
    project_review_2 = db.Column(db.String(255), default='')
    implementation_documentation = db.Column(db.Text, default='')
    
    # Faculty Remark
    remark = db.Column(db.Text, default='')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
