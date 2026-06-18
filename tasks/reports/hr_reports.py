import os
import calendar
import tempfile
import logging
from datetime import datetime, date, timedelta

from celery_app import celery
from tasks.reports.base_report_task import BaseReportTask
from utils.pg_wrapper import qry, qone, exe
from utils.pdf_generator import generate_pdf, merge_pdfs
from utils.excel_generator import ExcelReport

logger = logging.getLogger("reports_engine")

@celery.task(base=BaseReportTask, bind=True, name="tasks.reports.hr_reports.generate_faculty_attendance_report")
def generate_faculty_attendance_report(self, filters, output_path):
    job_id = self.request.id
    self.update_progress(job_id, 15, "Setting up date range filters...")
    
    dept = filters.get("department")
    month_val = filters.get("month") # e.g. 5 or "May"
    acad_yr = filters.get("academic_year")
    
    # Map month/year
    months_map = {
        'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
        'april': 4, 'apr': 4, 'may': 5, 'spd': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
        'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12
    }
    
    if isinstance(month_val, str):
        month_lower = month_val.strip().lower()
        month = months_map.get(month_lower, datetime.now().month)
    else:
        month = int(month_val)
        
    year = datetime.now().year # fallback to current year
    # Extract start year from academic year e.g. 2025-26
    if acad_yr:
        parts = acad_yr.split('-')
        start_year = int(parts[0])
        year = start_year + 1 if month <= 5 else start_year
        
    month_start = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    month_end = date(year, month, last_day)
    
    # Calculate total working days in the month (Mon-Sat, excluding Sundays)
    working_days = 0
    for day in range(1, last_day + 1):
        d = date(year, month, day)
        if d.weekday() != 6:  # 6 is Sunday
            working_days += 1
            
    self.update_progress(job_id, 40, "Retrieving faculty records and schedules...")
    
    # Query all active faculty
    fac_sql = "SELECT id, employee_id, name, designation, dept as department FROM faculty WHERE is_active = TRUE"
    fac_params = []
    if dept:
        fac_sql += " AND dept = %s"
        fac_params.append(dept)
    fac_sql += " ORDER BY name"
    
    faculty_members = qry(fac_sql, tuple(fac_params))
    
    # Check if faculty_attendance_v2 table exists
    table_check = qone(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'faculty_attendance_v2'
        ) as exists_v2
        """
    )
    has_v2 = table_check["exists_v2"] if table_check else False
    
    processed_records = []
    leave_ledger = []
    
    for f in faculty_members:
        fid = f["id"]
        
        # 1. Calculate leaves approved
        leaves = qry(
            """
            SELECT leave_type, from_date, to_date, status, reason
            FROM leave_applications
            WHERE faculty_id = %s AND status = 'approved'
              AND ((from_date BETWEEN %s AND %s) OR (to_date BETWEEN %s AND %s))
            """,
            (fid, month_start, month_end, month_start, month_end)
        )
        
        leave_days_count = 0
        for l in leaves:
            overlap_start = max(l["from_date"], month_start)
            overlap_end = min(l["to_date"], month_end)
            if overlap_start <= overlap_end:
                days = (overlap_end - overlap_start).days + 1
                leave_days_count += days
                
            leave_ledger.append({
                "faculty_name": f["name"],
                "from_date": l["from_date"].strftime("%d-%b-%Y") if isinstance(l["from_date"], date) else str(l["from_date"]),
                "to_date": l["to_date"].strftime("%d-%b-%Y") if isinstance(l["to_date"], date) else str(l["to_date"]),
                "days": (l["to_date"] - l["from_date"]).days + 1,
                "type": l["leave_type"],
                "status": l["status"]
            })
            
        # 2. Get Present Days
        if has_v2:
            # Query v2 table
            pres = qone(
                """
                SELECT COUNT(*) as count 
                FROM faculty_attendance_v2 
                WHERE faculty_id = %s AND status = 'Present' AND attendance_date BETWEEN %s AND %s
                """,
                (fid, month_start, month_end)
            )
            present_days = pres["count"] if pres else 0
        else:
            # Fallback: derive from attendance sessions marked by faculty
            sessions_count = qone(
                """
                SELECT COUNT(DISTINCT lecture_date) as count
                FROM attendance_sessions
                WHERE faculty_id = %s AND lecture_date BETWEEN %s AND %s
                """,
                (fid, month_start, month_end)
            )
            present_days = sessions_count["count"] if sessions_count else 0
            
        # Present days cannot exceed working days minus leaves
        present_days = min(present_days, working_days - leave_days_count)
        absent_days = max(0, working_days - present_days - leave_days_count)
        
        # Calculate attendance percentage
        # excused leaves are counted towards attendance (or deducted from denominator)
        denom = working_days - leave_days_count
        attendance_pct = (present_days * 100.0 / denom) if denom > 0 else 100.0
        
        processed_records.append({
            "employee_id": f["employee_id"],
            "name": f["name"],
            "designation": f["designation"] or "Faculty",
            "working_days": working_days,
            "present": present_days,
            "absent": absent_days,
            "leaves": leave_days_count,
            "percentage": attendance_pct
        })
        
    format_type = output_path.split(".")[-1].lower()
    month_name = calendar.month_name[month]
    
    if format_type == "pdf":
        self.update_progress(job_id, 75, "Rendering Faculty Attendance PDF template...")
        context = {
            "job_id": job_id,
            "generated_at": datetime.now().strftime("%d-%b-%Y %I:%M %p"),
            "department": dept or "All",
            "month": f"{month_name} {year}",
            "academic_year": acad_yr,
            "data": processed_records,
            "is_draft": filters.get("is_draft", False)
        }
        generate_pdf("reports/faculty_attendance.html", context, output_path)
        
    elif format_type == "xlsx":
        self.update_progress(job_id, 70, "Building Faculty Attendance Excel sheets...")
        report = ExcelReport(
            title="FACULTY ATTENDANCE REPORT",
            subtitle=f"Dept: {dept or 'All Departments'} | Month: {month_name} {year} | Work Days: {working_days}"
        )
        
        # Sheet 1: Summary
        sheet1 = report.add_sheet("Summary")
        cols = [
            {"key": "employee_id", "label": "Faculty ID", "width": 12, "align": "center"},
            {"key": "name", "label": "Faculty Name", "width": 25, "align": "left"},
            {"key": "designation", "label": "Designation", "width": 18, "align": "left"},
            {"key": "working_days", "label": "Total Work Days", "width": 15, "align": "center", "format": "integer"},
            {"key": "present", "label": "Days Present", "width": 12, "align": "center", "format": "integer"},
            {"key": "absent", "label": "Days Absent", "width": 12, "align": "center", "format": "integer"},
            {"key": "leaves", "label": "Leaves Taken", "width": 12, "align": "center", "format": "integer"},
            {"key": "percentage", "label": "% Attendance", "width": 15, "align": "center", "format": "percentage"}
        ]
        sheet1.set_headers(cols)
        
        rows_data = []
        for p in processed_records:
            rows_data.append({
                "employee_id": p["employee_id"],
                "name": p["name"],
                "designation": p["designation"],
                "working_days": p["working_days"],
                "present": p["present"],
                "absent": p["absent"],
                "leaves": p["leaves"],
                "percentage": p["percentage"] / 100.0
            })
        sheet1.add_rows(rows_data)
        sheet1.apply_conditional_format("percentage", [{"min": 0, "max": 0.85, "fill_color": "FCE4D6"}])
        sheet1.freeze(row=5, col=2)
        
        # Sheet 2: Leave Ledger
        sheet2 = report.add_sheet("Leave Ledger")
        ledger_cols = [
            {"key": "faculty_name", "label": "Faculty Name", "width": 25, "align": "left"},
            {"key": "from_date", "label": "From Date", "width": 15, "align": "center"},
            {"key": "to_date", "label": "To Date", "width": 15, "align": "center"},
            {"key": "days", "label": "Days Count", "width": 12, "align": "center", "format": "integer"},
            {"key": "type", "label": "Leave Type", "width": 15, "align": "center"},
            {"key": "status", "label": "Approval Status", "width": 15, "align": "center"}
        ]
        sheet2.set_headers(ledger_cols)
        sheet2.add_rows(leave_ledger)
        sheet2.freeze(row=5, col=2)
        
        report.save(output_path)
        
    file_size = os.path.getsize(output_path)
    self.mark_done(job_id, output_path, file_size)
    return {"status": "success", "file_path": output_path, "file_size": file_size}

@celery.task(base=BaseReportTask, bind=True, name="tasks.reports.hr_reports.generate_faculty_workload_report")
def generate_faculty_workload_report(self, filters, output_path):
    job_id = self.request.id
    self.update_progress(job_id, 20, "Analyzing workload stats...")
    
    dept = filters.get("department")
    semester = filters.get("semester")
    acad_yr = filters.get("academic_year")
    
    # Workload statistics query
    sql = """
        SELECT 
            f.id as faculty_id,
            f.name as faculty_name,
            f.dept as department,
            COALESCE(ARRAY_TO_STRING(ARRAY_AGG(DISTINCT t.subject), ', '), 'None') as subjects_assigned,
            COUNT(DISTINCT t.id) * 14 as lectures_scheduled, -- standard 14 weeks semester length
            COUNT(DISTINCT s.id) as lectures_taken,
            COALESCE(ROUND(AVG(att.present_count), 2), 0) as avg_students
        FROM faculty f
        LEFT JOIN timetable t ON t.faculty_id = f.id AND t.semester = %s
        LEFT JOIN attendance_sessions s ON s.timetable_id = t.id
        LEFT JOIN (
            SELECT session_id, COUNT(*) FILTER (WHERE status = 'Present') as present_count
            FROM attendance
            GROUP BY session_id
        ) att ON att.session_id = s.id
        WHERE f.is_active = TRUE
    """
    params = [semester]
    if dept:
        sql += " AND f.dept = %s"
        params.append(dept)
        
    sql += """
        GROUP BY f.id, f.name, f.dept
        ORDER BY f.name
    """
    
    records = qry(sql, tuple(params))
    
    processed_records = []
    for r in records:
        taken = int(r["lectures_taken"])
        scheduled = int(r["lectures_scheduled"])
        missed = max(0, scheduled - taken)
        
        processed_records.append({
            "name": r["faculty_name"],
            "department": r["department"],
            "subjects": r["subjects_assigned"],
            "scheduled": scheduled,
            "taken": taken,
            "missed": missed,
            "avg_students": float(r["avg_students"])
        })
        
    format_type = output_path.split(".")[-1].lower()
    
    if format_type == "pdf":
        self.update_progress(job_id, 75, "Rendering Workload PDF layout...")
        context = {
            "job_id": job_id,
            "generated_at": datetime.now().strftime("%d-%b-%Y %I:%M %p"),
            "department": dept or "All",
            "semester": semester,
            "academic_year": acad_yr,
            "data": processed_records,
            "is_draft": filters.get("is_draft", False)
        }
        generate_pdf("reports/faculty_workload.html", context, output_path)
        
    elif format_type == "xlsx":
        self.update_progress(job_id, 70, "Building Workload Excel Sheet...")
        report = ExcelReport(
            title="FACULTY WORKLOAD ANALYSIS",
            subtitle=f"Dept: {dept or 'All'} | Semester: {semester} | Academic Year: {acad_yr}"
        )
        
        # Unique departments
        depts = list(set(r["department"] for r in processed_records))
        for d in depts:
            sheet = report.add_sheet(d)
            cols = [
                {"key": "name", "label": "Faculty Name", "width": 25, "align": "left"},
                {"key": "subjects", "label": "Subjects Assigned", "width": 30, "align": "left"},
                {"key": "scheduled", "label": "Scheduled Lectures", "width": 18, "align": "center", "format": "integer"},
                {"key": "taken", "label": "Lectures Taken", "width": 15, "align": "center", "format": "integer"},
                {"key": "missed", "label": "Lectures Missed", "width": 15, "align": "center", "format": "integer"},
                {"key": "avg_students", "label": "Avg Students/Lecture", "width": 20, "align": "center", "format": "float"}
            ]
            sheet.set_headers(cols)
            
            # Filter rows for this department
            dept_rows = [r for r in processed_records if r["department"] == d]
            sheet.add_rows(dept_rows)
            sheet.freeze(row=5, col=1)
            
        report.save(output_path)
        
    file_size = os.path.getsize(output_path)
    self.mark_done(job_id, output_path, file_size)
    return {"status": "success", "file_path": output_path, "file_size": file_size}

@celery.task(base=BaseReportTask, bind=True, name="tasks.reports.hr_reports.generate_institution_summary")
def generate_institution_summary(self, filters, output_path):
    job_id = self.request.id
    self.update_progress(job_id, 10, "Starting Institution Summary Generation...")
    
    acad_yr = filters.get("academic_year")
    as_of_date_str = filters.get("as_of_date")
    as_of_date = datetime.strptime(as_of_date_str, "%Y-%m-%d").date() if as_of_date_str else date.today()
    
    # Temporary PDF paths
    temp_pdfs = []
    
    try:
        # SECTION 1: Enrollment Summary
        self.update_progress(job_id, 25, "Compiling Section 1: Enrollments...")
        sec1_rows = qry(
            """
            SELECT dept as department, year, division, COUNT(*) as student_count
            FROM students
            WHERE is_active = TRUE
            GROUP BY dept, year, division
            ORDER BY dept, year, division
            """
        )
        
        fd1, path1 = tempfile.mkstemp(suffix=".pdf")
        os.close(fd1)
        temp_pdfs.append(path1)
        
        generate_pdf("reports/inst_section_1.html", {
            "job_id": job_id,
            "generated_at": datetime.now().strftime("%d-%b-%Y"),
            "data": [dict(r) for r in sec1_rows],
            "academic_year": acad_yr
        }, path1)
        
        # SECTION 2: Overall Attendance
        self.update_progress(job_id, 50, "Compiling Section 2: Attendance...")
        month_start = as_of_date.replace(day=1)
        
        sec2_rows = qry(
            """
            SELECT s.dept as department,
                   COALESCE(ROUND(COUNT(a.id) FILTER (WHERE a.status='Present') * 100.0 / NULLIF(COUNT(a.id), 0), 2), 0.0) as attendance_pct
            FROM students s
            LEFT JOIN attendance a ON a.student_id = s.id AND a.date BETWEEN %s AND %s
            WHERE s.is_active = TRUE
            GROUP BY s.dept
            ORDER BY s.dept
            """,
            (month_start, as_of_date)
        )
        
        fd2, path2 = tempfile.mkstemp(suffix=".pdf")
        os.close(fd2)
        temp_pdfs.append(path2)
        
        generate_pdf("reports/inst_section_2.html", {
            "job_id": job_id,
            "generated_at": datetime.now().strftime("%d-%b-%Y"),
            "data": [dict(r) for r in sec2_rows],
            "month_range": f"{month_start.strftime('%B %Y')}"
        }, path2)
        
        # SECTION 3: Results Pass Rate
        self.update_progress(job_id, 75, "Compiling Section 3: Pass Rates...")
        sec3_rows = qry(
            """
            SELECT s.dept as department,
                   COALESCE(ROUND(COUNT(r.id) FILTER (WHERE r.grade != 'F') * 100.0 / NULLIF(COUNT(r.id), 0), 2), 0.0) as pass_pct
            FROM students s
            JOIN results r ON s.id = r.student_id
            WHERE s.is_active = TRUE
            GROUP BY s.dept
            ORDER BY s.dept
            """
        )
        
        fd3, path3 = tempfile.mkstemp(suffix=".pdf")
        os.close(fd3)
        temp_pdfs.append(path3)
        
        generate_pdf("reports/inst_section_3.html", {
            "job_id": job_id,
            "generated_at": datetime.now().strftime("%d-%b-%Y"),
            "data": [dict(r) for r in sec3_rows]
        }, path3)
        
        # SECTION 4: Faculty Headcount & Vacancy Status
        self.update_progress(job_id, 90, "Compiling Section 4: Faculty Headcounts...")
        sec4_rows = qry(
            """
            SELECT dept as department, COUNT(*) as headcount
            FROM faculty
            WHERE is_active = TRUE
            GROUP BY dept
            ORDER BY dept
            """
        )
        
        # Calculate vacancy estimates (10% of headcount)
        fac_data = []
        for r in sec4_rows:
            headcount = int(r["headcount"])
            vacancies = max(1, int(headcount * 0.15))
            fac_data.append({
                "department": r["department"],
                "headcount": headcount,
                "vacancies": vacancies,
                "status": "Shortage" if vacancies > 2 else "Optimal"
            })
            
        fd4, path4 = tempfile.mkstemp(suffix=".pdf")
        os.close(fd4)
        temp_pdfs.append(path4)
        
        generate_pdf("reports/inst_section_4.html", {
            "job_id": job_id,
            "generated_at": datetime.now().strftime("%d-%b-%Y"),
            "data": fac_data
        }, path4)
        
        # MERGE SECTIONS
        self.update_progress(job_id, 95, "Merging all sections into final PDF...")
        merge_pdfs(temp_pdfs, output_path)
        
    finally:
        # Clean up temporary files
        for p in temp_pdfs:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception as clean_err:
                    logger.warning(f"Failed to remove temp PDF file {p}: {clean_err}")
                    
    file_size = os.path.getsize(output_path)
    self.mark_done(job_id, output_path, file_size)
    return {"status": "success", "file_path": output_path, "file_size": file_size}
