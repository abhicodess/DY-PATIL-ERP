from repositories.results_repository import ResultsRepository

class ResultsService:
    def __init__(self):
        self.repository = ResultsRepository()

    def get_student_results(self, student_id):
        return self.repository.get_by_student(student_id)

    def calculate_gpa(self, student_id, semester):
        # GP calculation logic
        pass

    def calculate_grade(self, score):
        if score >= 75: return "O"
        if score >= 65: return "A"
        if score >= 55: return "B"
        if score >= 45: return "C"
        if score >= 35: return "D"
        return "F"

def calculate_result(assignment, attendance, teaching, ut, mse):
    total = assignment + attendance + teaching + ut + mse
    pct = (total / 60) * 100
    passed = (ut >= 8) and (mse >= 8) and (total >= 24)
    
    if not passed:
        grade = 'F'
        result = 'Fail'
    elif pct >= 75: grade, result = 'O', 'Pass'
    elif pct >= 65: grade, result = 'A', 'Pass'
    elif pct >= 55: grade, result = 'B', 'Pass'
    elif pct >= 45: grade, result = 'C', 'Pass'
    else:           grade, result = 'D', 'Pass'
    
    return total, grade, result, passed

