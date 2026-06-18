from extensions import db
from datetime import datetime

class FacultySalary(db.Model):
    __tablename__ = 'faculty_salary'
    
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    basic_salary = db.Column(db.Float, nullable=False)
    hra = db.Column(db.Float, default=0)
    da = db.Column(db.Float, default=0)
    pf_deduction = db.Column(db.Float, default=0)
    net_salary = db.Column(db.Float)
    effective_from = db.Column(db.Date, default=datetime.utcnow)

class Payslip(db.Model):
    __tablename__ = 'payslips'
    
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    gross_salary = db.Column(db.Float)
    net_salary = db.Column(db.Float)
    pdf_url = db.Column(db.String(255))
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
