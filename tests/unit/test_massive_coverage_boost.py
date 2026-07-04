import pytest
from unittest.mock import MagicMock, patch, mock_open
import datetime

# ────────────────────────────────────────────────────────
# utils/database_tool.py
# ────────────────────────────────────────────────────────
def test_database_tool_backup(app):
    from utils.database_tool import backup_db
    with patch("utils.database_tool.get_db") as mock_get_db, \
         patch("builtins.open", mock_open()) as mock_file:
        mock_conn = MagicMock()
        if hasattr(mock_conn, 'cur'):
            del mock_conn.cur
        mock_get_db.return_value = mock_conn
        
        mock_cur = MagicMock()
        mock_conn.conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [{"id": 1, "created_at": datetime.datetime.now(), "updated_at": None}]
        
        backup_db()
        mock_cur.execute.assert_called()
        mock_conn.close.assert_called_once()

def test_database_tool_backup_exception(app):
    from utils.database_tool import backup_db
    with patch("utils.database_tool.get_db") as mock_get_db:
        mock_conn = MagicMock()
        if hasattr(mock_conn, 'cur'):
            del mock_conn.cur
        mock_get_db.return_value = mock_conn
        mock_conn.conn.cursor.side_effect = Exception("DB Error")
        
        backup_db()  # should fail gracefully inside try-except

def test_database_tool_reset(app):
    from utils.database_tool import reset_db
    with patch("utils.database_tool.get_db") as mock_get_db, \
         patch("builtins.input", return_value="ERASE ALL"):
        mock_conn = MagicMock()
        if hasattr(mock_conn, 'cur'):
            del mock_conn.cur
        mock_get_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.conn.cursor.return_value = mock_cur
        
        reset_db()
        mock_cur.execute.assert_called()
        mock_conn.conn.commit.assert_called()
        mock_conn.close.assert_called_once()

def test_database_tool_reset_aborted(app):
    from utils.database_tool import reset_db
    with patch("builtins.input", return_value="NO"):
        reset_db()  # should return early

def test_database_tool_menu(app):
    from utils.database_tool import menu
    with patch("builtins.input", side_effect=["3"]):
        menu()


# ────────────────────────────────────────────────────────
# utils/db_schema_setup.py
# ────────────────────────────────────────────────────────
def test_db_schema_setup_run(app):
    from utils.db_schema_setup import setup_db_schemas
    with patch("utils.db_schema_setup.get_db") as mock_get_db:
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        
        setup_db_schemas()
        mock_cur.execute.assert_called()
        mock_conn.commit.assert_called()
        mock_conn.close.assert_called()


# ────────────────────────────────────────────────────────
# routes/sms_routes.py
# ────────────────────────────────────────────────────────
def test_sms_routes(client):
    with patch("routes.sms_routes.qry") as mock_qry, \
         patch("routes.sms_routes.qone") as mock_qone, \
         patch("routes.sms_routes.SMSService.send_immediate", return_value={"success": True}):
        
        # history
        mock_qry.return_value = [{"id": "uuid-123", "created_at": datetime.datetime.now(), "updated_at": None}]
        resp = client.get("/api/sms/history?limit=10")
        assert resp.status_code == 200
        
        # templates
        mock_qry.return_value = [{"id": 1, "slug": "welcome_msg", "created_at": datetime.datetime.now(), "is_active": True}]
        resp = client.get("/api/sms/templates")
        assert resp.status_code == 200
        
        # analytics
        mock_qone.return_value = {"total": 10, "delivered": 8, "failed": 1, "queued": 1}
        resp = client.get("/api/sms/analytics")
        assert resp.status_code == 200
        
        # send-test
        resp = client.post("/api/sms/send-test", json={"recipient": "1234567890"})
        assert resp.status_code == 200

def test_sms_routes_missing_recipient(client):
    resp = client.post("/api/sms/send-test", json={})
    assert resp.status_code == 400


# ────────────────────────────────────────────────────────
# routes/upload_attendance.py
# ────────────────────────────────────────────────────────
def test_upload_attendance_functions():
    from routes.upload_attendance import is_attendance_upload_allowed, process_attendance_upload, download_attendance_backup, restore_attendance_backup
    
    assert is_attendance_upload_allowed({"role": "admin"}) is True
    assert is_attendance_upload_allowed({"role": "student"}) is False
    
    with patch("routes.upload_attendance.parse_attendance_excel") as mock_parse, \
         patch("routes.upload_attendance.persist_attendance_upload") as mock_persist:
        mock_parse.return_value = MagicMock()
        mock_persist.return_value = {"batch_id": 1}
        
        res = process_attendance_upload(MagicMock(), {"role": "admin"})
        assert res["ok"] is True
        
        res = process_attendance_upload(MagicMock(), {"role": "student"})
        assert res["ok"] is False
        assert res["status"] == 403

def test_upload_attendance_download():
    from routes.upload_attendance import download_attendance_backup
    with patch("routes.upload_attendance.fetch_batch_backup", return_value=None):
        res, status = download_attendance_backup(99)
        assert status == 404
        assert res == "Backup not found"

def test_upload_attendance_restore():
    from routes.upload_attendance import restore_attendance_backup
    with patch("routes.upload_attendance.restore_attendance_upload", return_value=123):
        res = restore_attendance_backup(99)
        assert res.status_code == 302
        assert "restored=1" in res.location


# ────────────────────────────────────────────────────────
# tasks/notification_tasks.py
# ────────────────────────────────────────────────────────
def test_notification_tasks_send_custom(app):
    from tasks.notification_tasks import send_push_notification_task
    with app.app_context(), \
         patch("tasks.notification_tasks.PushNotificationService.send_to_user") as mock_send, \
         patch("services.tenant_service.TenantService.get_by_id", return_value={"id": 1, "slug": "default"}):
        send_push_notification_task(1, "Title", "Body", _tenant_id="default")
        mock_send.assert_called_once_with(1, "Title", "Body")

def test_notification_tasks_send_topic(app):
    from tasks.notification_tasks import broadcast_notification_task
    with app.app_context(), \
         patch("tasks.notification_tasks.PushNotificationService.send_to_topic") as mock_send, \
         patch("services.tenant_service.TenantService.get_by_id", return_value={"id": 1, "slug": "default"}):
        broadcast_notification_task("general", "Title", "Body", _tenant_id="default")
        mock_send.assert_called_once_with("general", "Title", "Body")


# ────────────────────────────────────────────────────────
# utils/cumulative_parser.py
# ────────────────────────────────────────────────────────
def test_cumulative_parser_parse_empty():
    from utils.cumulative_parser import parse_excel
    import io
    empty_file = io.BytesIO(b"")
    with pytest.raises(Exception):
        parse_excel(empty_file, "test.xlsx")
