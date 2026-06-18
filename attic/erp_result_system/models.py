import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    prn = db.Column(db.String(50), unique=True, nullable=False)
    division = db.Column(db.String(1), nullable=False) # A, B, C, D

    results = db.relationship('Result', backref='student', lazy=True)

class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    subject_code = db.Column(db.String(20), unique=True, nullable=False)
    subject_name = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    max_marks = db.Column(db.Integer, default=60)

    results = db.relationship('Result', backref='subject', lazy=True)

class Result(db.Model):
    __tablename__ = 'results'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    semester = db.Column(db.String(20), nullable=False)
    
    assignment_marks = db.Column(db.Float, default=0.0) # out of 5
    attendance_marks = db.Column(db.Float, default=0.0) # out of 5
    ut_marks = db.Column(db.Float, default=0.0)         # out of 20
    mse_marks = db.Column(db.Float, default=0.0)        # out of 20

    @property
    def total_marks(self):
        return (self.assignment_marks or 0) + (self.attendance_marks or 0) + (self.ut_marks or 0) + (self.mse_marks or 0)

    @property
    def grade_info(self):
        T = self.total_marks
        if T >= 50: return 'A', 9
        elif T >= 45: return 'B', 8
        elif T >= 40: return 'C', 7
        elif T >= 35: return 'D', 6
        else: return 'F', 0
