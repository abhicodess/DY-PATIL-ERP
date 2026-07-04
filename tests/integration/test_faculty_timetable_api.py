import pytest
from utils.pg_wrapper import qone, exe, qry

@pytest.fixture
def logged_in_faculty(client):
    with client.session_transaction() as sess:
        sess['faculty_id'] = 999
        sess['name'] = 'Prof. Test Faculty'
        sess['role'] = 'faculty'
    return 999

@pytest.fixture
def logged_in_admin(client):
    with client.session_transaction() as sess:
        sess['role'] = 'admin'
        sess['name'] = 'Admin User'
    return 'admin'

def test_add_slot_returns_201_and_draft_status(client, logged_in_faculty):
    """New slots must start as 'draft', not 'pending'. Faculty submits separately."""
    payload = {
        "day": "Monday",
        "time_slot": "8:30-9:30",
        "subject": "Cloud Computing",
        "division": "SE CSE-A",
        "room": "Lab 5",
        "slot_type": "Theory",
        "semester": "Sem 4"
    }
    resp = client.post('/api/faculty/my-timetable', json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['id'] is not None
    assert data['status'] == 'draft'  # New slots start as draft
    assert data['subject'] == "Cloud Computing"

def test_add_slot_does_not_create_notification_before_submit(client, logged_in_faculty):
    """Adding a slot (draft) must NOT notify admin. Only submit triggers notification."""
    # Clear any existing notifications
    exe("DELETE FROM admin_notifications WHERE event_type = 'timetable_submitted'")

    payload = {
        "day": "Tuesday",
        "time_slot": "9:30-10:30",
        "subject": "DevOps",
        "division": "SE CSE-B",
        "room": "Room 201",
        "slot_type": "Lab",
        "semester": "Sem 4"
    }
    resp = client.post('/api/faculty/my-timetable', json=payload)
    assert resp.status_code == 201
    assert resp.get_json()['status'] == 'draft'

    # No notification should have been sent yet
    notif = qone("SELECT * FROM admin_notifications WHERE event_type = 'timetable_submitted' ORDER BY id DESC LIMIT 1")
    assert notif is None, "Admin must NOT be notified on draft creation, only on submit"

def test_submit_transitions_drafts_to_pending_and_notifies_admin(client, logged_in_faculty):
    """POST /submit must flip draft/rejected slots to 'pending' and send admin notification."""
    exe("DELETE FROM admin_notifications WHERE event_type = 'timetable_submitted'")

    # Create two draft slots
    for day, ts in [("Monday", "7:30-8:30"), ("Tuesday", "7:30-8:30")]:
        client.post('/api/faculty/my-timetable', json={
            "day": day, "time_slot": ts, "subject": "OS",
            "division": "SE CSE-A", "slot_type": "Theory"
        })

    # Submit for approval
    resp = client.post('/api/faculty/my-timetable/submit')
    assert resp.status_code == 200
    data = resp.get_json()
    assert "submitted" in data['message'].lower()

    # All slots for this faculty should now be 'pending'
    from utils.pg_wrapper import qry
    pending_slots = qry(
        "SELECT status FROM faculty_timetable WHERE faculty_id = %s AND status = 'pending'",
        (999,)
    )
    assert len(pending_slots) >= 2

    # Admin notification should have been created
    notif = qone("SELECT * FROM admin_notifications WHERE event_type = 'timetable_submitted' ORDER BY id DESC LIMIT 1")
    assert notif is not None

def test_submit_with_no_drafts_returns_400(client, logged_in_faculty):
    """Submitting when there are no draft/rejected slots must return 400."""
    exe("UPDATE faculty_timetable SET status = 'pending' WHERE faculty_id = 999 AND status IN ('draft','rejected')")
    resp = client.post('/api/faculty/my-timetable/submit')
    assert resp.status_code == 400
    assert "No draft" in resp.get_json()['error']

def test_duplicate_slot_same_day_time_returns_409(client, logged_in_faculty):
    payload = {
        "day": "Wednesday",
        "time_slot": "10:30-11:30",
        "subject": "Web Tech",
        "division": "SE CSE-A",
        "slot_type": "Theory"
    }
    resp1 = client.post('/api/faculty/my-timetable', json=payload)
    assert resp1.status_code == 201

    resp2 = client.post('/api/faculty/my-timetable', json=payload)
    assert resp2.status_code == 409
    assert "already have a slot" in resp2.get_json()['error']

def test_invalid_day_returns_400(client, logged_in_faculty):
    payload = {
        "day": "InvalidDay",
        "time_slot": "10:30-11:30",
        "subject": "Web Tech",
        "division": "SE CSE-A",
        "slot_type": "Theory"
    }
    resp = client.post('/api/faculty/my-timetable', json=payload)
    assert resp.status_code == 400
    assert "day" in resp.get_json()['errors']

def test_edit_pending_slot_allowed(client, logged_in_faculty):
    payload = {
        "day": "Thursday",
        "time_slot": "11:30-12:30",
        "subject": "Machine Learning",
        "division": "SE AIDS",
        "slot_type": "Theory"
    }
    resp = client.post('/api/faculty/my-timetable', json=payload)
    slot_id = resp.get_json()['id']

    updated = {
        "day": "Thursday",
        "time_slot": "11:30-12:30",
        "subject": "Deep Learning",
        "division": "SE AIDS",
        "slot_type": "Theory"
    }
    resp_put = client.put(f'/api/faculty/my-timetable/{slot_id}', json=updated)
    assert resp_put.status_code == 200
    assert resp_put.get_json()['subject'] == "Deep Learning"

def test_edit_approved_slot_returns_403(client, logged_in_faculty):
    # Set status to approved directly in DB
    row = qone("""
        INSERT INTO faculty_timetable (faculty_id, faculty_name, day, time_slot, subject, division, slot_type, status)
        VALUES (999, 'Prof. Test Faculty', 'Friday', '1:30-2:30', 'Maths', 'SE CSE-A', 'Theory', 'approved')
        RETURNING id
    """)
    slot_id = row[0]

    updated = {
        "day": "Friday",
        "time_slot": "1:30-2:30",
        "subject": "Advanced Maths",
        "division": "SE CSE-A",
        "slot_type": "Theory"
    }
    resp_put = client.put(f'/api/faculty/my-timetable/{slot_id}', json=updated)
    assert resp_put.status_code == 403
    assert "Only draft or rejected slots can be edited" in resp_put.get_json()['error']

def test_delete_pending_slot_returns_403(client, logged_in_faculty):
    """Pending slots are under admin review — faculty must NOT be able to delete them."""
    row = qone("""
        INSERT INTO faculty_timetable (faculty_id, faculty_name, day, time_slot, subject, division, slot_type, status)
        VALUES (999, 'Prof. Test Faculty', 'Saturday', '2:30-3:30', 'Physics', 'SE CSE-A', 'Theory', 'pending')
        RETURNING id
    """)
    slot_id = row[0]

    resp_del = client.delete(f'/api/faculty/my-timetable/{slot_id}')
    assert resp_del.status_code == 403  # Cannot delete a slot that is under review

def test_delete_approved_slot_returns_403(client, logged_in_faculty):
    row = qone("""
        INSERT INTO faculty_timetable (faculty_id, faculty_name, day, time_slot, subject, division, slot_type, status)
        VALUES (999, 'Prof. Test Faculty', 'Saturday', '3:30-4:30', 'Physics', 'SE CSE-A', 'Theory', 'approved')
        RETURNING id
    """)
    slot_id = row[0]

    resp_del = client.delete(f'/api/faculty/my-timetable/{slot_id}')
    assert resp_del.status_code == 403

def test_different_faculty_cannot_delete_others_slot(client):
    # Insert for faculty 999
    row = qone("""
        INSERT INTO faculty_timetable (faculty_id, faculty_name, day, time_slot, subject, division, slot_type, status)
        VALUES (999, 'Prof. Test Faculty', 'Monday', '4:30-5:30', 'English', 'SE CSE-A', 'Theory', 'pending')
        RETURNING id
    """)
    slot_id = row[0]

    # Log in as faculty 888
    with client.session_transaction() as sess:
        sess['faculty_id'] = 888
        sess['name'] = 'Other Faculty'
        sess['role'] = 'faculty'

    resp_del = client.delete(f'/api/faculty/my-timetable/{slot_id}')
    assert resp_del.status_code == 403

def test_admin_approve_copies_to_master_timetable(client, logged_in_faculty, logged_in_admin):
    row = qone("""
        INSERT INTO faculty_timetable (faculty_id, faculty_name, day, time_slot, subject, division, slot_type, status)
        VALUES (999, 'Prof. Test Faculty', 'Monday', '8:30-9:30', 'Chemistry', 'SE CSE-A', 'Theory', 'pending')
        RETURNING id
    """)
    slot_id = row[0]

    resp = client.patch(f'/api/admin/timetable-requests/{slot_id}/approve')
    assert resp.status_code == 200

    # Verify status in faculty_timetable is approved
    slot_db = qone("SELECT status FROM faculty_timetable WHERE id = %s", (slot_id,))
    assert slot_db[0] == 'approved'

    # Verify added to timetable (master)
    master = qone("SELECT * FROM timetable WHERE subject = %s AND division = %s AND teacher = %s", ('Chemistry', 'SE CSE-A', 'Prof. Test Faculty'))
    assert master is not None
    assert master['day'] == 'Monday'
    assert master['time'] == '8:30-9:30'

def test_admin_approve_sets_status_approved(client, logged_in_admin):
    row = qone("""
        INSERT INTO faculty_timetable (faculty_id, faculty_name, day, time_slot, subject, division, slot_type, status)
        VALUES (999, 'Prof. Test Faculty', 'Tuesday', '8:30-9:30', 'Biology', 'SE CSE-A', 'Theory', 'pending')
        RETURNING id
    """)
    slot_id = row[0]

    resp = client.patch(f'/api/admin/timetable-requests/{slot_id}/approve')
    assert resp.status_code == 200
    
    # Try approving again → should fail
    resp_again = client.patch(f'/api/admin/timetable-requests/{slot_id}/approve')
    assert resp_again.status_code == 400

def test_admin_reject_requires_note(client, logged_in_admin):
    row = qone("""
        INSERT INTO faculty_timetable (faculty_id, faculty_name, day, time_slot, subject, division, slot_type, status)
        VALUES (999, 'Prof. Test Faculty', 'Wednesday', '8:30-9:30', 'Art', 'SE CSE-A', 'Theory', 'pending')
        RETURNING id
    """)
    slot_id = row[0]

    # Empty note
    resp = client.patch(f'/api/admin/timetable-requests/{slot_id}/reject', json={"note": ""})
    assert resp.status_code == 400

def test_admin_reject_sets_note_on_slot(client, logged_in_admin):
    row = qone("""
        INSERT INTO faculty_timetable (faculty_id, faculty_name, day, time_slot, subject, division, slot_type, status)
        VALUES (999, 'Prof. Test Faculty', 'Thursday', '8:30-9:30', 'History', 'SE CSE-A', 'Theory', 'pending')
        RETURNING id
    """)
    slot_id = row[0]

    resp = client.patch(f'/api/admin/timetable-requests/{slot_id}/reject', json={"note": "Room clash"})
    assert resp.status_code == 200

    slot_db = qone("SELECT status, admin_note FROM faculty_timetable WHERE id = %s", (slot_id,))
    assert slot_db['status'] == 'rejected'
    assert slot_db['admin_note'] == 'Room clash'

def test_notifications_returned_newest_first(client, logged_in_admin):
    from datetime import datetime, timedelta
    exe("DELETE FROM admin_notifications")
    exe("""
        INSERT INTO admin_notifications (event_type, message, created_at)
        VALUES ('test_event', 'First message', %s)
    """, (datetime.utcnow() - timedelta(hours=1),))
    exe("""
        INSERT INTO admin_notifications (event_type, message, created_at)
        VALUES ('test_event', 'Second message', %s)
    """, (datetime.utcnow(),))

    resp = client.get('/api/admin/notifications')
    assert resp.status_code == 200
    notifs = resp.get_json()['notifications']
    assert len(notifs) >= 2
    assert notifs[0]['message'] == 'Second message'
    assert notifs[1]['message'] == 'First message'

def test_unread_filter_works(client, logged_in_admin):
    exe("DELETE FROM admin_notifications")
    exe("""
        INSERT INTO admin_notifications (event_type, message, is_read)
        VALUES ('test_event', 'Read message', TRUE)
    """)
    exe("""
        INSERT INTO admin_notifications (event_type, message, is_read)
        VALUES ('test_event', 'Unread message', FALSE)
    """)

    resp = client.get('/api/admin/notifications?unread=true')
    assert resp.status_code == 200
    notifs = resp.get_json()['notifications']
    assert len(notifs) == 1
    assert notifs[0]['message'] == 'Unread message'

def test_resubmit_increments_resubmission_count(client, logged_in_faculty):
    exe("DELETE FROM faculty_timetable")
    exe("DELETE FROM admin_notifications")
    
    payload = {
        "day": "Monday",
        "time_slot": "9:30-10:30",
        "subject": "Resubmit Test Sub",
        "division": "SE CSE-A",
        "slot_type": "Theory"
    }
    resp = client.post('/api/faculty/my-timetable', json=payload)
    assert resp.status_code == 201
    slot_id = resp.get_json()['id']

    resp = client.post('/api/faculty/my-timetable/submit')
    assert resp.status_code == 200

    # Login as admin explicitly
    with client.session_transaction() as sess:
        sess['role'] = 'admin'
        sess['name'] = 'Admin User'

    resp = client.patch(f'/api/admin/timetable-requests/{slot_id}/reject', json={"note": "clash with DB lab"})
    assert resp.status_code == 200

    # Log back in as faculty
    with client.session_transaction() as sess:
        sess['faculty_id'] = 999
        sess['name'] = 'Prof. Test Faculty'
        sess['role'] = 'faculty'

    updated = {
        "day": "Monday",
        "time_slot": "10:30-11:30",
        "subject": "Resubmit Test Sub",
        "division": "SE CSE-A",
        "slot_type": "Theory"
    }
    resp = client.put(f'/api/faculty/my-timetable/{slot_id}', json=updated)
    assert resp.status_code == 200
    
    slot_db = qone("SELECT last_rejected_note, status FROM faculty_timetable WHERE id = %s", (slot_id,))
    assert slot_db['last_rejected_note'] == "clash with DB lab"
    assert slot_db['status'] == 'draft'

    resp = client.post('/api/faculty/my-timetable/submit')
    assert resp.status_code == 200
    
    slot_db2 = qone("SELECT resubmission_count, status FROM faculty_timetable WHERE id = %s", (slot_id,))
    assert slot_db2['resubmission_count'] == 1
    assert slot_db2['status'] == 'pending'

def test_resubmit_sends_resubmitted_notification_not_submitted(client, logged_in_faculty):
    exe("DELETE FROM faculty_timetable")
    exe("DELETE FROM admin_notifications")
    
    payload = {
        "day": "Tuesday",
        "time_slot": "9:30-10:30",
        "subject": "Notify Test Sub",
        "division": "SE CSE-A",
        "slot_type": "Theory"
    }
    resp = client.post('/api/faculty/my-timetable', json=payload)
    assert resp.status_code == 201, f"Expected 201 but got {resp.status_code}: {resp.get_data(as_text=True)}"
    slot_id = resp.get_json()['id']

    client.post('/api/faculty/my-timetable/submit')
    exe("DELETE FROM admin_notifications")

    # Login as admin explicitly
    with client.session_transaction() as sess:
        sess['role'] = 'admin'
        sess['name'] = 'Admin User'

    resp_rej = client.patch(f'/api/admin/timetable-requests/{slot_id}/reject', json={"note": "clash with DB lab"})
    assert resp_rej.status_code == 200

    # Log back in as faculty
    with client.session_transaction() as sess:
        sess['faculty_id'] = 999
        sess['name'] = 'Prof. Test Faculty'
        sess['role'] = 'faculty'

    updated = {
        "day": "Tuesday",
        "time_slot": "10:30-11:30",
        "subject": "Notify Test Sub",
        "division": "SE CSE-A",
        "slot_type": "Theory"
    }
    client.put(f'/api/faculty/my-timetable/{slot_id}', json=updated)

    client.post('/api/faculty/my-timetable/submit')

    notifs = qry("SELECT event_type FROM admin_notifications ORDER BY id DESC")
    event_types = [n[0] for n in notifs]
    assert 'timetable_resubmitted' in event_types
    assert 'timetable_submitted' not in event_types

def test_fresh_submit_sends_submitted_not_resubmitted(client, logged_in_faculty):
    exe("DELETE FROM admin_notifications")
    
    payload = {
        "day": "Wednesday",
        "time_slot": "9:30-10:30",
        "subject": "Fresh Sub",
        "division": "SE CSE-A",
        "slot_type": "Theory"
    }
    resp = client.post('/api/faculty/my-timetable', json=payload)
    assert resp.status_code == 201

    resp = client.post('/api/faculty/my-timetable/submit')
    assert resp.status_code == 200

    notifs = qry("SELECT event_type FROM admin_notifications ORDER BY id DESC")
    event_types = [n[0] for n in notifs]
    assert 'timetable_submitted' in event_types
    assert 'timetable_resubmitted' not in event_types


# ── ADMIN OVERRIDE TESTS ─────────────────────────────────────────

def test_admin_override_slot(client, logged_in_admin):
    # Insert a slot directly in DB with pending status
    row = qone("""
        INSERT INTO faculty_timetable (faculty_id, faculty_name, day, time_slot, subject, division, slot_type, status)
        VALUES (999, 'Prof. Test Faculty', 'Friday', '1:30-2:30', 'Maths', 'SE CSE-A', 'Theory', 'pending')
        RETURNING id
    """)
    slot_id = row[0]

    updated = {
        "day": "Friday",
        "time_slot": "1:30-2:30",
        "subject": "Advanced Maths",
        "division": "SE CSE-A",
        "slot_type": "Theory",
        "room": "Room 303",
        "semester": "Sem 5",
        "status": "approved"
    }

    resp = client.put(f'/api/admin/timetable-slots/{slot_id}', json=updated)
    assert resp.status_code == 200
    
    # Check database updates
    slot = qone("SELECT * FROM faculty_timetable WHERE id = %s", (slot_id,))
    assert slot['subject'] == "Advanced Maths"
    assert slot['room'] == "Room 303"
    assert slot['status'] == "approved"

    # Since status was updated to approved, verify it was synced into master timetable
    master = qone("SELECT * FROM timetable WHERE day='Friday' AND time='1:30-2:30' AND teacher='Prof. Test Faculty'")
    assert master is not None
    assert master['subject'] == "Advanced Maths"
    assert master['room'] == "Room 303"


def test_get_admin_timetable_slots(client, logged_in_admin):
    # Insert multiple slots
    exe("DELETE FROM faculty_timetable")
    exe("""
        INSERT INTO faculty_timetable (faculty_id, faculty_name, day, time_slot, subject, division, slot_type, status)
        VALUES 
        (999, 'Prof. Test Faculty', 'Monday', '8:30-9:30', 'Maths', 'SE CSE-A', 'Theory', 'approved'),
        (999, 'Prof. Test Faculty', 'Tuesday', '9:30-10:30', 'Physics', 'SE CSE-B', 'Theory', 'pending')
    """)

    resp_all = client.get('/api/admin/timetable-slots')
    assert resp_all.status_code == 200
    assert isinstance(resp_all.get_json(), list)
    assert len(resp_all.get_json()) == 2

    resp_approved = client.get('/api/admin/timetable-slots?status=approved')
    assert resp_approved.status_code == 200
    assert len(resp_approved.get_json()) == 1
    assert resp_approved.get_json()[0]['subject'] == 'Maths'
