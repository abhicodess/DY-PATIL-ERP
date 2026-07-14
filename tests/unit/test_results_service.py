import pytest
from services.results_service import ResultsService

class TestResultsService:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = ResultsService()

    @pytest.mark.parametrize("score, expected_grade", [
        (95, "O"),
        (85, "O"),
        (75, "O"),
        (65, "A"),
        (55, "B"),
        (45, "C"),
        (35, "D"),
        (25, "F"),
    ])
    def test_calculate_grade(self, score, expected_grade):
        assert self.service.calculate_grade(score) == expected_grade

    def test_get_student_results_empty(self):
        results = self.service.get_student_results(999)
        assert len(results) == 0

    def test_ca_total_regression(self, session, app):
        from models.student import Student
        from models.extra_models import Subject
        from models.results import SubjectMaster, MarksComponents
        from services.results_service import get_ca_total
        
        with app.app_context():
            student = Student(name="John Doe Regression", roll="12345_reg", department="Computer", year="TY")
            session.add(student)
            session.commit()
            
            # 2. Create two subjects in the same semester
            subject1 = Subject(name="Subject One Regression", subject_code="SUB_REG_1", dept="Computer", semester="V")
            subject2 = Subject(name="Subject Two Regression", subject_code="SUB_REG_2", dept="Computer", semester="V")
            session.add(subject1)
            session.add(subject2)
            session.commit()
            
            # Create subjects_master configuration
            sm1 = SubjectMaster(subject_code="SUB_REG_1", subject_name="Subject One Regression", department="Computer", semester="V",
                                max_assignment=5, max_attendance=5, max_teaching=10, max_ut=20, max_mse=20, max_total=60)
            sm2 = SubjectMaster(subject_code="SUB_REG_2", subject_name="Subject Two Regression", department="Computer", semester="V",
                                max_assignment=5, max_attendance=5, max_teaching=10, max_ut=20, max_mse=20, max_total=60)
            session.add(sm1)
            session.add(sm2)
            session.commit()
            
            # 3. Insert component marks for both subjects for this student
            # Subject 1 component marks (should sum up to 15)
            mc1 = MarksComponents(student_id=student.id, subject_id=subject1.id, semester="V",
                                  component_type="Assignment", max_marks=5.0, obtained_marks=5.0)
            mc2 = MarksComponents(student_id=student.id, subject_id=subject1.id, semester="V",
                                  component_type="Attendance", max_marks=5.0, obtained_marks=5.0)
            mc3 = MarksComponents(student_id=student.id, subject_id=subject1.id, semester="V",
                                  component_type="Teacher Assessment", max_marks=10.0, obtained_marks=5.0)
            
            # Subject 2 component marks (should sum up to 20, but not affect Subject 1)
            mc4 = MarksComponents(student_id=student.id, subject_id=subject2.id, semester="V",
                                  component_type="Assignment", max_marks=5.0, obtained_marks=5.0)
            mc5 = MarksComponents(student_id=student.id, subject_id=subject2.id, semester="V",
                                  component_type="Attendance", max_marks=5.0, obtained_marks=5.0)
            mc6 = MarksComponents(student_id=student.id, subject_id=subject2.id, semester="V",
                                  component_type="Teacher Assessment", max_marks=10.0, obtained_marks=10.0)
            
            session.add_all([mc1, mc2, mc3, mc4, mc5, mc6])
            session.commit()
            
            # 4. Call get_ca_total and verify that only Subject 1's marks are summed
            ca_total = get_ca_total("John Doe Regression", "Subject One Regression", "V")
            
            # Expected: 5 (Assignment) + 5 (Attendance) + 5 (Teacher Assessment) = 15.0
            assert ca_total == 15.0

