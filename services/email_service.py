import os
from flask import render_template
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from services.student_service import StudentService

class EmailService:
    def __init__(self):
        self.sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        self.from_email = 'no-reply@dypatil.edu'

    def send_welcome_email(self, student_id):
        student_service = StudentService()
        student = student_service.repository.get_by_id(student_id)
        
        html_content = render_template('emails/welcome.html', student=student)
        message = Mail(
            from_email=self.from_email,
            to_emails=student.email,
            subject='Welcome to DY Patil ERP',
            html_content=html_content
        )
        try:
            self.sg.send(message)
        except Exception as e:
            print(f"Error sending email: {e}")

    def send_attendance_alert(self, student_email, percentage):
        html_content = render_template('emails/attendance_alert.html', percentage=percentage)
        message = Mail(
            from_email=self.from_email,
            to_emails=student_email,
            subject='Attendance Alert - Action Required',
            html_content=html_content
        )
        self.sg.send(message)

    def send_deprecation_warning(self, contact_email, version, sunset_date, migration_guide):
        html_content = render_template(
            'email/api_deprecation_notice.html', 
            version=version, 
            sunset_date=sunset_date, 
            migration_guide=migration_guide
        )
        message = Mail(
            from_email=self.from_email,
            to_emails=contact_email,
            subject=f"Action required: {version} API deprecation notice",
            html_content=html_content
        )
        try:
            self.sg.send(message)
        except Exception as e:
            print(f"Error sending deprecation email: {e}")
