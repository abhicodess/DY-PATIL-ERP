import os
from flask import render_template, request, session, redirect, url_for, flash, jsonify
import openpyxl
from blueprints.student_timetable import student_timetable_bp
from blueprints.auth.decorators import login_required, faculty_required, admin_required, student_required
from utils.pg_wrapper import qry, qone, exe
from config import DEPARTMENTS, SEMESTERS, DIVISIONS, DAYS

# Standard periods 1 to 8
PERIODS = [f"Period {i}" for i in range(1, 9)]

@student_timetable_bp.route("/faculty/assign-student-timetable", methods=["GET", "POST"])
@faculty_required
def assign_student_timetable():
    faculty_id = session.get("faculty_id")
    
    # Get faculty name
    fac = qone("SELECT name FROM faculty WHERE id = %s", (faculty_id,))
    faculty_name = fac["name"] if fac else "Faculty"

    if request.method == "POST":
        # Check if this is an Excel upload or form submission
        if 'excel_file' in request.files:
            file = request.files['excel_file']
            if file.filename == '':
                flash("No selected file", "danger")
                return redirect(request.url)
            
            if not file.filename.endswith(('.xlsx', '.xls')):
                flash("Invalid file format. Please upload an Excel file (.xlsx or .xls)", "danger")
                return redirect(request.url)

            try:
                wb = openpyxl.load_workbook(file, read_only=True)
                sheet = wb.active
                
                imported_count = 0
                error_count = 0
                
                # Expected headers: Division, Semester, Department, Day, Time Slot, Subject, Room
                # We start reading from row 2 (assuming row 1 is header)
                for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                    if not any(row):  # Skip empty rows
                        continue
                        
                    if len(row) < 6:
                        error_count += 1
                        continue
                    
                    division, semester, day, time_slot, subject, room = row[0], row[1], row[2], row[3], row[4], row[5]
                    # Check if department is provided in 7th column, otherwise default to "General" or empty
                    department = row[6] if len(row) > 6 and row[6] else "General"
                    
                    # Basic validation
                    if not (division and semester and day and time_slot and subject and room):
                        error_count += 1
                        continue
                        
                    exe("""
                        INSERT INTO student_timetable 
                        (division, semester, department, day, time_slot, subject, faculty_name, room, created_by_faculty_id, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                    """, (
                        str(division).strip(), 
                        str(semester).strip(), 
                        str(department).strip(), 
                        str(day).strip(), 
                        str(time_slot).strip(), 
                        str(subject).strip(), 
                        faculty_name, 
                        str(room).strip(), 
                        faculty_id
                    ))
                    imported_count += 1
                
                if error_count > 0:
                    flash(f"Imported {imported_count} records. Skipped {error_count} invalid rows.", "warning")
                else:
                    flash(f"Successfully imported {imported_count} timetable requests from Excel!", "success")
                
                return redirect(request.url)
                
            except Exception as e:
                flash(f"Error processing Excel file: {str(e)}", "danger")
                return redirect(request.url)
        
        else:
            # Handle standard form submission
            division = request.form.get("division")
            semester = request.form.get("semester")
            department = request.form.get("department")
            day = request.form.get("day")
            time_slot = request.form.get("time_slot")
            subject = request.form.get("subject")
            room = request.form.get("room")
            
            if not (division and semester and department and day and time_slot and subject and room):
                flash("All form fields are required.", "danger")
                return redirect(request.url)
                
            try:
                exe("""
                    INSERT INTO student_timetable 
                    (division, semester, department, day, time_slot, subject, faculty_name, room, created_by_faculty_id, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                """, (division, semester, department, day, time_slot, subject, faculty_name, room, faculty_id))
                
                flash("Timetable slot submitted for approval!", "success")
                return redirect(request.url)
            except Exception as e:
                flash(f"Error saving request: {str(e)}", "danger")
                return redirect(request.url)

    # Fetch all requests assigned by this faculty
    my_requests = qry("""
        SELECT * FROM student_timetable 
        WHERE created_by_faculty_id = %s 
        ORDER BY created_at DESC
    """, (faculty_id,))

    return render_template(
        "faculty/assign_student_timetable.html",
        requests=my_requests,
        DEPARTMENTS=DEPARTMENTS,
        SEMESTERS=SEMESTERS,
        DIVISIONS=DIVISIONS,
        DAYS=DAYS,
        PERIODS=PERIODS
    )

