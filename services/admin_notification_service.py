import json
import logging
from utils.pg_wrapper import exe

class AdminNotificationService:

    # Message templates — one per event type
    MESSAGES = {
        'timetable_submitted':
            "Prof. {faculty_name} has submitted their timetable "
            "for approval",

        'timetable_resubmitted':
            "Prof. {faculty_name} re-submitted slot: {subject} on "
            "{day} at {time_slot} for {division}. "
            "Previously rejected reason: \"{last_rejected_note}\". "
            "Resubmission #{resubmission_count}",

        'timetable_slot_requested':
            "Prof. {faculty_name} requested a new slot: "
            "{subject} on {day} at {time_slot} for {division} "
            "— awaiting approval",

        'timetable_slot_approved':
            "Your slot {subject} ({day} {time_slot}) has been "
            "approved and added to the master timetable",

        'timetable_slot_rejected':
            "Your slot {subject} ({day} {time_slot}) was not "
            "approved. Reason: {admin_note}",

        'subject_assignment_requested':
            "Prof. {faculty_name} requested to teach {subject_name} "
            "for {division}",

        'subject_assignment_approved':
            "Your request to teach {subject_name} for {division} "
            "has been approved",

        'subject_assignment_rejected':
            "Your request to teach {subject_name} for {division} "
            "was rejected. Reason: {admin_note}",

        'attendance_submitted':
            "Prof. {faculty_name} submitted attendance for "
            "{subject} ({division}) on {date}: "
            "{present_count}/{total_students} present",

        'marks_submitted':
            "Prof. {faculty_name} submitted {exam_type} marks "
            "for {subject} ({division}) — {student_count} students",
    }

    def notify_admin(self, event_type: str, **kwargs) -> None:
        """
        Central method. Never raises — all errors logged silently.
        Saves notification to DB only (no external services yet).
        """
        try:
            message = self._format_message(event_type, kwargs)
            self._save_to_db(
                event_type   = event_type,
                faculty_id   = kwargs.get('faculty_id'),
                faculty_name = kwargs.get('faculty_name', ''),
                message      = message,
                payload      = kwargs,
            )
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(
                f"AdminNotificationService.notify_admin failed "
                f"for {event_type}: {e}"
            )

    def _format_message(self, event_type: str, kwargs: dict) -> str:
        template = self.MESSAGES.get(event_type, f"Event: {event_type}")
        try:
            return template.format(**kwargs)
        except KeyError:
            return template  # return unformatted rather than crashing

    def _save_to_db(self, event_type, faculty_id, faculty_name,
                    message, payload) -> None:
        exe(
            """INSERT INTO admin_notifications
               (event_type, faculty_id, faculty_name, message, payload)
               VALUES (%s, %s, %s, %s, %s)""",
            (event_type, faculty_id, faculty_name,
             message, json.dumps(payload, default=str))
        )

# Module-level singleton — import this everywhere
admin_notifier = AdminNotificationService()
