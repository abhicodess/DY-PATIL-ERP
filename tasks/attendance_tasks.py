from celery_app import celery
from services.attendance_service import AttendanceService
from services.email_service import EmailService

attendance_service = AttendanceService()
email_service = EmailService()

@celery.task(bind=True, max_retries=3)
def daily_shortage_check(self):
    """Identify students with < 75% attendance and notify them."""
    defaulters = attendance_service.get_defaulters(threshold=75)
    for student in defaulters:
        email_service.send_attendance_alert(student.email, student.attendance_pct)

@celery.task(bind=True, max_retries=3)
def weekly_faculty_report(self):
    """Generate and email attendance reports to HODs."""
    # Logic to summarize and email
    pass

@celery.task(bind=True, max_retries=3)
def process_submitted_attendance(self, session_id):
    """Trigger notifications and rebuild attendance summaries after a session is finalized."""
    from utils.pg_wrapper import qry, qone, exe
    from services.parent_notification_service import ParentNotificationService
    from services.push_notification_service import PushNotificationService

    # 1. Fetch session details
    sess = qone("SELECT * FROM attendance_sessions WHERE id = %s", (session_id,))
    if not sess:
        return f"Session {session_id} not found."

    subject = sess["subject"]
    lecture_date = str(sess["lecture_date"])

    # 2. Get all students marked Absent in this session
    absents = qry("SELECT student_id FROM attendance WHERE lecture_id = %s AND status = 'Absent'", (session_id,))

    push_service = PushNotificationService()

    for a in absents:
        sid = a["student_id"]
        # Twilio SMS to parents of absent student
        try:
            ParentNotificationService.notify_student_parents(
                student_id=sid,
                category='attendance',
                template_slug='student_absent',
                context={'subject': subject, 'date': lecture_date}
            )
        except Exception as e:
            # Let it retry if SMS service fails
            self.retry(exc=e, countdown=10)

        # Firebase Push Notification to student
        try:
            push_service.send_to_user(
                user_id=sid,
                title="Attendance Alert",
                body=f"You were marked Absent for {subject} on {lecture_date}."
            )
        except Exception as e:
            # Silently log push failures
            pass

    # 3. Rebuild attendance_summary for all affected students in this session
    all_marked = qry("SELECT DISTINCT student_id FROM attendance WHERE lecture_id = %s", (session_id,))
    for r in all_marked:
        sid = r["student_id"]
        exe("""
            INSERT INTO attendance_summary (student_id, student_name, subject, attended, total, division, semester, department)
            SELECT 
                s.id, s.name, a.subject,
                COUNT(*) FILTER (WHERE a.status IN ('Present', 'Late')) as attended,
                COUNT(*) as total,
                s.division,
                s.year,
                s.department
            FROM students s
            JOIN attendance a ON s.id = a.student_id
            WHERE s.id = %s AND a.subject = %s
            GROUP BY s.id, s.name, a.subject, s.division, s.department
            ON CONFLICT (student_id, subject) DO UPDATE SET
                student_name = EXCLUDED.student_name,
                attended = EXCLUDED.attended,
                total = EXCLUDED.total,
                division = EXCLUDED.division,
                department = EXCLUDED.department
        """, (sid, subject))

    return f"Processed session {session_id}."
