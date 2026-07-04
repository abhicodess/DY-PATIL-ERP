from tasks.reports.attendance_reports import get_date_range_from_month_academic_year
from datetime import date

def test_get_date_range_from_month_academic_year():
    # Test academic year 2025-26, January (month 1)
    # January 2026 is part of the 2025-26 academic year
    start, end = get_date_range_from_month_academic_year("january", "2025-26")
    assert start == date(2026, 1, 1)
    assert end == date(2026, 1, 31)

    # Test June (month 6)
    # June 2025 is the start of the 2025-26 academic year
    start, end = get_date_range_from_month_academic_year("june", "2025-26")
    assert start == date(2025, 6, 1)
    assert end == date(2025, 6, 30)

    # Test month as number
    start, end = get_date_range_from_month_academic_year(12, "2025-26")
    assert start == date(2025, 12, 1)
    assert end == date(2025, 12, 31)

def test_generate_monthly_attendance_report(monkeypatch, tmp_path):
    from unittest.mock import MagicMock
    from tasks.reports.attendance_reports import generate_monthly_attendance_report
    import tasks.reports.attendance_reports
    
    from services.tenant_service import TenantService
    monkeypatch.setattr(TenantService, "get_by_id", lambda tenant_id: {"id": 1, "slug": "dypatil", "schema_name": "public"})
    
    # Mock qry/exe calls to prevent database calls
    monkeypatch.setattr(tasks.reports.attendance_reports, "qry", lambda sql, params: [
        {"id": 1, "roll": "CS-0001", "name": "John Doe", "division": "A", "year": "TY", "present": 10, "absent": 2, "total": 12, "percentage": 83.33}
    ])
    monkeypatch.setattr(tasks.reports.attendance_reports, "exe", lambda sql, params=None: None)
    
    # Mock generate_pdf to write a dummy file so os.path.getsize does not fail
    def mock_gen_pdf(template, context, out_path):
        with open(out_path, "w") as f:
            f.write("dummy pdf content")
    monkeypatch.setattr(tasks.reports.attendance_reports, "generate_pdf", mock_gen_pdf)
    
    # Mock task request and update_progress
    generate_monthly_attendance_report.request.id = "dummy-job-id"
    progress_calls = []
    monkeypatch.setattr(generate_monthly_attendance_report, "update_progress", lambda *args: progress_calls.append(args))
    
    filters = {
        "department": "Computer",
        "month": "january",
        "academic_year": "2025-26",
        "year": "TY",
        "division": "A"
    }
    
    out_file = tmp_path / "report.pdf"
    generate_monthly_attendance_report(filters, str(out_file), _tenant_id=1)
    
    assert len(progress_calls) >= 1

