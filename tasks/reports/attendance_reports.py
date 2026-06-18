import os
import calendar
import io
import base64
from datetime import datetime, date, timedelta
import matplotlib
matplotlib.use('Agg')  # Headless mode for matplotlib
import matplotlib.pyplot as plt

from celery_app import celery
from tasks.reports.base_report_task import BaseReportTask
from utils.pg_wrapper import qry, qone, exe
from utils.pdf_generator import generate_pdf
from utils.excel_generator import ExcelReport
from services.parent_notification_service import ParentNotificationService

def get_date_range_from_month_academic_year(month_val, academic_year_str):
    """
    Parses a month (number/string) and academic year (e.g. 2025-26)
    and returns date(start) and date(end).
    """
    months_map = {
        'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
        'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
        'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12
    }
    
    # Normalize month
    if isinstance(month_val, str):
        month_lower = month_val.strip().lower()
        if month_lower.isdigit():
            month = int(month_lower)
        else:
            month = months_map.get(month_lower, 6)  # fallback to June
    else:
        month = int(month_val)
        
    # Parse academic year (e.g., "2025-26" or "2025")
    parts = academic_year_str.split('-')
    start_year = int(parts[0])
    
    # Academic months June-Dec belong to start_year; Jan-May belong to next year
    if month <= 5:
        if len(parts) > 1:
            end_year_part = parts[1]
            if len(end_year_part) == 2:
                year = int(str(start_year)[:2] + end_year_part)
            else:
                year = int(end_year_part)
        else:
            year = start_year + 1
    else:
        year = start_year
        
    _, last_day = calendar.monthrange(year, month)
    return date(year, month, 1), date(year, month, last_day)

