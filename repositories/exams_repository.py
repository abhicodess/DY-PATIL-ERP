from repositories.base_repository import BaseRepository
from models.exams import Exam, ExamSlot

class ExamsRepository(BaseRepository):
    def __init__(self):
        super().__init__(Exam)

    def get_slots(self, exam_id):
        return ExamSlot.query.filter_by(exam_id=exam_id).all()
