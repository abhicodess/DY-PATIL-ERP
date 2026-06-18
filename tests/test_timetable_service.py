import unittest
from unittest.mock import MagicMock
from models.timetable_model import TimetableEntry
from services.timetable_service import TimetableService
from repositories.timetable_repository import TimetableRepository

class TestTimetableService(unittest.TestCase):
    def setUp(self):
        self.mock_repo = MagicMock(spec=TimetableRepository)
        self.service = TimetableService(self.mock_repo)

    def test_normalize_time_pads_correctly(self):
        # Happy Path: Single digit hour gets zero-padded
        self.assertEqual(self.service._normalize_time_str("9:30-10:30"), "09:30-10:30")
        self.assertEqual(self.service._normalize_time_str("09:00-11:00"), "09:00-11:00")
        # Edge Case: Malformed or different format
        self.assertEqual(self.service._normalize_time_str("Lunch Break"), "Lunch Break")

    def test_add_slot_detects_conflict(self):
        # Setup: Mock repo to return a clash
        entry = TimetableEntry(None, "Monday", "09:00-10:00", "Math", "Dr. Smith")
        self.mock_repo.check_clash.return_value = {
            'type': 'FACULTY', 
            'entry': {'subject': 'Physics', 'teacher': 'Dr. Smith'}
        }

        result = self.service.add_or_update_slot(entry)
        
        self.assertFalse(result['ok'])
        self.assertIn("Conflict detected", result['error'])
        # Verify repo was called with normalized time
        self.mock_repo.check_clash.assert_called_with(
            day="Monday", time="09:00-10:00", teacher="Dr. Smith", room=None, exclude_id=None, faculty_id=None
        )

    def test_add_slot_success(self):
        # Happy Path
        entry = TimetableEntry(None, "Monday", "9:00-10:00", "Math", "Dr. Smith")
        self.mock_repo.check_clash.return_value = None
        self.mock_repo.save.return_value = 123

        result = self.service.add_or_update_slot(entry)

        self.assertTrue(result['ok'])
        self.assertEqual(result['id'], 123)
        self.mock_repo.save.assert_called_once()

    def test_copy_day_with_skipping_conflicts(self):
        # Setup: Source day has 2 slots, one conflicts on target day
        self.mock_repo.get_all.return_value = [
            TimetableEntry(1, "Mon", "09:00", "S1", "T1"),
            TimetableEntry(2, "Mon", "10:00", "S2", "T2")
        ]
        # First call (S1) returns clash, second (S2) returns None
        self.mock_repo.check_clash.side_effect = [{'type': 'ROOM'}, None]

        result = self.service.copy_day_schedule("Mon", "Tue")

        self.assertEqual(result['count'], 1)
        self.assertEqual(result['conflicts'], 1)

if __name__ == '__main__':
    unittest.main()