@celery.task(base=BaseReportTask, bind=True, name="tasks.reports.attendance_reports.generate_monthly_attendance_report")
def generate_monthly_attendance_report(self, filters, output_path):
    job_id = self.request.id
    self.update_progress(job_id, 10, "Initializing filters...")
    
    dept = filters.get("department")
    month_val = filters.get("month")
    acad_yr = filters.get("academic_year")
    year = filters.get("year")  # e.g., I, II, III
    division = filters.get("division")
    
    start_date, end_date = get_date_range_from_month_academic_year(month_val, acad_yr)
    
    self.update_progress(job_id, 25, "Fetching student list and attendance percentages...")
    
    # Base query for attendance percentages
    sql = """
        SELECT 
            s.id, s.roll, s.name, s.division, s.year,
            COUNT(a.id) FILTER (WHERE a.status='Present') AS present,
            COUNT(a.id) FILTER (WHERE a.status='Absent')  AS absent,
            COUNT(a.id) AS total,
            COALESCE(ROUND(
                COUNT(a.id) FILTER (WHERE a.status='Present') * 100.0 
                / NULLIF(COUNT(a.id), 0), 2
            ), 0.0) AS percentage
        FROM students s
        LEFT JOIN attendance a ON a.student_id = s.id AND a.date BETWEEN %s AND %s
        WHERE s.department = %s AND s.is_active = TRUE
    """
    params = [start_date, end_date, dept]
    
    if division:
        sql += " AND s.division = %s"
        params.append(division)
    if year:
        sql += " AND s.year = %s"
        params.append(year)
        
    sql += """
        GROUP BY s.id, s.roll, s.name, s.division, s.year
        ORDER BY s.roll
    """
    
    records = qry(sql, tuple(params))
    
    # Calculate stats
    total_records = len(records)
    defaulter_count = 0
    total_pct = 0.0
    valid_students_count = 0
    
    student_names_chart = []
    attendance_pcts_chart = []
    
    for r in records:
        pct = float(r["percentage"])
        if pct < 75.0:
            defaulter_count += 1
        if r["total"] > 0:
            total_pct += pct
            valid_students_count += 1
            
        # Add to chart arrays (abbreviate long names for chart readability)
        short_name = r["name"].split()[0] if r["name"] else "Student"
        student_names_chart.append(f"{r['roll']}-{short_name}")
        attendance_pcts_chart.append(pct)
        
    class_average = (total_pct / valid_students_count) if valid_students_count > 0 else 0.0
    
    # Format month name for display
    month_name = calendar.month_name[start_date.month]
    
    # Check format and compile
    format_type = output_path.split(".")[-1].lower()
    
    if format_type == "pdf":
        self.update_progress(job_id, 50, "Generating bar chart visualization...")
        # Matplotlib chart
        chart_base64 = None
        if total_records > 0:
            plt.figure(figsize=(10, 5))
            colors = ['#2ecc71' if p >= 75.0 else ('#f1c40f' if p >= 60.0 else '#e74c3c') for p in attendance_pcts_chart]
            plt.bar(student_names_chart[:25], attendance_pcts_chart[:25], color=colors[:25], width=0.5) # limit to first 25 for spacing
            plt.axhline(y=75, color='#e74c3c', linestyle='--', linewidth=1.5, label='75% Threshold')
            plt.title(f'Attendance Summary - {month_name} {start_date.year}', fontsize=12, fontweight='bold', color='#800000')
            plt.xlabel('Roll No & Student')
            plt.ylabel('Attendance %')
            plt.ylim(0, 105)
            plt.xticks(rotation=45, ha='right', fontsize=8)
            plt.grid(axis='y', linestyle=':', alpha=0.5)
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150)
            buf.seek(0)
            chart_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close()
            
        self.update_progress(job_id, 75, "Rendering PDF template...")
        context = {
            "job_id": job_id,
            "generated_at": datetime.now().strftime("%d-%b-%Y %I:%M %p"),
            "department": dept,
            "month": f"{month_name} {start_date.year}",
            "academic_year": acad_yr,
            "year": year,
            "division": division,
            "data": [dict(r) for r in records],
            "class_average": class_average,
            "defaulter_count": defaulter_count,
            "chart_img": chart_base64,
            "is_draft": filters.get("is_draft", False)
        }
        
        generate_pdf("reports/monthly_attendance.html", context, output_path)
        
    elif format_type == "xlsx":
        self.update_progress(job_id, 60, "Building Excel workbook sheets...")
        
        report = ExcelReport(
            title="MONTHLY ATTENDANCE SUMMARY",
            subtitle=f"Dept: {dept} | Month: {month_name} {start_date.year} | Year: {year or 'All'} | Div: {division or 'All'}"
        )
        
        # Sheet 1: Summary Table
        sheet1 = report.add_sheet("Summary")
        cols = [
            {"key": "roll", "label": "Roll No", "width": 10, "align": "center"},
            {"key": "name", "label": "Student Name", "width": 25, "align": "left"},
            {"key": "total", "label": "Total Classes", "width": 15, "align": "center", "format": "integer"},
            {"key": "present", "label": "Present", "width": 12, "align": "center", "format": "integer"},
            {"key": "absent", "label": "Absent", "width": 12, "align": "center", "format": "integer"},
            {"key": "percentage", "label": "Percentage", "width": 15, "align": "center", "format": "percentage"},
            {"key": "status", "label": "Status", "width": 15, "align": "center"}
        ]
        sheet1.set_headers(cols)
        
        # Process rows data shape
        rows_data = []
        for r in records:
            pct = float(r["percentage"])
            status = "OK" if pct >= 75.0 else ("Low" if pct >= 60.0 else "Defaulter")
            rows_data.append({
                "roll": r["roll"],
                "name": r["name"],
                "total": r["total"],
                "present": r["present"],
                "absent": r["absent"],
                "percentage": pct / 100.0,
                "status": status
            })
            
        sheet1.add_rows(rows_data)
        sheet1.add_summary_row({
            "roll": "Class Avg",
            "name": "",
            "total": "",
            "present": "",
            "absent": "",
            "percentage": class_average / 100.0,
            "status": f"Defaulters: {defaulter_count}"
        })
        
        # Apply conditional formatting (<75% gets light red fill)
        sheet1.apply_conditional_format("percentage", [{"min": 0, "max": 0.749, "fill_color": "FCE4D6"}])
        sheet1.freeze(row=5, col=2)
        
        # Sheet 2: Raw Grid data
        self.update_progress(job_id, 75, "Assembling Raw Data Grid...")
        sheet2 = report.add_sheet("Raw Data")
        
        # Fetch distinct dates of lectures
        date_rows = qry(
            """
            SELECT DISTINCT a.date 
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE s.department = %s AND a.date BETWEEN %s AND %s AND s.is_active = TRUE
            ORDER BY a.date
            """,
            (dept, start_date, end_date)
        )
        distinct_dates = [r["date"] for r in date_rows]
        
        # Headers for raw data sheet
        raw_cols = [
            {"key": "roll", "label": "Roll", "width": 8, "align": "center"},
            {"key": "name", "label": "Student Name", "width": 22, "align": "left"}
        ]
        for d in distinct_dates:
            date_str = d.strftime("%d-%b") if isinstance(d, (date, datetime)) else str(d)
            raw_cols.append({"key": f"date_{d}", "label": date_str, "width": 10, "align": "center"})
            
        sheet2.set_headers(raw_cols)
        
        # Fetch individual attendance actions
        raw_att = qry(
            """
            SELECT s.roll, s.name, a.date, a.status
            FROM students s
            LEFT JOIN attendance a ON a.student_id = s.id AND a.date BETWEEN %s AND %s
            WHERE s.department = %s AND s.is_active = TRUE
            ORDER BY s.roll, a.date
            """,
            (start_date, end_date, dept)
        )
        
        # Restructure raw attendance logs
        student_records_map = {}
        for r in raw_att:
            roll = r["roll"]
            if roll not in student_records_map:
                student_records_map[roll] = {"roll": roll, "name": r["name"]}
            if r["date"]:
                # P or A shorthand
                status_short = "P" if r["status"] == "Present" else ("A" if r["status"] == "Absent" else "")
                student_records_map[roll][f"date_{r['date']}"] = status_short
                
        sheet2.add_rows(list(student_records_map.values()))
        sheet2.freeze(row=5, col=2)
        
        # Sheet 3: Pivot breakdown
        sheet3 = report.add_sheet("Cohort Pivot")
        pivot_cols = [
            {"key": "year", "label": "Year", "width": 15, "align": "center"},
            {"key": "division", "label": "Division", "width": 15, "align": "center"},
            {"key": "avg_pct", "label": "Avg Attendance %", "width": 20, "align": "center", "format": "percentage"}
        ]
        sheet3.set_headers(pivot_cols)
        
        pivot_rows = qry(
            """
            SELECT s.year, s.division,
                   COALESCE(ROUND(COUNT(a.id) FILTER (WHERE a.status='Present') * 100.0 / NULLIF(COUNT(a.id), 0), 2), 0.0) as avg_pct
            FROM students s
            LEFT JOIN attendance a ON a.student_id = s.id AND a.date BETWEEN %s AND %s
            WHERE s.department = %s AND s.is_active = TRUE
            GROUP BY s.year, s.division
            ORDER BY s.year, s.division
            """,
            (start_date, end_date, dept)
        )
        
        pivot_data = []
        for r in pivot_rows:
            pivot_data.append({
                "year": r["year"],
                "division": r["division"],
                "avg_pct": float(r["avg_pct"]) / 100.0
            })
        sheet3.add_rows(pivot_data)
        
        report.save(output_path)
        
    file_size = os.path.getsize(output_path)
    self.mark_done(job_id, output_path, file_size)
    return {"status": "success", "file_path": output_path, "file_size": file_size}

