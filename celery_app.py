from celery import Celery
from kombu import Queue
import os
from tasks.base_task import TenantTask

celery = Celery(
    "erp_tasks",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/1"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1"),
    include=[
        "tasks.attendance_tasks", 
        "tasks.notification_tasks", 
        "tasks.student_tasks",
        "tasks.reports.attendance_reports",
        "tasks.reports.results_reports",
        "tasks.reports.hr_reports",
        "utils.report_cleanup",
        "tasks.sms_tasks"
    ]
)

celery.Task = TenantTask

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    
    # Celery Beat schedule
    beat_schedule={
        "daily-attendance-digest-at-6pm": {
            "task": "tasks.notification_tasks.dispatch_daily_attendance_digests",
            "schedule": 86400.0,  # runs once a day
        }
    },
    
    # Queue declarations
    task_default_queue="default",
    task_queues=(
        Queue("default", routing_key="default"),
        Queue("critical", routing_key="critical"),
        Queue("bulk", routing_key="bulk"),
        Queue("scheduled", routing_key="scheduled"),
    ),
    
    # Task routing
    task_routes={
        # Bulk tasks
        "tasks.student_tasks.process_student_import": {"queue": "bulk"},
        
        # Critical notification tasks
        "tasks.notification_tasks.notify_low_attendance": {"queue": "critical"},
        "tasks.notification_tasks.send_push_notification_task": {"queue": "critical"},
        "tasks.notification_tasks.broadcast_notification_task": {"queue": "critical"},
        "tasks.notification_tasks.send_application_confirmation": {"queue": "critical"},
        "tasks.notification_tasks.send_offer_letter": {"queue": "critical"},
        "tasks.notification_tasks.send_status_update": {"queue": "critical"},
        "tasks.sms_tasks.send_async_sms": {"queue": "critical"},
        
        # Scheduled digest tasks
        "tasks.notification_tasks.dispatch_daily_attendance_digests": {"queue": "scheduled"},
        "tasks.notification_tasks.daily_attendance_digest": {"queue": "scheduled"},
        
        # Report tasks routing
        "tasks.reports.hr_reports.generate_institution_summary": {"queue": "bulk"},
        "tasks.reports.attendance_reports.*": {"queue": "default"},
        "tasks.reports.results_reports.*": {"queue": "default"},
        "tasks.reports.hr_reports.*": {"queue": "default"},
        "utils.report_cleanup.*": {"queue": "scheduled"},
        
        # Default queue fallback
        "tasks.attendance_tasks.*": {"queue": "default"},
    }
)

# Apply crontab schedules
from celery.schedules import crontab

celery.conf.beat_schedule["daily-attendance-digest-at-6pm"] = {
    "task": "tasks.notification_tasks.dispatch_daily_attendance_digests",
    "schedule": crontab(hour=18, minute=0),  # 6 PM daily
}

celery.conf.beat_schedule["hourly-report-cleanup"] = {
    "task": "utils.report_cleanup.dispatch_tenant_report_cleanups",
    "schedule": crontab(minute=0),  # Every hour
}
