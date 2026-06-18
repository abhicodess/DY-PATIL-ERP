# backend/core/repositories/timetable_repository.py
from backend.core.repositories.base_repository import BaseRepository

class TimetableRepository(BaseRepository):
    @staticmethod
    def get_slot_details(timetable_id):
        """
        Retrieves full academic context for a timetable slot.
        Used to prevent manual subject/session entry and ensure timetable-driven flow.
        """
        sql = """
            SELECT t.id, t.subject_id, t.faculty_id, t.day_of_week, t.start_time, t.end_time,
                   sub.name as subject_name, sub.department, sub.year, sub.division
            FROM timetable t
            JOIN subjects sub ON t.subject_id = sub.id
            WHERE t.id = %s
        """
        return TimetableRepository.fetch_one(sql, (timetable_id,))

    @staticmethod
    def get_faculty_current_slots(faculty_id, day_of_week):
        """Fetches active slots for a faculty member for a specific day."""
        sql = """
            SELECT t.id, sub.name as subject, t.start_time
            FROM timetable t
            JOIN subjects sub ON t.subject_id = sub.id
            WHERE t.faculty_id = %s AND t.day_of_week = %s
            ORDER BY t.start_time
        """
        return TimetableRepository.fetch_all(sql, (faculty_id, day_of_week))

    @staticmethod
    def check_conflict(room_id, day_of_week, start_time, end_time):
        """Enterprise feature: Room/Faculty conflict detection."""
        sql = """
            SELECT id FROM timetable
            WHERE room_id = %s AND day_of_week = %s 
            AND (start_time, end_time) OVERLAPS (%s, %s)
        """
        return TimetableRepository.fetch_one(sql, (room_id, day_of_week, start_time, end_time))
