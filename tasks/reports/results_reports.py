import os
import io
import base64
from datetime import datetime
import qrcode

from celery_app import celery
from tasks.reports.base_report_task import BaseReportTask
from utils.pg_wrapper import qry, qone, exe
from utils.pdf_generator import generate_pdf

# ReportLab Imports
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Circle, Rect, String
from reportlab.graphics.charts.piecharts import Pie

def get_grade_point(grade):
    grade_points = {
        'O': 10, 'A+': 9, 'A': 8, 'B+': 7, 'B': 6, 'C': 5, 'F': 0
    }
    return grade_points.get(grade, 0)

@celery.task(base=BaseReportTask, bind=True, name="tasks.reports.results_reports.generate_student_marksheet")
def generate_student_marksheet(self, filters, output_path):
    job_id = self.request.id
    self.update_progress(job_id, 15, "Retrieving student profile details...")
    
    student_id = int(filters.get("student_id"))
    semester = filters.get("semester")
    
    student = qone(
        """
        SELECT id, name, roll, prn, division, department, year 
        FROM students 
        WHERE id = %s AND is_active = TRUE
        """,
        (student_id,)
    )
    if not student:
        raise ValueError(f"Student with ID {student_id} not found.")
        
    self.update_progress(job_id, 40, "Fetching published results...")
    
    # Query results joined with subjects to get code and credits
    rows = qry(
        """
        SELECT r.internal_marks, r.external_marks, r.total as total_marks, r.grade, r.is_published,
               s.name as subject_name, s.code as subject_code, s.credits
        FROM results r
        JOIN subjects s ON r.subject_id = s.id
        WHERE r.student_id = %s AND r.semester = %s AND r.is_published = TRUE
        ORDER BY s.name
        """,
        (student_id, semester)
    )
    
    # Calculate SGPA and aggregates
    total_earned_marks = 0.0
    total_max_marks = 0
    total_credits = 0
    weighted_grade_points = 0.0
    failed_count = 0
    
    results_list = []
    for r in rows:
        internal = float(r["internal_marks"]) if r["internal_marks"] is not None else 0.0
        external = float(r["external_marks"]) if r["external_marks"] is not None else 0.0
        total = float(r["total_marks"]) if r["total_marks"] is not None else (internal + external)
        
        # Assume max marks of 100 per subject
        max_marks = 100
        grade = r["grade"] or "F"
        
        total_earned_marks += total
        total_max_marks += max_marks
        
        credits = int(r["credits"]) if r["credits"] is not None else 4
        grade_point = get_grade_point(grade)
        
        total_credits += credits
        weighted_grade_points += (grade_point * credits)
        
        if grade == "F" or total < 40.0:
            failed_count += 1
            result_status = "FAIL"
        else:
            result_status = "PASS"
            
        results_list.append({
            "subject_code": r["subject_code"],
            "subject_name": r["subject_name"],
            "internal_marks": internal,
            "external_marks": external,
            "total_marks": total,
            "max_marks": max_marks,
            "grade": grade,
            "result": result_status
        })
        
    sgpa = (weighted_grade_points / total_credits) if total_credits > 0 else 0.0
    percentage = (total_earned_marks * 100.0 / total_max_marks) if total_max_marks > 0 else 0.0
    
    if failed_count == 0:
        overall_result = "PASS"
    elif failed_count <= 2:
        overall_result = "ATKT"
    else:
        overall_result = "FAIL"
        
    overall = {
        "total_marks": total_earned_marks,
        "max_marks": total_max_marks,
        "percentage": percentage,
        "sgpa": sgpa,
        "result": overall_result
    }
    
    self.update_progress(job_id, 70, "Generating verification QR code...")
    # QR Code generation
    verify_url = f"http://localhost:8000/api/v1/results/verify?prn={student['prn']}&sem={semester}"
    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)
    qr_base64 = base64.b64encode(qr_buf.read()).decode("utf-8")
    
    self.update_progress(job_id, 85, "Compiling PDF marksheet template...")
    context = {
        "job_id": job_id,
        "generated_at": datetime.now().strftime("%d-%b-%Y %I:%M %p"),
        "student": student,
        "semester": semester,
        "academic_year": student.get("year", "N/A"),
        "results": results_list,
        "overall": overall,
        "qr_code": qr_base64,
        "is_draft": filters.get("is_draft", False)
    }
    
    generate_pdf("reports/student_marksheet.html", context, output_path)
    
    file_size = os.path.getsize(output_path)
    self.mark_done(job_id, output_path, file_size)
    return {"status": "success", "file_path": output_path, "file_size": file_size}

