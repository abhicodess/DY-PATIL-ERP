from repositories.base_repository import BaseRepository
from models.student import Student

class StudentRepository(BaseRepository):
    def __init__(self):
        super().__init__(Student)

    def get_by_prn(self, prn):
        return Student.query.filter_by(prn=prn).first()

    def get_by_roll(self, roll):
        return Student.query.filter_by(roll=roll).first()
    
    def search(self, q=None, dept=None, year=None, division=None):
        query = Student.query
        if q:
            query = query.filter(
                (Student.name.ilike(f"%{q}%")) | 
                (Student.roll.ilike(f"%{q}%")) | 
                (Student.prn.ilike(f"%{q}%"))
            )
        if dept:
            query = query.filter_by(department=dept)
        if year:
            query = query.filter_by(year=year)
        if division:
            query = query.filter_by(division=division)
        return query.order_by(Student.id.desc()).all()
