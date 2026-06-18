from repositories.base_repository import BaseRepository
from models.results import Mark, ResultSummary

class ResultsRepository(BaseRepository):
    def __init__(self):
        super().__init__(Mark)

    def get_by_student(self, student_id):
        return Mark.query.filter_by(student_id=student_id).all()

    def get_summary(self, student_id, semester):
        return ResultSummary.query.filter_by(student_id=student_id, semester=semester).first()
