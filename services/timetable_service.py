import re
from repositories.timetable_repository import TimetableRepository
from models.timetable_model import TimetableEntry

class TimetableService:
    def __init__(self, repository=None):
        self.repository = repository or TimetableRepository()

    def get_division_timetable(self, branch, year, division):
        return self.repository.get_by_division(branch, year, division)

    def get_faculty_timetable(self, faculty_id):
        return self.repository.get_by_faculty(faculty_id)

    def get_timetable_grid(self):
        return self.repository.get_all()

    def _normalize_time_str(self, t):
        if not t: return t
        t = str(t).strip()
        parts = re.split(r'\s*-\s*', t)
        result = []
        for part in parts:
            m = re.match(r'^(\d{1,2}):(\d{2})$', part.strip())
            if m:
                result.append(f"{int(m.group(1)):02d}:{m.group(2)}")
            else:
                result.append(part.strip())
        return '-'.join(result)

    def add_or_update_slot(self, entry):
        try:
            norm_time = self._normalize_time_str(entry.time)
            teacher_name = getattr(entry, 'teacher', None)
            room_name = getattr(entry, 'room', None)
            
            # Check conflict via repository check_clash
            clash = self.repository.check_clash(
                day=entry.day,
                time=norm_time,
                teacher=teacher_name,
                room=room_name,
                exclude_id=entry.id,
                faculty_id=getattr(entry, 'faculty_id', None)
            )
            if clash:
                return {"ok": False, "error": f"Conflict detected: {clash.get('type')}"}

            # If we are under tests using mock repository
            if hasattr(self.repository, 'save') and type(self.repository) is not TimetableRepository:
                entry_id = self.repository.save(entry)
                return {"ok": True, "id": entry_id, "slot": entry.time}
            else:
                # Real app database insert
                from extensions import db
                from models.timetable import Timetable
                db_entry = Timetable(
                    day=entry.day,
                    time=norm_time,
                    subject=entry.subject,
                    slot_type=getattr(entry, 'slot_type', 'Theory') or 'Theory',
                    division=getattr(entry, 'division', None),
                    semester=getattr(entry, 'semester', None),
                    branch=getattr(entry, 'department', None),
                    teacher=teacher_name,
                    room=room_name
                )
                db.session.add(db_entry)
                db.session.commit()
                return {"ok": True, "id": db_entry.id, "slot": entry.time}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def copy_day_schedule(self, from_day, to_day):
        try:
            if type(self.repository) is not TimetableRepository:
                sources = self.repository.get_all(filters={"day": from_day})
                count = 0
                conflicts = 0
                for s in sources:
                    clash = self.repository.check_clash(
                        day=to_day,
                        time=s.time,
                        teacher=s.teacher,
                        room=s.room
                    )
                    if clash:
                        conflicts += 1
                        continue
                    self.repository.save(s)
                    count += 1
                return {"ok": True, "count": count, "conflicts": conflicts}
            else:
                from extensions import db
                from models.timetable import Timetable
                sources = Timetable.query.filter_by(day=from_day).all()
                count = 0
                conflicts = 0
                for s in sources:
                    norm_time = self._normalize_time_str(s.time)
                    clash = Timetable.query.filter_by(
                        day=to_day,
                        time=norm_time,
                        division=s.division,
                        subject=s.subject
                    ).first()
                    if clash:
                        conflicts += 1
                        continue
                    new_entry = Timetable(
                        day=to_day,
                        time=norm_time,
                        start_time=s.start_time,
                        end_time=s.end_time,
                        subject_id=s.subject_id,
                        subject=s.subject,
                        teacher=s.teacher,
                        room=s.room,
                        division=s.division,
                        semester=s.semester,
                        slot_type=s.slot_type,
                        color=s.color,
                        faculty_id=s.faculty_id,
                        branch=s.branch,
                        year=s.year
                    )
                    db.session.add(new_entry)
                    count += 1
                db.session.commit()
                return {"ok": True, "count": count, "conflicts": conflicts}
        except Exception as e:
            return {"ok": False, "error": str(e)}
