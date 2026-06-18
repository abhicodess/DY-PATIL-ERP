import pytest
from services.attendance_service import AttendanceService
from models.attendance import Attendance
from datetime import datetime

class TestAttendanceService:
    @pytest.fixture(autouse=True)
    def setup(self, session):
        self.service = AttendanceService()
        self.session = session

    def test_mark_attendance_present(self, student, faculty):
        record = self.service.mark_attendance(
            student_id=student.id,
            subject="Mathematics",
            status="Present",
            faculty_id=faculty.id
        )
        assert record.id is not None
        assert record.status == "Present"
        assert record.student_id == student.id

    def test_mark_attendance_absent(self, student, faculty):
        record = self.service.mark_attendance(
            student_id=student.id,
            subject="Mathematics",
            status="Absent",
            faculty_id=faculty.id
        )
        assert record.status == "Absent"

    def test_get_student_stats_perfect(self, student, faculty):
        # Mark 2 present
        self.service.mark_attendance(student.id, "Math", "Present", faculty.id)
        self.service.mark_attendance(student.id, "Math", "Present", faculty.id)
        
        stats = self.service.get_student_stats(student.id)
        assert stats['total'] == 2
        assert stats['present'] == 2
        assert stats['percentage'] == 100.0

    def test_get_student_stats_half(self, student, faculty):
        # 1 present, 1 absent
        self.service.mark_attendance(student.id, "Math", "Present", faculty.id)
        self.service.mark_attendance(student.id, "Math", "Absent", faculty.id)
        
        stats = self.service.get_student_stats(student.id)
        assert stats['percentage'] == 50.0

    def test_get_student_stats_empty(self, student):
        stats = self.service.get_student_stats(student.id)
        assert stats['total'] == 0
        assert stats['percentage'] == 0.0