@celery.task(base=BaseReportTask, bind=True, name="tasks.reports.results_reports.generate_class_result_analysis")
def generate_class_result_analysis(self, filters, output_path):
    job_id = self.request.id
    self.update_progress(job_id, 10, "Fetching class result metadata...")
    
    dept = filters.get("department")
    year = filters.get("year")
    division = filters.get("division")
    semester = filters.get("semester")
    
    self.update_progress(job_id, 25, "Aggregating performance stats...")
    
    # 1. Fetch subjects
    subjects_rows = qry(
        "SELECT id, name, code, credits FROM subjects WHERE department = %s AND semester = %s ORDER BY name",
        (dept, semester)
    )
    subject_map = {s["id"]: s for s in subjects_rows}
    
    # 2. Fetch students
    std_sql = "SELECT id, name, roll FROM students WHERE department = %s AND year = %s AND is_active = TRUE"
    std_params = [dept, year]
    if division:
        std_sql += " AND division = %s"
        std_params.append(division)
    std_sql += " ORDER BY roll"
    
    students = qry(std_sql, tuple(std_params))
    student_ids = [s["id"] for s in students]
    
    if not student_ids:
        raise ValueError("No students found in class matching filters.")
        
    # 3. Fetch marks
    marks = qry(
        """
        SELECT student_id, subject_id, total, grade
        FROM results
        WHERE semester = %s AND is_published = TRUE AND student_id = ANY(%s)
        """,
        (semester, student_ids)
    )
    
    # Restructure marks mapping
    marks_map = {} # { student_id: { subject_id: {total, grade} } }
    for m in marks:
        sid = m["student_id"]
        subid = m["subject_id"]
        if sid not in marks_map:
            marks_map[sid] = {}
        marks_map[sid][subid] = {
            "total": float(m["total"]) if m["total"] is not None else 0.0,
            "grade": m["grade"] or "F"
        }
        
    # Process Class Statistics
    pass_count = 0
    fail_count = 0
    atkt_count = 0
    total_class_marks = 0.0
    total_class_max = 0
    highest_marks = -1.0
    lowest_marks = 999.0
    
    subject_analysis = {s["id"]: {"pass": 0, "fail": 0, "total_marks": 0.0, "count": 0, "highest": -1.0, "highest_student": ""} for s in subjects_rows}
    student_summaries = []
    
    for s in students:
        sid = s["id"]
        student_marks = marks_map.get(sid, {})
        
        student_failed_count = 0
        student_total = 0.0
        student_max = 0
        student_weighted_gp = 0.0
        student_credits = 0
        
        for sub in subjects_rows:
            subid = sub["id"]
            credits = int(sub["credits"]) if sub["credits"] is not None else 4
            
            sub_mark = student_marks.get(subid, {"total": 0.0, "grade": "F"})
            total = sub_mark["total"]
            grade = sub_mark["grade"]
            
            student_total += total
            student_max += 100
            
            gp = get_grade_point(grade)
            student_weighted_gp += (gp * credits)
            student_credits += credits
            
            # Subject specific aggregates
            analysis = subject_analysis[subid]
            analysis["count"] += 1
            analysis["total_marks"] += total
            
            if grade == "F" or total < 40.0:
                student_failed_count += 1
                analysis["fail"] += 1
            else:
                analysis["pass"] += 1
                
            if total > analysis["highest"]:
                analysis["highest"] = total
                analysis["highest_student"] = s["name"]
                
        sgpa = (student_weighted_gp / student_credits) if student_credits > 0 else 0.0
        
        # Determine overall result
        if student_failed_count == 0:
            pass_count += 1
            res = "PASS"
        elif student_failed_count <= 2:
            atkt_count += 1
            res = "ATKT"
        else:
            fail_count += 1
            res = "FAIL"
            
        if student_max > 0:
            total_class_marks += student_total
            total_class_max += student_max
            if student_total > highest_marks:
                highest_marks = student_total
            if student_total < lowest_marks:
                lowest_marks = student_total
                
        student_summaries.append({
            "roll": s["roll"],
            "name": s["name"],
            "marks": student_marks,
            "sgpa": sgpa,
            "result": res
        })
        
    class_average = (total_class_marks * 100.0 / total_class_max) if total_class_max > 0 else 0.0
    total_students = len(students)
    
    pass_pct = (pass_count * 100.0 / total_students) if total_students > 0 else 0.0
    fail_pct = (fail_count * 100.0 / total_students) if total_students > 0 else 0.0
    atkt_pct = (atkt_count * 100.0 / total_students) if total_students > 0 else 0.0
    
    self.update_progress(job_id, 60, "Generating ReportLab PDF document structure...")
    
    # Build ReportLab Document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#800000'),
        alignment=1, # Center
        spaceAfter=15
    )
    
    header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#800000'),
        spaceBefore=15,
        spaceAfter=10
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9,
        leading=13
    )
    
    grid_header_style = ParagraphStyle(
        'GridHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1
    )
    
    grid_cell_style = ParagraphStyle(
        'GridCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        alignment=1
    )
    
    grid_cell_left = ParagraphStyle(
        'GridCellLeft',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        alignment=0
    )
    
    story = []
    
    # --- PAGE 1: Executive Summary & Donut Chart ---
    story.append(Paragraph("CLASS PERFORMANCE ANALYSIS REPORT", title_style))
    story.append(Spacer(1, 10))
    
    # Meta Details Box
    meta_data = [
        [Paragraph(f"<b>Department:</b> {dept}", body_style), Paragraph(f"<b>Semester:</b> {semester}", body_style)],
        [Paragraph(f"<b>Class / Division:</b> Year {year} / Div {division or 'All'}", body_style), Paragraph(f"<b>Date Generated:</b> {datetime.now().strftime('%d-%b-%Y')}", body_style)]
    ]
    meta_table = Table(meta_data, colWidths=[260, 260])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F5F5F5')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#800000')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))
    
    # KPI metrics table
    story.append(Paragraph("Executive Performance Metrics", header_style))
    kpi_data = [
        [
            Paragraph("<b>Total Students</b>", grid_cell_style),
            Paragraph("<b>Pass %</b>", grid_cell_style),
            Paragraph("<b>ATKT %</b>", grid_cell_style),
            Paragraph("<b>Fail %</b>", grid_cell_style),
            Paragraph("<b>Class Average</b>", grid_cell_style)
        ],
        [
            Paragraph(str(total_students), grid_cell_style),
            Paragraph(f"{pass_pct:.2f}%", grid_cell_style),
            Paragraph(f"{atkt_pct:.2f}%", grid_cell_style),
            Paragraph(f"{fail_pct:.2f}%", grid_cell_style),
            Paragraph(f"{class_average:.2f}%", grid_cell_style)
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[104]*5)
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#800000')),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#FDF2F2')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#EAEAEA')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#EAEAEA')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 20))
    
    # Donut Chart Drawing
    story.append(Paragraph("Result Distribution", header_style))
    
    drawing = Drawing(400, 180)
    pie = Pie()
    pie.x = 100
    pie.y = 10
    pie.width = 150
    pie.height = 150
    pie.data = [pass_count, atkt_count, fail_count]
    pie.labels = [f"Pass ({pass_count})", f"ATKT ({atkt_count})", f"Fail ({fail_count})"]
    pie.slices.strokeWidth = 0.5
    pie.slices[0].fillColor = colors.HexColor('#2ecc71')
    pie.slices[1].fillColor = colors.HexColor('#f1c40f')
    pie.slices[2].fillColor = colors.HexColor('#e74c3c')
    drawing.add(pie)
    
    # White inner circle to convert to donut
    inner_circle = Circle(175, 85, 45)
    inner_circle.fillColor = colors.white
    inner_circle.strokeColor = colors.white
    drawing.add(inner_circle)
    
    story.append(drawing)
    story.append(PageBreak())
    
    # --- PAGE 2: Subject-wise Analysis Table ---
    story.append(Paragraph("Subject-Wise Performance Breakdown", header_style))
    sub_table_headers = [
        Paragraph("Code", grid_header_style),
        Paragraph("Subject Name", grid_header_style),
        Paragraph("Pass", grid_header_style),
        Paragraph("Fail", grid_header_style),
        Paragraph("Avg Marks", grid_header_style),
        Paragraph("Highest Scorer", grid_header_style)
    ]
    sub_table_data = [sub_table_headers]
    for sub in subjects_rows:
        subid = sub["id"]
        analysis = subject_analysis[subid]
        avg = (analysis["total_marks"] / analysis["count"]) if analysis["count"] > 0 else 0.0
        
        # Abbreviate scorer name if needed
        scorer_name = analysis["highest_student"]
        if len(scorer_name) > 15:
            scorer_name = scorer_name.split()[0]
            
        sub_table_data.append([
            Paragraph(sub["code"], grid_cell_style),
            Paragraph(sub["name"], grid_cell_left),
            Paragraph(str(analysis["pass"]), grid_cell_style),
            Paragraph(str(analysis["fail"]), grid_cell_style),
            Paragraph(f"{avg:.2f}", grid_cell_style),
            Paragraph(f"{scorer_name} ({analysis['highest']:.1f})", grid_cell_style)
        ])
        
    sub_table = Table(sub_table_data, colWidths=[55, 175, 45, 45, 60, 140])
    sub_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#800000')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CCCCCC')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#EAEAEA')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9F9F9')]),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(sub_table)
    story.append(PageBreak())
    
    # --- PAGE 3: Class Results Matrix ---
    story.append(Paragraph("Complete Student Marks Matrix", header_style))
    
    # Build columns based on subjects count dynamically
    matrix_headers = [Paragraph("Roll", grid_header_style), Paragraph("Student Name", grid_header_style)]
    for sub in subjects_rows:
        matrix_headers.append(Paragraph(sub["code"], grid_header_style))
    matrix_headers.append(Paragraph("SGPA", grid_header_style))
    matrix_headers.append(Paragraph("Result", grid_header_style))
    
    matrix_data = [matrix_headers]
    
    for s in student_summaries:
        row = [
            Paragraph(s["roll"], grid_cell_style),
            Paragraph(s["name"], grid_cell_left)
        ]
        for sub in subjects_rows:
            subid = sub["id"]
            sub_total = s["marks"].get(subid, {}).get("total", "-")
            row.append(Paragraph(str(sub_total), grid_cell_style))
            
        row.append(Paragraph(f"{s['sgpa']:.2f}", grid_cell_style))
        
        # Result status coloring in PDF
        res_color = "#155724" if s["result"] == "PASS" else ("#856404" if s["result"] == "ATKT" else "#721c24")
        row.append(Paragraph(f"<font color='{res_color}'><b>{s['result']}</b></font>", grid_cell_style))
        matrix_data.append(row)
        
    # Calculate column widths
    subject_cols_count = len(subjects_rows)
    avail_width = 520
    roll_width = 35
    result_width = 45
    sgpa_width = 40
    name_width = 140
    # Remaining width distributed to subjects
    each_subject_width = (avail_width - roll_width - result_width - sgpa_width - name_width) / subject_cols_count
    
    col_widths = [roll_width, name_width] + [each_subject_width] * subject_cols_count + [sgpa_width, result_width]
    
    matrix_table = Table(matrix_data, colWidths=col_widths, repeatRows=1)
    matrix_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#800000')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CCCCCC')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#EAEAEA')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9F9F9')]),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(matrix_table)
    
    # Official disclaimer at end
    story.append(Spacer(1, 20))
    story.append(Paragraph("<font size='7' color='#777'><i>This is an official computer-generated aggregate analysis document compiled by the DY Patil University Exams Cell.</i></font>", grid_cell_style))
    
    self.update_progress(job_id, 85, "Saving compiled ReportLab PDF...")
    doc.build(story)
    
    file_size = os.path.getsize(output_path)
    self.mark_done(job_id, output_path, file_size)
    return {"status": "success", "file_path": output_path, "file_size": file_size}
