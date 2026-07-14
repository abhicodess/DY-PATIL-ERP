import pytest
from unittest.mock import MagicMock, patch

def test_validation_rule_checks(app):
    from services.results_service import validate_result_record_rules
    
    # Mock subject info: Assignment max 5, Attendance max 5
    sub_info = {
        'components': [
            {'component_name': 'Assignment', 'max_marks': 5.0},
            {'component_name': 'Attendance', 'max_marks': 5.0}
        ],
        'max_total': 10.0
    }
    
    with patch('services.results_service.get_components_for_subject', return_value=sub_info):
        # 1. Valid record
        r_valid = {
            'subject': 'Math', 'department': 'CS', 'semester': 'I',
            'assignment_marks': 4.0, 'attendance_marks': 4.0, 'marks': 8.0,
            'is_absent': False
        }
        is_valid, errors = validate_result_record_rules(r_valid)
        assert is_valid
        assert len(errors) == 0
        
        # 2. Exceeded cap
        r_exceeded = {
            'subject': 'Math', 'department': 'CS', 'semester': 'I',
            'assignment_marks': 6.0, 'attendance_marks': 4.0, 'marks': 10.0,
            'is_absent': False
        }
        is_valid, errors = validate_result_record_rules(r_exceeded)
        assert not is_valid
        assert any('exceeds max cap' in e for e in errors)
        
        # 3. Missing component (unless absent)
        r_missing = {
            'subject': 'Math', 'department': 'CS', 'semester': 'I',
            'assignment_marks': 4.0, 'attendance_marks': None, 'marks': 4.0,
            'is_absent': False
        }
        is_valid, errors = validate_result_record_rules(r_missing)
        assert not is_valid
        assert any('Missing base component' in e for e in errors)
        
        # 4. Missing component ALLOWED if absent
        r_absent_missing = {
            'subject': 'Math', 'department': 'CS', 'semester': 'I',
            'assignment_marks': None, 'attendance_marks': None, 'marks': 0.0,
            'is_absent': True
        }
        is_valid, errors = validate_result_record_rules(r_absent_missing)
        assert is_valid
        
        # 5. Mismatched total
        r_mismatch = {
            'subject': 'Math', 'department': 'CS', 'semester': 'I',
            'assignment_marks': 4.0, 'attendance_marks': 4.0, 'marks': 10.0,
            'is_absent': False
        }
        is_valid, errors = validate_result_record_rules(r_mismatch)
        assert not is_valid
        assert any('Mismatched total' in e for e in errors)

def test_approve_validation_override(app):
    from routes.results import admin_approve_result
    
    r_exceeded = {
        'id': 1, 'subject': 'Math', 'department': 'CS', 'semester': 'I',
        'assignment_marks': 6.0, 'attendance_marks': 4.0, 'marks': 10.0,
        'is_absent': False, 'status': 'verified', 'faculty_id': 2
    }
    
    mock_exe = MagicMock()
    mock_qone = MagicMock(return_value=r_exceeded)
    
    # Without override -> redirects to confirm_override_id
    with app.test_request_context(method='POST', data={'result_id': '1', 'override': 'false'}):
        from flask import session
        session['role'] = 'admin'
        session['user_id'] = 1
        session['username'] = 'admin'
        
        with patch('routes.results._qone', mock_qone),              patch('routes.results._exe', mock_exe),              patch('routes.results.redirect') as redirect_mock:
            admin_approve_result()
            assert redirect_mock.called
            # Ensure it redirects to confirm_override_id URL
            args, kwargs = redirect_mock.call_args
            assert 'confirm_override_id=1' in args[0]
            
    # With override -> updates and approves successfully
    with app.test_request_context(method='POST', data={'result_id': '1', 'override': 'true'}):
        from flask import session
        session['role'] = 'admin'
        session['user_id'] = 1
        session['username'] = 'admin'
        
        with patch('routes.results._qone', mock_qone),              patch('routes.results._exe', mock_exe),              patch('routes.results.redirect') as redirect_mock:
            admin_approve_result()
            assert mock_exe.called
            assert redirect_mock.called
            args, kwargs = redirect_mock.call_args
            assert 'approved=1' in args[0]
