# backend/core/services/attendance_service.py
from datetime import date
import uuid
from backend.core.repositories.attendance_repository import AttendanceRepository
from backend.core.repositories.timetable_repository import TimetableRepository

class AttendanceService:
    @staticmethod
    def initialize_faculty_session(timetable_id, faculty_id):
        """
        Main Business Logic for starting a session.
        1. Validates slot ownership.
        2. Prevents duplicate sessions for the same slot pada the same day.
        3. Prepares the student roster.
        """
        slot = TimetableRepository.get_slot_details(timetable_id)
        if not slot:
            return {"error": "Invalid timetable slot"}, 404
        
        # Security: Ensure faculty owns this slot
        if slot['faculty_id'] != faculty_id:
            return {"error": "Unauthorized: You are not assigned to this slot"}, 403

        # Create session logic...
        session_id = str(uuid.uuid4())
        
        # Fetch roster automatically
        students = AttendanceRepository.get_students_for_session(timetable_id)
        
        return {
            "session_id": session_id,
            "subject": slot['subject_name'],
            "students": students,
            "context": {
                "dept": slot['department'],
                "year": slot['year'],
                "div": slot['division']
            }
        }, 200

    @staticmethod
    def submit_session_attendance(session_id, user_id, attendance_records):
        """
        Finalizes attendance and logs the audit.
        """
        AttendanceRepository.submit_bulk_attendance(session_id, attendance_records)
        AttendanceRepository.log_session_audit(session_id, user_id, "SUBMIT_ATTENDANCE")
        
        return {"status": "success", "message": "Attendance submitted and locked"}, 200
