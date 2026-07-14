import pytest
from unittest.mock import MagicMock, patch

def test_compute_ranks_logic(app):
    from routes.results import admin_compute_ranks
    
    # Mock data
    rows_sub1 = [
        {'id': 1, 'roll': '101', 'student_name': 'Alice', 'marks': 50.0},
        {'id': 2, 'roll': '102', 'student_name': 'Bob', 'marks': 45.0},
    ]
    rows_sub2 = [
        {'id': 3, 'roll': '101', 'student_name': 'Alice', 'marks': 40.0},
        {'id': 4, 'roll': '102', 'student_name': 'Bob', 'marks': 45.0},
    ]
    
    def qry_side(sql, params=None):
        if 'DISTINCT subject' in sql:
            return [{'subject': 'Math'}, {'subject': 'Science'}]
        if 'subject=%s' in sql:
            subj = params[1]
            if subj == 'Math':
                return rows_sub1
            return rows_sub2
        if 'SUM(marks)' in sql:
            return [
                {'roll': '101', 'student_name': 'Alice', 'total_marks': 90.0, 'subjects_count': 2},
                {'roll': '102', 'student_name': 'Bob', 'total_marks': 90.0, 'subjects_count': 2},
            ]
        return []
        
    mock_exe = MagicMock()
    mock_qone = MagicMock(return_value={'c': 2})
    
    # Run inside app test request context so session and request exist
    with app.test_request_context(method='POST', data={'semester': 'V', 'dept': 'CS'}):
        from flask import session
        session['role'] = 'admin'
        session['user_id'] = 1
        session['username'] = 'admin'
        
        with patch('routes.results._qry', MagicMock(side_effect=qry_side)),              patch('routes.results._exe', mock_exe),              patch('routes.results._qone', mock_qone),              patch('routes.results.flash') as flash_mock,              patch('routes.results.redirect') as redirect_mock:
                 
            admin_compute_ranks()
            assert flash_mock.called
            assert redirect_mock.called

def test_bulk_delete_preview_and_execute(app):
    from routes.results import admin_bulk_delete_preview, admin_bulk_delete_execute
    
    mock_exe = MagicMock()
    mock_qone = MagicMock(return_value={'c': 10})
    mock_qry = MagicMock(return_value=[{'id': 1}, {'id': 2}])
    
    with app.test_request_context(method='GET', query_string='semester=V&dept=CS'):
        from flask import session
        session['role'] = 'admin'
        session['user_id'] = 1
        session['username'] = 'admin'
        
        with patch('routes.results._qone', mock_qone),              patch('routes.results.render_template') as render_mock:
            admin_bulk_delete_preview()
            assert render_mock.called

    with app.test_request_context(method='POST', data={'semester': 'V', 'dept': 'CS', 'safety_word': 'DELETE'}):
        from flask import session
        session['role'] = 'admin'
        session['user_id'] = 1
        session['username'] = 'admin'
        
        with patch('routes.results._exe', mock_exe),              patch('routes.results._qry', mock_qry),              patch('routes.results.flash') as flash_mock,              patch('routes.results.redirect') as redirect_mock:
            admin_bulk_delete_execute()
            assert mock_exe.called
            assert flash_mock.called
            assert redirect_mock.called

def test_bulk_delete_safety_word_mismatch(app):
    from routes.results import admin_bulk_delete_execute
    mock_exe = MagicMock()
    
    with app.test_request_context(method='POST', data={'semester': 'V', 'dept': 'CS', 'safety_word': 'WRONG'}):
        from flask import session
        session['role'] = 'admin'
        session['user_id'] = 1
        session['username'] = 'admin'
        
        with patch('routes.results._exe', mock_exe),              patch('routes.results.flash') as flash_mock,              patch('routes.results.redirect') as redirect_mock:
            admin_bulk_delete_execute()
            assert not mock_exe.called
            assert flash_mock.called
            assert redirect_mock.called
