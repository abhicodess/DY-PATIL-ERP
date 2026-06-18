from repositories.base_repository import BaseRepository
from models.faculty import Faculty

class FacultyRepository(BaseRepository):
    def __init__(self):
        super().__init__(Faculty)

    def get_by_email(self, email):
        return Faculty.query.filter_by(email=email).first()

    def search(self, q=None, dept=None):
        query = Faculty.query
        if q:
            query = query.filter(
                (Faculty.name.ilike(f"%{q}%")) | 
                (Faculty.email.ilike(f"%{q}%"))
            )
        if dept:
            query = query.filter_by(department=dept)
        return query.order_by(Faculty.name).all()
