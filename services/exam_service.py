from repositories.exams_repository import ExamsRepository
from services.attendance_service import AttendanceService

class ExamService:
    def __init__(self):
        self.repository = ExamsRepository()
        self.attendance_service = AttendanceService()

    def validate_eligibility(self, student_id):
        """Standard DY Patil eligibility: 75% attendance overall."""
        stats = self.attendance_service.get_student_stats(student_id)
        return stats['percentage'] >= 75.0

    def get_upcoming_exams(self):
        return self.repository.get_all()

    def generate_hall_ticket(self, student_id, exam_id):
        # Logic to generate hall ticket PDF
        pass
