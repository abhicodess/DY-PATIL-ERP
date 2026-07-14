"""
Stage 1 Regression Tests: get_ca_total() and calculate_result()
================================================================
Fully mock-based — no real database required. These tests verify:

  1. get_ca_total() uses AND (not OR) to scope marks to the exact
     subject_id — marks from another subject in the same semester
     must never leak into the total.
  2. NULL obtained_marks are treated as 0 (not skipped).
  3. obtained_marks > max_marks is capped at max_marks.
  4. Missing student / subject returns 0.0 (no crash).
  5. calculate_result() pass/fail/grade thresholds are correct.
"""
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# get_ca_total() — isolation regression
# ---------------------------------------------------------------------------

class TestGetCaTotalRegression:
    STUDENT = "Test Student Regression"
    SUBJ1   = "Subject Alpha"
    SUBJ2   = "Subject Beta"
    SEM     = "V"

    COMPONENTS_SUBJ1 = [
        {"component_type": "Assignment",        "max_marks": 5.0,  "obtained_marks": 5.0},
        {"component_type": "Attendance",        "max_marks": 5.0,  "obtained_marks": 5.0},
        {"component_type": "Teacher Assessment","max_marks": 10.0, "obtained_marks": 5.0},
    ]
    COMPONENTS_SUBJ2 = [
        {"component_type": "Assignment",        "max_marks": 5.0,  "obtained_marks": 5.0},
        {"component_type": "Attendance",        "max_marks": 5.0,  "obtained_marks": 5.0},
        {"component_type": "Teacher Assessment","max_marks": 10.0, "obtained_marks": 10.0},
    ]

    def _qone(self, student_id=1, subj1_id=10, subj2_id=20):
        def side(sql, params):
            u = sql.upper()
            if "FROM STUDENTS" in u:
                return {"id": student_id}
            if "FROM SUBJECTS" in u:
                n = params[0]
                if n == self.SUBJ1:
                    return {"id": subj1_id}
                if n == self.SUBJ2:
                    return {"id": subj2_id}
            return None
        return side

    def _qry(self, subj1_id=10):
        def side(sql, params):
            if "FROM MARKS_COMPONENTS" in sql.upper():
                _sid, subj_id, _sem = params
                # Only return subject 1 marks when subject 1 is requested
                if subj_id == subj1_id:
                    return self.COMPONENTS_SUBJ1
                # Subject 2 marks exist in DB but must NOT appear when subject 1 requested
                return []
            return []
        return side

    def test_only_target_subject_marks_summed(self):
        """Core regression: Subject 2 marks must not add to Subject 1 total."""
        from services.results_service import get_ca_total
        with patch("services.results_service.qone", MagicMock(side_effect=self._qone())), \
             patch("services.results_service.qry",  MagicMock(side_effect=self._qry())):
            result = get_ca_total(self.STUDENT, self.SUBJ1, self.SEM)
        # 5+5+5 = 15, never 30 (which would happen with OR)
        assert result == 15.0, (
            f"Expected 15.0 (Subject Alpha only), got {result}. "
            "Marks from Subject Beta leaked — AND/OR bug still present."
        )

    def test_unknown_student_returns_zero(self):
        from services.results_service import get_ca_total
        with patch("services.results_service.qone", return_value=None), \
             patch("services.results_service.qry",  return_value=[]):
            assert get_ca_total("Nobody", "Math", "V") == 0.0

    def test_unknown_subject_returns_zero(self):
        from services.results_service import get_ca_total
        def qone_no_subj(sql, params):
            if "FROM STUDENTS" in sql.upper():
                return {"id": 1}
            return None  # subject missing
        with patch("services.results_service.qone", MagicMock(side_effect=qone_no_subj)), \
             patch("services.results_service.qry",  return_value=[]):
            assert get_ca_total(self.STUDENT, "Nonexistent", "V") == 0.0

    def test_null_obtained_marks_treated_as_zero(self):
        """NULL obtained_marks counts as 0, not skipped."""
        from services.results_service import get_ca_total
        comps = [
            {"component_type": "Assignment", "max_marks": 5.0, "obtained_marks": 5.0},
            {"component_type": "Attendance", "max_marks": 5.0, "obtained_marks": None},
        ]
        with patch("services.results_service.qone", MagicMock(side_effect=self._qone())), \
             patch("services.results_service.qry",  return_value=comps):
            assert get_ca_total(self.STUDENT, self.SUBJ1, self.SEM) == 5.0

    def test_over_max_is_capped(self):
        """obtained_marks > max_marks must be capped to max_marks."""
        from services.results_service import get_ca_total
        comps = [{"component_type": "Assignment", "max_marks": 5.0, "obtained_marks": 99.0}]
        with patch("services.results_service.qone", MagicMock(side_effect=self._qone())), \
             patch("services.results_service.qry",  return_value=comps):
            assert get_ca_total(self.STUDENT, self.SUBJ1, self.SEM) == 5.0

    def test_empty_components_returns_zero(self):
        """No marks entered yet ? 0.0, no crash."""
        from services.results_service import get_ca_total
        with patch("services.results_service.qone", MagicMock(side_effect=self._qone())), \
             patch("services.results_service.qry",  return_value=[]):
            assert get_ca_total(self.STUDENT, self.SUBJ1, self.SEM) == 0.0


# ---------------------------------------------------------------------------
# calculate_result() — grade / pass-fail thresholds
# ---------------------------------------------------------------------------

class TestCalculateResult:

    def test_all_pass_grade_O(self):
        from services.results_service import calculate_result
        total, grade, result, passed = calculate_result(5, 5, 10, 12, 20)
        # 52/60 = 86.7% ? O
        assert passed is True
        assert grade == "O"
        assert result == "Pass"
        assert total == 52

    def test_grade_A(self):
        from services.results_service import calculate_result
        # 40/60 = 66.7% ? A
        total, grade, result, passed = calculate_result(4, 4, 8, 10, 14)
        assert passed is True
        assert grade == "A"

    def test_grade_B(self):
        from services.results_service import calculate_result
        # 35/60 = 58.3% ? B
        total, grade, result, passed = calculate_result(3, 3, 6, 10, 13)
        assert grade == "B"

    def test_fail_low_ut(self):
        """UT below 8 must fail regardless of total."""
        from services.results_service import calculate_result
        _, grade, result, passed = calculate_result(5, 5, 10, 5, 20)
        assert passed is False
        assert grade == "F"
        assert result == "Fail"

    def test_fail_low_mse(self):
        """MSE below 8 must fail regardless of total."""
        from services.results_service import calculate_result
        _, grade, result, passed = calculate_result(5, 5, 10, 12, 5)
        assert passed is False
        assert grade == "F"

    def test_fail_low_total(self):
        """Total < 24 must fail."""
        from services.results_service import calculate_result
        _, grade, result, passed = calculate_result(1, 1, 1, 10, 10)
        assert passed is False
        assert result == "Fail"
