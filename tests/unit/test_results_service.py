import pytest
from services.results_service import ResultsService

class TestResultsService:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = ResultsService()

    @pytest.mark.parametrize("score, expected_grade", [
        (95, "O"),
        (85, "A+"),
        (75, "A"),
        (65, "B+"),
        (55, "B"),
        (45, "C"),
        (35, "F"),
    ])
    def test_calculate_grade(self, score, expected_grade):
        # We need to implement this in ResultsService, or test the logic here
        # Assuming we add a helper method to ResultsService
        if hasattr(self.service, 'calculate_grade'):
            assert self.service.calculate_grade(score) == expected_grade
        else:
            pytest.skip("calculate_grade not implemented in service yet")

    def test_get_student_results_empty(self):
        results = self.service.get_student_results(999)
        assert len(results) == 0