@celery.task(base=BaseReportTask, bind=True, name="tasks.reports.attendance_reports.generate_defaulter_report")
def generate_defaulter_report(self, filters, output_path):
    job_id = self.request.id
    self.update_progress(job_id, 10, "Initializing defaulter filters...")
    
    dept = filters.get("department")
    year = filters.get("year")
    threshold = float(filters.get("threshold", 75.0))
    as_of_date_str = filters.get("as_of_date")
    as_of_date = datetime.strptime(as_of_date_str, "%Y-%m-%d").date() if as_of_date_str else date.today()
    
    self.update_progress(job_id, 30, "Querying attendance records below threshold...")
    
    # SQL query for defaulters list
    sql = """
        SELECT 
            s.id as student_id, s.roll, s.name, s.email,
            COUNT(a.id) FILTER (WHERE a.status='Present') AS present,
            COUNT(a.id) FILTER (WHERE a.status='Absent')  AS absent,
            COUNT(a.id) AS total,
            COALESCE(ROUND(
                COUNT(a.id) FILTER (WHERE a.status='Present') * 100.0 
                / NULLIF(COUNT(a.id), 0), 2
            ), 0.0) AS percentage
        FROM students s
        JOIN attendance a ON a.student_id = s.id
        WHERE s.department = %s AND a.date <= %s AND s.is_active = TRUE
    """
    params = [dept, as_of_date]
    if year:
        sql += " AND s.year = %s"
        params.append(year)
        
    sql += """
        GROUP BY s.id, s.roll, s.name, s.email
        HAVING COALESCE(ROUND(COUNT(a.id) FILTER (WHERE a.status='Present') * 100.0 / NULLIF(COUNT(a.id), 0), 2), 0.0) < %s
        ORDER BY percentage ASC
    """
    params.append(threshold)
    
    defaulters = qry(sql, tuple(params))
    
    # Process data and subjects below threshold
    self.update_progress(job_id, 50, "Calculating subject-wise shortages...")
    processed_defaulters = []
    
    # Pre-fetch parent contact templates or check template
    exe(
        """
        INSERT INTO sms_templates (slug, name, body, is_active)
        VALUES ('attendance_alert', 'Defaulter Alert', 'Dear {{parent_name}}, your ward {{student_name}} (Roll: {{roll}}) has low attendance: {{percentage}}% as of {{date}}. Please contact the department.', true)
        ON CONFLICT (slug) DO NOTHING
        """
    )
    
    for d in defaulters:
        # Fetch parent contact details
        parent = qone(
            """
            SELECT p.phone_primary, p.full_name
            FROM parent_contacts p
            JOIN student_parent_mapping m ON p.id = m.parent_id
            WHERE m.student_id = %s AND m.is_primary_contact = True
            LIMIT 1
            """,
            (d["student_id"],)
        )
        
        parent_contact = parent["phone_primary"] if parent else "N/A"
        parent_name = parent["full_name"] if parent else "Parent"
        
        # Calculate subject wise percentage below 75
        subject_stats = qry(
            """
            SELECT 
                subject,
                COALESCE(ROUND(COUNT(id) FILTER (WHERE status='Present') * 100.0 / NULLIF(COUNT(id), 0), 2), 0.0) as sub_pct
            FROM attendance
            WHERE student_id = %s AND date <= %s
            GROUP BY subject
            """,
            (d["student_id"], as_of_date)
        )
        
        subjects_below_75 = sum(1 for s in subject_stats if float(s["sub_pct"]) < 75.0)
        
        processed_defaulters.append({
            "student_id": d["student_id"],
            "roll": d["roll"],
            "name": d["name"],
            "contact": d["email"], # Email serves as student contact
            "parent_name": parent_name,
            "parent_contact": parent_contact,
            "percentage": float(d["percentage"]),
            "missed": int(d["absent"]),
            "subjects_below_75": subjects_below_75
        })
        
    # Format check and compile
    format_type = output_path.split(".")[-1].lower()
    
    if format_type == "pdf":
        self.update_progress(job_id, 70, "Rendering PDF Defaulter template...")
        # Since templates are jinja, we create a direct HTML file for defaulters list
        # For simplicity, we can render using monthly_attendance.html or a new template.
        # But wait, let's create templates/reports/defaulter_list.html in results or write a clean structure
        # Wait, the prompt says "PDF: only students BELOW threshold. Urgent red header banner..."
        # Let's create the HTML template files. Wait, we can write the HTML inside the base layout or create a new template.
        # Let's create templates/reports/defaulter_list.html! We will write it shortly.
        context = {
            "job_id": job_id,
            "generated_at": datetime.now().strftime("%d-%b-%Y %I:%M %p"),
            "department": dept,
            "year": year,
            "threshold": threshold,
            "as_of_date": as_of_date.strftime("%d-%b-%Y"),
            "data": processed_defaulters,
            "is_draft": filters.get("is_draft", False)
        }
        generate_pdf("reports/defaulter_list.html", context, output_path)
        
    elif format_type == "xlsx":
        self.update_progress(job_id, 70, "Building Excel Defaulter spreadsheet...")
        report = ExcelReport(
            title="ATTENDANCE DEFAULTER LIST (URGENT)",
            subtitle=f"Dept: {dept} | Threshold: < {threshold}% | As of: {as_of_date.strftime('%d-%b-%Y')}"
        )
        sheet = report.add_sheet("Defaulters")
        cols = [
            {"key": "roll", "label": "Roll", "width": 8, "align": "center"},
            {"key": "name", "label": "Student Name", "width": 25, "align": "left"},
            {"key": "contact", "label": "Student Email", "width": 22, "align": "left"},
            {"key": "parent_contact", "label": "Parent Contact", "width": 18, "align": "center"},
            {"key": "percentage", "label": "% Attendance", "width": 15, "align": "center", "format": "percentage"},
            {"key": "missed", "label": "Lectures Missed", "width": 15, "align": "center", "format": "integer"},
            {"key": "subjects_below_75", "label": "Subjects < 75%", "width": 15, "align": "center", "format": "integer"},
            {"key": "action_taken", "label": "Action Taken", "width": 20, "align": "left"} # Blank for manual fill
        ]
        sheet.set_headers(cols)
        
        rows_data = []
        for p in processed_defaulters:
            rows_data.append({
                "roll": p["roll"],
                "name": p["name"],
                "contact": p["contact"],
                "parent_contact": p["parent_contact"],
                "percentage": p["percentage"] / 100.0,
                "missed": p["missed"],
                "subjects_below_75": p["subjects_below_75"],
                "action_taken": ""
            })
            
        sheet.add_rows(rows_data)
        sheet.apply_conditional_format("percentage", [{"min": 0, "max": 1.0, "fill_color": "FCE4D6"}])
        sheet.freeze(row=5, col=2)
        report.save(output_path)
        
    # Queue parent SMS alerts asynchronously
    self.update_progress(job_id, 90, "Queueing parent SMS notifications...")
    for p in processed_defaulters:
        if p["parent_contact"] != "N/A" and p["parent_contact"].strip() != "":
            try:
                # Trigger parents notification
                ParentNotificationService.notify_student_parents(
                    student_id=p["student_id"],
                    category='attendance',
                    template_slug='attendance_alert',
                    context={
                        'percentage': f"{p['percentage']:.2f}",
                        'date': as_of_date.strftime('%d-%b-%Y')
                    }
                )
            except Exception as sms_err:
                # Log error but don't fail report compilation
                logger.warning(f"Failed to queue SMS for student {p['student_id']}: {sms_err}")
                
    file_size = os.path.getsize(output_path)
    self.mark_done(job_id, output_path, file_size)
    return {"status": "success", "file_path": output_path, "file_size": file_size}

