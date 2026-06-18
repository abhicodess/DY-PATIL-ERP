from repositories.base_repository import BaseRepository
from models.timetable import Timetable

class TimetableRepository(BaseRepository):
    def __init__(self):
        super().__init__(Timetable)

    def get_all(self, filters=None):
        if not filters:
            return super().get_all()
        query = Timetable.query
        for key, value in filters.items():
            if value and hasattr(Timetable, key):
                query = query.filter(getattr(Timetable, key) == value)
        return query.all()

    def get_by_division(self, branch, year, division):
        return Timetable.query.filter_by(
            branch=branch, 
            year=year, 
            division=division, 
            published=True
        ).all()

    def get_by_faculty(self, faculty_id):
        return Timetable.query.filter_by(faculty_id=faculty_id, published=True).all()

    def check_clash(self, day, time, teacher=None, room=None, exclude_id=None, faculty_id=None):
        query = Timetable.query.filter_by(day=day, time=time)
        if exclude_id:
            query = query.filter(Timetable.id != exclude_id)
        if faculty_id:
            f_clash = query.filter_by(faculty_id=faculty_id).first()
            if f_clash:
                return {'type': 'FACULTY', 'entry': {'subject': f_clash.subject, 'teacher': f_clash.teacher}}
        if teacher:
            t_clash = query.filter_by(teacher=teacher).first()
            if t_clash:
                return {'type': 'FACULTY', 'entry': {'subject': t_clash.subject, 'teacher': t_clash.teacher}}
        if room:
            r_clash = query.filter_by(room=room).first()
            if r_clash:
                return {'type': 'ROOM', 'entry': {'subject': r_clash.subject, 'room': r_clash.room}}
        return None

    def save(self, entry):
        from extensions import db
        # If it's a domain dataclass, convert to model
        if not hasattr(entry, '_sa_instance_state'):
            entry = Timetable(
                day=entry.day,
                time=entry.time,
                subject=entry.subject,
                slot_type=getattr(entry, 'slot_type', 'Theory'),
                division=getattr(entry, 'division', None),
                semester=getattr(entry, 'semester', None),
                branch=getattr(entry, 'department', None),
                teacher=getattr(entry, 'teacher', None),
                room=getattr(entry, 'room', None)
            )
        db.session.add(entry)
        db.session.commit()
        return entry.id