@student_timetable_bp.route("/admin/student-timetable-requests", methods=["GET"])
@admin_required
def student_timetable_requests():
    # Fetch all pending requests
    pending_requests = qry("""
        SELECT * FROM student_timetable 
        WHERE status = 'pending' 
        ORDER BY created_at DESC
    """)
    
    # We will pass config options for the edit modal
    return render_template(
        "admin/student_timetable_requests.html",
        requests=pending_requests,
        DEPARTMENTS=DEPARTMENTS,
        SEMESTERS=SEMESTERS,
        DIVISIONS=DIVISIONS,
        DAYS=DAYS,
        PERIODS=PERIODS
    )

@student_timetable_bp.route("/admin/student-timetable-requests/approve/<int:id>", methods=["POST"])
@admin_required
def approve_request(id):
    try:
        # Check if request exists
        req = qone("SELECT id FROM student_timetable WHERE id = %s", (id,))
        if not req:
            return jsonify({"success": False, "message": "Request not found."}), 404
            
        exe("""
            UPDATE student_timetable 
            SET status = 'approved', approved_by_admin = TRUE 
            WHERE id = %s
        """, (id,))
        return jsonify({"success": True, "message": "Request approved successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@student_timetable_bp.route("/admin/student-timetable-requests/reject/<int:id>", methods=["POST"])
@admin_required
def reject_request(id):
    try:
        req = qone("SELECT id FROM student_timetable WHERE id = %s", (id,))
        if not req:
            return jsonify({"success": False, "message": "Request not found."}), 404
            
        exe("""
            UPDATE student_timetable 
            SET status = 'rejected', approved_by_admin = FALSE 
            WHERE id = %s
        """, (id,))
        return jsonify({"success": True, "message": "Request rejected successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@student_timetable_bp.route("/admin/student-timetable-requests/edit/<int:id>", methods=["POST"])
@admin_required
def edit_request(id):
    try:
        req = qone("SELECT id FROM student_timetable WHERE id = %s", (id,))
        if not req:
            return jsonify({"success": False, "message": "Request not found."}), 404
            
        division = request.form.get("division")
        semester = request.form.get("semester")
        department = request.form.get("department")
        day = request.form.get("day")
        time_slot = request.form.get("time_slot")
        subject = request.form.get("subject")
        room = request.form.get("room")
        
        if not (division and semester and department and day and time_slot and subject and room):
            return jsonify({"success": False, "message": "All fields are required."}), 400
            
        exe("""
            UPDATE student_timetable 
            SET division = %s, semester = %s, department = %s, day = %s, time_slot = %s, subject = %s, room = %s
            WHERE id = %s
        """, (division, semester, department, day, time_slot, subject, room, id))
        
        return jsonify({"success": True, "message": "Request updated successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@student_timetable_bp.route("/student/timetable", methods=["GET"])
@student_required
def view_student_timetable():
    student_id = session.get("student_id")
    division = session.get("student_division")
    department = session.get("student_branch")
    year = session.get("student_year")
    
    # Fallback to query student record from DB if session variables are empty
    if not (division and department and year):
        student = qone("SELECT division, department, year FROM students WHERE id = %s", (student_id,))
        if student:
            division = student["division"]
            department = student["department"]
            year = student["year"]
            # Save back to session
            session["student_division"] = division
            session["student_branch"] = department
            session["student_year"] = year

    # If still empty, apply defaults to avoid empty state issues
    if not division:
        division = "A"
    if not department:
        department = "AIDS"
    if not year:
        year = "I"

    # Map student year (I, II, III, IV) to semesters (odd and even)
    semesters_map = {
        "I": ["I", "II"],
        "II": ["III", "IV"],
        "III": ["V", "VI"],
        "IV": ["VII", "VIII"]
    }
    allowed_semesters = semesters_map.get(year, ["I", "II"])

    # Fetch approved student timetable entries matching the division, department, and semesters
    approved_slots = qry("""
        SELECT * FROM student_timetable 
        WHERE division = %s AND department = %s AND semester IN %s AND status = 'approved'
    """, (division, department, tuple(allowed_semesters)))
    
    # Structure the grid: DAYS (Monday - Saturday) x PERIODS (Period 1 - Period 8)
    grid = {period: {day: None for day in DAYS} for period in PERIODS}
    
    for slot in approved_slots:
        p = slot["time_slot"]
        d = slot["day"]
        # Populate if period and day match
        if p in grid and d in grid[p]:
            grid[p][d] = slot

    # For display subtitle
    display_semester = " & ".join(allowed_semesters)

    return render_template(
        "student/view_timetable.html",
        grid=grid,
        DAYS=DAYS,
        PERIODS=PERIODS,
        division=division,
        semester=display_semester,
        department=department
    )
