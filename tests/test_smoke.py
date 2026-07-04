"""Quick smoke tests: admin dashboard and cumulative marks (requires college.db)."""
import os
import sys
import unittest

# Project root on path when run as `python -m unittest tests.test_smoke` from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app  # noqa: E402


class AdminCumulativeSmoke(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        with self.client.session_transaction() as s:
            s["role"] = "admin"
            s["name"] = "Administrator"
            s["_csrf_token"] = "smoke_test_csrf_token"

    def test_admin_ok(self):
        r = self.client.get("/admin", follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b"Traceback", r.data)
        self.assertNotIn(b"Internal Server Error", r.data)

    def test_cumulative_marks_ok(self):
        r = self.client.get("/cumulative_marks")
        self.assertEqual(r.status_code, 200)
        r2 = self.client.get("/cumulative_marks?dept=CS")
        self.assertEqual(r2.status_code, 200)

    def test_export_cumulative_xlsx(self):
        r = self.client.get("/export_cumulative_excel")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.mimetype,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertTrue(r.data.startswith(b"PK"))

    def test_post_without_csrf_returns_400(self):
        with self.client.session_transaction() as s:
            s["role"] = "admin"
            s["name"] = "Administrator"
            if "_csrf_token" in s:
                del s["_csrf_token"]
        r = self.client.post("/delete_student", data={"student_id": "999999999"})
        self.assertEqual(r.status_code, 400)

    def test_post_with_csrf_succeeds_for_delete_student(self):
        r = self.client.post(
            "/delete_student",
            data={"student_id": "999999999", "_csrf": "smoke_test_csrf_token"},
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 302)

    def test_clear_all_pdf_summary_wrong_phrase_redirects(self):
        r = self.client.post(
            "/clear_all_attendance_summary",
            data={
                "_csrf": "smoke_test_csrf_token",
                "confirm_phrase": "wrong phrase",
            },
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn("bad_summary_confirm", r.headers.get("Location", ""))

    def test_attendance_dashboard_renders(self):
        r = self.client.get("/attendance_dashboard")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b"Traceback", r.data)

    def test_view_attendance_renders(self):
        r = self.client.get("/view_attendance")
        self.assertEqual(r.status_code, 200)

    def test_cumulative_import_has_csrf_meta(self):
        r = self.client.get("/cumulative_import")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'csrf-token', r.data)

    def test_cumulative_commit_requires_csrf_header(self):
        r = self.client.post("/cumulative_commit", json={"rows": []})
        self.assertEqual(r.status_code, 400)
        r2 = self.client.post(
            "/cumulative_commit",
            json={"rows": []},
            headers={"X-CSRF-Token": "smoke_test_csrf_token"},
        )
        self.assertEqual(r2.status_code, 200)
        body = r2.get_json()
        self.assertIsNotNone(body)
        self.assertIn("inserted", body)

    def test_cumulative_report_renders(self):
        r = self.client.get("/cumulative_report")
        self.assertEqual(r.status_code, 200)

    def test_analytics_renders(self):
        r = self.client.get("/analytics")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b"Traceback", r.data)
        self.assertNotIn(b"Internal Server Error", r.data)

    def test_api_attendance_trend(self):
        r = self.client.get("/api/admin/attendance_trend?view=daily")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("labels", data)
        self.assertIn("data", data)

    def test_api_attendance_calendar(self):
        r = self.client.get("/api/admin/attendance_calendar?year=2026&month=6")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("data", data)

    def test_api_attendance_date_details(self):
        r = self.client.get("/api/admin/attendance_date_details?date=2026-06-25")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["status"], "success")


if __name__ == "__main__":
    unittest.main()
