import pytest
from unittest.mock import patch, MagicMock
from services.admin_notification_service import AdminNotificationService

def test_format_message_attendance_submitted():
    service = AdminNotificationService()
    message = service._format_message(
        'attendance_submitted',
        {
            'faculty_name': 'Dr. Smith',
            'subject': 'Mathematics',
            'division': 'SE CSE-A',
            'date': '2026-06-24',
            'present_count': 45,
            'total_students': 50
        }
    )
    assert message == "Prof. Dr. Smith submitted attendance for Mathematics (SE CSE-A) on 2026-06-24: 45/50 present"

def test_format_message_unknown_event_type():
    service = AdminNotificationService()
    message = service._format_message('unknown_event', {'foo': 'bar'})
    assert message == "Event: unknown_event"

def test_notify_admin_saves_to_db():
    service = AdminNotificationService()
    with patch.object(service, '_save_to_db') as mock_save:
        service.notify_admin(
            'timetable_slot_approved',
            faculty_id=1,
            faculty_name='Dr. Smith',
            subject='Mathematics',
            day='Monday',
            time_slot='8:30-9:30'
        )
        mock_save.assert_called_once()
        args, kwargs = mock_save.call_args
        assert kwargs.get('event_type') == 'timetable_slot_approved'
        assert kwargs.get('faculty_id') == 1
        assert kwargs.get('faculty_name') == 'Dr. Smith'

def test_notify_admin_never_raises_on_db_failure():
    service = AdminNotificationService()
    with patch.object(service, '_save_to_db', side_effect=Exception("DB connection lost")):
        # Should not raise exception
        try:
            service.notify_admin(
                'timetable_slot_approved',
                faculty_id=1,
                faculty_name='Dr. Smith',
                subject='Mathematics',
                day='Monday',
                time_slot='8:30-9:30'
            )
        except Exception as e:
            pytest.fail(f"notify_admin raised an exception on DB failure: {e}")

def test_notify_admin_never_raises_on_format_failure():
    service = AdminNotificationService()
    # Missing required keys like 'subject'
    try:
        service.notify_admin(
            'timetable_slot_approved',
            faculty_id=1,
            faculty_name='Dr. Smith',
            # missing day, time_slot, subject
        )
    except Exception as e:
        pytest.fail(f"notify_admin raised an exception on format failure: {e}")
