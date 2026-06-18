from extensions import celery
from services.push_notification_service import PushNotificationService
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from utils.pg_wrapper import qone, qry

push_service = PushNotificationService()

@celery.task(bind=True, max_retries=3)
def send_push_notification_task(self, user_id, title, body):
    """Asynchronously send push notifications to ensure UI responsiveness."""
    return push_service.send_to_user(user_id, title, body)

@celery.task(bind=True, max_retries=3)
def broadcast_notification_task(self, topic, title, body):
    """Broadcast notifications to all users subscribed to a specific topic."""
    return push_service.send_to_topic(topic, title, body)

@celery.task(bind=True, max_retries=3)
def send_application_confirmation(self, application_id):
    """Send email via SendGrid to confirm application receipt."""
    app = qone("SELECT * FROM applications WHERE id = :id", {"id": application_id})
    if not app:
        return
    
    docs = qry("SELECT document_type, verified FROM application_documents WHERE application_id = :id", {"id": application_id})
    uploaded_types = {d['document_type'] for d in docs}
    
    core_docs = ['SSC_MARKSHEET', 'HSC_MARKSHEET', 'LEAVING_CERTIFICATE', 'PHOTO', 'SIGNATURE']
    pending_docs = [d for d in core_docs if d not in uploaded_types]
    pending_str = ", ".join(pending_docs) if pending_docs else "None"
    
    sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
    html_content = f"""
    <h3>Dear {app['applicant_name']},</h3>
    <p>We have successfully received your application for the <strong>{app['applied_department']}</strong> department.</p>
    <p><strong>Application Token:</strong> {app['token']}</p>
    <p><strong>Documents Pending Upload:</strong> {pending_str}</p>
    <p>You can check your application status at any time here: <a href="http://localhost:8000/admissions/status/{app['token']}">Check Status</a></p>
    <br>
    <p>Best Regards,<br>Admissions Office<br>DY Patil College ERP</p>
    """
    
    message = Mail(
        from_email='no-reply@dypatil.edu',
        to_emails=app['applicant_email'],
        subject=f"Application Received — Token: {app['token']}",
        html_content=html_content
    )
    try:
        sg.send(message)
    except Exception as e:
        self.retry(exc=e, countdown=10)

@celery.task(bind=True, max_retries=3)
def send_offer_letter(self, application_id):
    """Send email via SendGrid with offer of admission."""
    app = qone("SELECT * FROM applications WHERE id = :id", {"id": application_id})
    if not app:
        return
    
    sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
    html_content = f"""
    <h3>Dear {app['applicant_name']},</h3>
    <p><strong>Congratulations!</strong> We are pleased to offer you admission to the <strong>{app['applied_department']}</strong> department.</p>
    <p><strong>Your Rank:</strong> {app['rank_in_department']}</p>
    <p><strong>Reporting Date:</strong> 2026-06-15</p>
    <p>Please bring the following original documents for physical verification:
        <ul>
            <li>SSC Marksheet</li>
            <li>HSC Marksheet</li>
            <li>Leaving Certificate</li>
            <li>Caste Certificate (if applicable)</li>
            <li>Domicile Certificate</li>
            <li>Passport Photo & Signature</li>
        </ul>
    </p>
    <br>
    <p>Best Regards,<br>Admissions Office<br>DY Patil College ERP</p>
    """
    
    message = Mail(
        from_email='no-reply@dypatil.edu',
        to_emails=app['applicant_email'],
        subject="Congratulations — Offer of Admission",
        html_content=html_content
    )
    try:
        sg.send(message)
    except Exception as e:
        self.retry(exc=e, countdown=10)

@celery.task(bind=True, max_retries=3)
def send_status_update(self, application_id, new_status):
    """Send SMS via Twilio to applicant phone on status change."""
    app = qone("SELECT * FROM applications WHERE id = :id", {"id": application_id})
    if not app:
        return
    
    link = f"http://localhost:8000/admissions/status/{app['token']}"
    message_text = f"Your DY Patil application {app['token']} status: {new_status}. Check details at {link}"
    
    from services.sms.factory import SMSFactory
    try:
        provider = SMSFactory.get_provider()
        provider.send_sms(app['applicant_phone'], message_text)
    except Exception as e:
        self.retry(exc=e, countdown=10)

@celery.task(bind=True, max_retries=3, default_retry_delay=10)
def notify_low_attendance(self, student_ids):
    """Notify students with low attendance (< 75%) via SMS and Push Notification."""
    if not student_ids:
        return "No students to notify"
        
    from services.sms.factory import SMSFactory
    try:
        provider = SMSFactory.get_provider()
    except Exception:
        provider = None
        
    chunk_size = 100
    for i in range(0, len(student_ids), chunk_size):
        chunk = student_ids[i:i+chunk_size]
        students = qry("SELECT id, name, phone FROM students WHERE id = ANY(%s) AND is_active = TRUE", (chunk,))
        
        for s in students:
            sid = s["id"]
            name = s["name"]
            phone = s["phone"]
            
            msg = f"Dear {name}, your cumulative attendance is below 75%. Please contact your department coordinator."
            
            try:
                push_service.send_to_user(sid, "Attendance Shortage Alert", msg)
            except Exception:
                pass
                
            if provider and phone:
                try:
                    provider.send_sms(phone, msg)
                except Exception as se:
                    self.retry(exc=se, countdown=60)
                    
    return f"Notifications dispatched for {len(student_ids)} students"

@celery.task
def daily_attendance_digest():
    """Daily task at 6 PM IST to check attendance levels and trigger shortage notifications."""
    stats = qry("""
        SELECT student_id, 
               COUNT(*) as total,
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE s.is_active = TRUE
        GROUP BY student_id
    """)
    
    defaulter_ids = []
    for row in stats:
        total = row["total"]
        present = row["present"]
        if total > 0:
            pct = (present / total) * 100
            if pct < 75.0:
                defaulter_ids.append(row["student_id"])
                
    if defaulter_ids:
        from utils.tenant_context import get_tenant_id
        notify_low_attendance.delay(defaulter_ids, _tenant_id=get_tenant_id())
        
    return f"Processed daily attendance digest. Found {len(defaulter_ids)} defaulters."

@celery.task(base=celery.Task, name="tasks.notification_tasks.dispatch_daily_attendance_digests")
def dispatch_daily_attendance_digests():
    """Global task to fetch all active tenants and trigger their daily digests."""
    from utils.pg_wrapper import get_public_db
    with get_public_db() as cur:
        cur.execute("SELECT id FROM public.tenants WHERE is_active = true")
        tenants = cur.fetchall()
        for t in tenants:
            daily_attendance_digest.delay(_tenant_id=t['id'])
