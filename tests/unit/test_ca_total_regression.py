import pytest
from unittest.mock import MagicMock, patch

class TestGetCaTotalRegression:
    STUDENT = 'Test Student Regression'
    SUBJ1   = 'Subject Alpha'
    SUBJ2   = 'Subject Beta'
    SEM     = 'V'

    COMPONENTS_SUBJ1 = [
        {'component_type': 'Assignment',         'max_marks': 5.0,  'obtained_marks': 5.0},
        {'component_type': 'Attendance',         'max_marks': 5.0,  'obtained_marks': 5.0},
        {'component_type': 'Teacher Assessment', 'max_marks': 10.0, 'obtained_marks': 5.0},
    ]
    COMPONENTS_SUBJ2 = [
        {'component_type': 'Assignment',         'max_marks': 5.0,  'obtained_marks': 5.0},
        {'component_type': 'Attendance',         'max_marks': 5.0,  'obtained_marks': 5.0},
        {'component_type': 'Teacher Assessment', 'max_marks': 10.0, 'obtained_marks': 10.0},
    ]

    def _qone(self, student_id=1, subj1_id=10, subj2_id=20):
        def side(sql, params):
            u = sql.upper()
            if 'FROM STUDENTS' in u:
                return {'id': student_id}
            if 'FROM SUBJECTS' in u:
                n = params[0]
                if n == self.SUBJ1:
                    return {'id': subj1_id}
                if n == self.SUBJ2:
                    return {'id': subj2_id}
            return None
        return side

    def _qry_subj1_only(self, subj1_id=10):
        def side(sql, params):
            if 'FROM MARKS_COMPONENTS' in sql.upper():
                _sid, subj_id, _sem = params
                if subj_id == subj1_id:
                    return self.COMPONENTS_SUBJ1
                return []
            return []
        return side

    def test_only_target_subject_marks_summed(self):
        from services.results_service import get_ca_total
        with patch('utils.pg_wrapper.qone', MagicMock(side_effect=self._qone())),              patch('utils.pg_wrapper.qry',  MagicMock(side_effect=self._qry_subj1_only())):
            result = get_ca_total(self.STUDENT, self.SUBJ1, self.SEM)
        assert result == 15.0

    def test_unknown_student_returns_zero(self):
        from services.results_service import get_ca_total
        with patch('utils.pg_wrapper.qone', return_value=None),              patch('utils.pg_wrapper.qry',  return_value=[]):
            assert get_ca_total('Nobody', 'Math', 'V') == 0.0

    def test_unknown_subject_returns_zero(self):
        from services.results_service import get_ca_total
        def qone_no_subj(sql, params):
            if 'FROM STUDENTS' in sql.upper():
                return {'id': 1}
            return None
        with patch('utils.pg_wrapper.qone', MagicMock(side_effect=qone_no_subj)),              patch('utils.pg_wrapper.qry',  return_value=[]):
            assert get_ca_total(self.STUDENT, 'Nonexistent', 'V') == 0.0

    def test_null_obtained_marks_treated_as_zero(self):
        from services.results_service import get_ca_total
        comps = [
            {'component_type': 'Assignment', 'max_marks': 5.0, 'obtained_marks': 5.0},
            {'component_type': 'Attendance', 'max_marks': 5.0, 'obtained_marks': None},
        ]
        with patch('utils.pg_wrapper.qone', MagicMock(side_effect=self._qone())),              patch('utils.pg_wrapper.qry',  return_value=comps):
            assert get_ca_total(self.STUDENT, self.SUBJ1, self.SEM) == 5.0

    def test_over_max_is_capped(self):
        from services.results_service import get_ca_total
        comps = [{'component_type': 'Assignment', 'max_marks': 5.0, 'obtained_marks': 99.0}]
        with patch('utils.pg_wrapper.qone', MagicMock(side_effect=self._qone())),              patch('utils.pg_wrapper.qry',  return_value=comps):
            assert get_ca_total(self.STUDENT, self.SUBJ1, self.SEM) == 5.0

    def test_empty_components_returns_zero(self):
        from services.results_service import get_ca_total
        with patch('utils.pg_wrapper.qone', MagicMock(side_effect=self._qone())),              patch('utils.pg_wrapper.qry',  return_value=[]):
            assert get_ca_total(self.STUDENT, self.SUBJ1, self.SEM) == 0.0

class TestCalculateResult:
    def test_all_pass_grade_O(self):
        from services.results_service import calculate_result
        total, grade, result, passed = calculate_result(5, 5, 10, 12, 20)
        assert passed is True
        assert grade == 'O'
        assert result == 'Pass'
        assert total == 52

    def test_grade_A(self):
        from services.results_service import calculate_result
        total, grade, result, passed = calculate_result(4, 4, 8, 10, 14)
        assert passed is True
        assert grade == 'A'

    def test_grade_B_plus(self):
        from services.results_service import calculate_result
        total, grade, result, passed = calculate_result(3, 3, 6, 10, 13)
        assert grade == 'B+'

    def test_fail_low_total_score(self):
        from services.results_service import calculate_result
        # Total = 10 (16.7% < 40%) -> Fail
        total, grade, result, passed = calculate_result(1, 1, 2, 3, 3)
        assert passed is False
        assert grade == 'F'
        assert result == 'Fail'

    def test_absent_flow(self):
        from services.results_service import calculate_result
        total, grade, result, passed = calculate_result(is_absent=True)
        assert passed is False
        assert grade == 'AB'
        assert result == 'Absent'
        assert total is None
