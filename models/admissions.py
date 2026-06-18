from extensions import db
from datetime import datetime

class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    applicant_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    dept_preference = db.Column(db.String(50), nullable=False)
    score_10th = db.Column(db.Float, nullable=False)
    score_12th = db.Column(db.Float, nullable=False)
    entrance_score = db.Column(db.Float)
    documents_url = db.Column(db.String(255))
    status = db.Column(db.String(20), default='Pending') # Pending, Approved, Rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    token = db.Column(db.String(100), unique=True) # For status checking
