import io
import os
import sys
import unittest
from unittest.mock import patch

from openpyxl import Workbook
from werkzeug.datastructures import FileStorage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.excel_parser import AttendanceParseError, parse_attendance_excel  # noqa: E402
import app  # noqa: E402


def build_report_file():
    wb = Workbook()
    ws = wb.active
    ws.append(["School of Engineering & Technology"])
    ws.append(["Department of Computer Engineering"])
    ws.append(["Academic Year 2025-26, Semester -II"])
    ws.append(["Final Attendance Report"])
    ws.append(["From 19.01.2026 to 10.04.2026"])
    ws.append(["Program: S. Y. B. Tech Comp. Engg. (Div. A)"])
    ws.append(["SR. NO.", "ROLL NO.", "NAME OF STUDENT", "DBMS", "SE", "Total", "% of Attendance"])
    ws.append(["", "", "", "U24CEPC401", "U24CEPC402", "", ""])
    ws.append(["", "", "", "TH", "TH", "", ""])
    ws.append(["", "", "TOTAL NO. OF LECTURES CONDUCTED", 40, 20, 60, 100])
    ws.append([1, "A01", "Alpha Student", 30, 15, 45, 75])
    ws.append([2, "A02", "Beta Student", 20, 10, 30, 50])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return FileStorage(stream=io.BytesIO(buf.getvalue()), filename="attendance_report.xlsx")


class AttendanceParserTests(unittest.TestCase):
    def test_parse_real_world_style_report(self):
        file_obj = build_report_file()
        result = parse_attendance_excel(file_obj)
        self.assertEqual(result.metadata["division"], "A")
        self.assertEqual(result.metadata["department"], "CS")
        self.assertEqual(result.metadata["semester"], "II")
        self.assertEqual(result.analytics["total_students"], 2)
        self.assertEqual(len(result.normalized_rows), 4)

    def test_reject_non_xlsx(self):
        bad = FileStorage(stream=io.BytesIO(b"hello"), filename="attendance.csv")
        with self.assertRaises(AttendanceParseError):
            parse_attendance_excel(bad)


class AttendanceRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        with self.client.session_transaction() as s:
            s["role"] = "admin"
            s["name"] = "Administrator"
            s["_csrf_token"] = "upload_csrf"

    @patch("app.process_attendance_upload")
    def test_route_redirects_to_dashboard_on_success(self, mocked_upload):
        mocked_upload.return_value = {
            "ok": True,
            "result": {"saved": 4, "skipped": 0, "students": 2, "batch_id": 77},
        }
        file_obj = build_report_file()
        response = self.client.post(
            "/import_attendance_excel",
            data={"file": file_obj, "_csrf": "upload_csrf"},
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/attendance_dashboard?saved=4", response.headers["Location"])


if __name__ == "__main__":
    unittest.main()