@celery.task(base=BaseReportTask, bind=True, name="tasks.reports.attendance_reports.generate_timetable_pdf")
def generate_timetable_pdf(self, filters, output_path):
    job_id = self.request.id
    self.update_progress(job_id, 15, "Initializing timetable filters...")
    
    dept = filters.get("department") # maps to branch column
    year = filters.get("year")
    division = filters.get("division")
    semester = filters.get("semester")
    
    self.update_progress(job_id, 40, "Fetching timetable entries...")
    
    # Query database for published timetable entries
    records = qry(
        """
        SELECT day, time, start_time::TEXT as start_time, end_time::TEXT as end_time,
               subject, teacher, room, color
        FROM timetable
        WHERE branch = %s AND year = %s AND division = %s AND semester = %s AND published = true
        ORDER BY start_time
        """,
        (dept, year, division, semester)
    )
    
    self.update_progress(job_id, 65, "Structuring weekly grid...")
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    # Get distinct time slots sorted by start time
    time_slots = sorted(list(set(r['time'] for r in records)), key=lambda x: x.split('-')[0].strip())
    
    # Build grid structure
    grid = {slot: {day: [] for day in days} for slot in time_slots}
    for r in records:
        slot = r['time']
        day = r['day']
        if slot in grid and day in grid[slot]:
            grid[slot][day].append(r)
            
    # Assign consistent pastel colors to subjects
    distinct_subjects = list(set(r['subject'] for r in records))
    pastel_colors = [
        '#FFF0F5', '#E6F2FF', '#EAFaf1', '#FFFDE6', '#FFF3E0', 
        '#F3E5F5', '#E0F7FA', '#E8F5E9', '#F9F1E7', '#FCE4EC'
    ]
    subject_colors = {sub: pastel_colors[idx % len(pastel_colors)] for idx, sub in enumerate(distinct_subjects)}
    
    self.update_progress(job_id, 80, "Rendering timetable PDF...")
    context = {
        "job_id": job_id,
        "generated_at": datetime.now().strftime("%d-%b-%Y %I:%M %p"),
        "department": dept,
        "year": year,
        "division": division,
        "semester": semester,
        "academic_year": filters.get("academic_year", "N/A"),
        "time_slots": time_slots,
        "days": days,
        "grid": grid,
        "subject_colors": subject_colors,
        "is_draft": filters.get("is_draft", False)
    }
    
    generate_pdf("reports/timetable_grid.html", context, output_path)
    
    file_size = os.path.getsize(output_path)
    self.mark_done(job_id, output_path, file_size)
    return {"status": "success", "file_path": output_path, "file_size": file_size}
