from repositories.results_repository import ResultsRepository

class ResultsService:
    def __init__(self):
        self.repository = ResultsRepository()

    def get_student_results(self, student_id):
        return self.repository.get_by_student(student_id)

    def calculate_gpa(self, student_id, semester):
        # GP calculation logic
        pass
