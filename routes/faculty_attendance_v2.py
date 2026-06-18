
from flask import Blueprint, render_template, request, redirect, session, jsonify, flash, send_file, url_for
from utils.db_helpers import safe_query, safe_fetch_one, safe_fetch_scalar, safe_execute, log_audit
from blueprints.auth.decorators import login_required

def normalize_branch(branch):
    if not branch: return ""
    return str(branch).strip()

def normalize_division(division):
    if not division: return ""
    return str(division).strip()
from datetime import datetime
import io
import logging
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

# Configure logger
logger = logging.getLogger(__name__)

faculty_att_bp = Blueprint('faculty_att', __name__)

# ─── ADMIN: SUBJECT-FACULTY ASSIGNMENT ───────────────────

@faculty_att_bp.route("/admin/faculty_assignments", methods=["GET", "POST"])
@login_required("admin")
def faculty_assignments():
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "assign":
            faculty_id = request.form.get("faculty_id")
            subject_name = request.form.get("subject_name")
            class_name = request.form.get("class_name")
            department = request.form.get("department")
            semester = request.form.get("semester")
            division = request.form.get("division")
            
            if not all([faculty_id, subject_name, class_name, department, semester, division]):
                flash("All fields are required for assignment.", "error")
            else:
                safe_execute("""
                    INSERT INTO faculty_subject_assignments 
                    (faculty_id, subject_name, class_name, department, semester, division)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (faculty_id, subject_name, class_name) 
                    DO UPDATE SET 
                        department = EXCLUDED.department,
                        semester = EXCLUDED.semester,
                        division = EXCLUDED.division
                """, (faculty_id, subject_name, class_name, department, semester, division))
                flash(f"Successfully assigned {subject_name} to class {class_name}", "success")
        
        elif action == "delete":
            assignment_id = request.form.get("id")
            safe_execute("DELETE FROM faculty_subject_assignments WHERE id = %s", (assignment_id,))
            flash("Assignment removed successfully", "info")
            
        return redirect(url_for('faculty_att.faculty_assignments'))

    # GET Request: Fetch data for the page
    assignments = safe_query("""
        SELECT a.*, f.name as faculty_name 
        FROM faculty_subject_assignments a 
        JOIN faculty f ON a.faculty_id = f.id 
        ORDER BY f.name, a.class_name
    """)
    
    faculty_list = safe_query("SELECT id, name, department FROM faculty ORDER BY name")
    subject_list = safe_query("SELECT DISTINCT name FROM subjects ORDER BY name")
    
    from config import DEPARTMENTS, SEMESTERS, DIVISIONS
    
    return render_template("admin/faculty_assignments.html", 
                         assignments=assignments, 
                         faculty_list=faculty_list, 
                         subject_list=subject_list,
                         DEPARTMENTS=DEPARTMENTS,
                         SEMESTERS=SEMESTERS,
                         DIVISIONS=DIVISIONS)


@faculty_att_bp.route("/admin/auto_link_faculty", methods=["POST"])
@login_required("admin")
def auto_link_faculty():
    # Run the timetable -> faculty_id update SQL
    safe_execute("""
        UPDATE timetable t
        SET faculty_id = f.id
        FROM faculty f
        WHERE t.faculty_id IS NULL
        AND TRIM(REPLACE(t.teacher, ' ', '')) ILIKE TRIM(REPLACE(f.name, ' ', ''))
    """)
    
    # Check fixed count
    fixed_count = safe_fetch_scalar("SELECT COUNT(*) FROM timetable WHERE faculty_id IS NOT NULL")
    
    # Run the timetable -> faculty_subject_assignments insert SQL
    # Get count before
    pre_count = safe_fetch_scalar("SELECT COUNT(*) FROM faculty_subject_assignments")
    
    safe_execute("""
        INSERT INTO faculty_subject_assignments (faculty_id, subject_name, class_name, department, semester, division)
        SELECT DISTINCT t.faculty_id, t.subject, (f.department || '-' || t.division) as class_name, f.department, t.semester, t.division
        FROM timetable t
        JOIN faculty f ON t.faculty_id = f.id
        WHERE t.faculty_id IS NOT NULL
        ON CONFLICT (faculty_id, subject_name, class_name) DO NOTHING
    """)
    
    # Get count after
    post_count = safe_fetch_scalar("SELECT COUNT(*) FROM faculty_subject_assignments")
    inserted_assignments = post_count - pre_count
    
    # Get unmatched teachers
    unmatched_rows = safe_query("SELECT DISTINCT teacher FROM timetable WHERE faculty_id IS NULL")
    unmatched = [r['teacher'] for r in unmatched_rows]
    
    flash(f"Timetable linking complete! Inserted {inserted_assignments} new subject assignments.", "success")
    return jsonify({
        "fixed_timetable_total": fixed_count,
        "inserted_assignments": inserted_assignments,
        "unmatched": unmatched
    })

@faculty_att_bp.route("/admin/fix_student_divisions", methods=["POST"])
@login_required("admin")
def fix_student_divisions():
    # Update students SET division using pattern from roll number if division is empty
    safe_execute("""
        UPDATE students 
        SET division = SUBSTRING(TRIM(roll) FROM 1 FOR 1) 
        WHERE (division IS NULL OR division = '') 
        AND roll IS NOT NULL 
        AND char_length(TRIM(roll)) > 0
    """)
    flash("Students divisions updated based on their roll numbers.", "success")
    return redirect("/students")



# ─── FACULTY: PORTAL & ATTENDANCE FLOW ───────────────────

@faculty_att_bp.route("/faculty/attendance_portal")
@login_required("faculty")
def attendance_portal():
    fid = session.get("faculty_id")
    # Assigned subjects
    my_assignments = safe_query("""
        SELECT * FROM faculty_subject_assignments 
        WHERE faculty_id = %s 
        ORDER BY class_name, subject_name
    """, (fid,))
    
    # Session stats per assignment
    enhanced_assignments = []
    for a in my_assignments:
        count = safe_fetch_scalar("""
            SELECT COUNT(*) FROM attendance_sessions 
            WHERE faculty_id = %s AND subject = %s AND division = %s
        """, (fid, a['subject_name'], a['division']))
        a_dict = dict(a)
        a_dict['session_count'] = count
    # Recent sessions
    recent_sessions = safe_query("""
        SELECT * FROM attendance_sessions 
        WHERE faculty_id = %s 
        ORDER BY lecture_date DESC, created_at DESC 
        LIMIT 10
    """, (fid,))
    
    # Today's schedule from Master Timetable
    from datetime import datetime
    today_name = datetime.now().strftime("%A")
    faculty_name = session.get("name")
    
    # ─── SELF-HEALING LOGIC ───
    # We use a robust query with TRIM and similarity handles for name mismatches
    # Fallback to 0.3 similarity if exact trim match fails
    today_schedule = safe_query("""
        SELECT t.*, s.status as attendance_status, s.id as session_id
        FROM timetable t
        LEFT JOIN attendance_sessions s ON t.id = s.timetable_id AND s.lecture_date = CURRENT_DATE
        WHERE (
            t.faculty_id = %s 
            OR TRIM(REPLACE(t.teacher, ' ', '')) ILIKE TRIM(REPLACE(%s, ' ', ''))
            OR (SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='pg_trgm') AND similarity(t.teacher, %s::text) > 0.4)
        ) 
        AND t.day = %s
        ORDER BY t.start_time
    """, (fid, faculty_name, faculty_name, today_name))

    # Auto-insert missing assignments to bridge the data gap automatically
    for slot in today_schedule:
        # Check if assignment exists
        exists = safe_fetch_one("""
            SELECT id FROM faculty_subject_assignments 
            WHERE faculty_id = %s AND subject_name = %s AND division = %s
        """, (fid, slot['subject'], slot['division']))
        
        if not exists:
            safe_execute("""
                INSERT INTO faculty_subject_assignments (faculty_id, subject_name, class_name, department, semester, division)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (fid, slot['subject'], f"{slot['branch']}-{slot['division']}", slot['branch'], slot['semester'], slot['division']))
            # Refresh assignments if we added a new one
            my_assignments = safe_query("SELECT * FROM faculty_subject_assignments WHERE faculty_id = %s ORDER BY class_name, subject_name", (fid,))

    # Session stats per assignment (Recalculate after auto-insert)
    enhanced_assignments = []
    for a in my_assignments:
        count = safe_fetch_scalar("""
            SELECT COUNT(*) FROM attendance_sessions 
            WHERE faculty_id = %s AND subject = %s AND division = %s
        """, (fid, a['subject_name'], a['division']))
        a_dict = dict(a)
        a_dict['session_count'] = count
        enhanced_assignments.append(a_dict)
    
    return render_template("faculty/attendance_portal.html", 
                         assignments=enhanced_assignments, 
                         recent_sessions=recent_sessions,
                         today_schedule=today_schedule,
                         today_date=datetime.now().strftime("%Y-%m-%d"))

@faculty_att_bp.route("/faculty/create_session_from_slot/<int:slot_id>")
@login_required("faculty")
def create_session_from_slot(slot_id):
    fid = session.get("faculty_id")
    # Fetch slot details
    slot = safe_fetch_one("SELECT * FROM timetable WHERE id = %s", (slot_id,))
    if not slot:
        flash("Timetable slot not found", "error")
        return redirect(url_for('faculty_att.attendance_portal'))
        
    # Check if a session already exists for today
    today = datetime.now().strftime("%Y-%m-%d")
    existing = safe_fetch_one("""
        SELECT id FROM attendance_sessions 
        WHERE timetable_id = %s AND lecture_date = %s
    """, (slot_id, today))
    
    if existing:
        return redirect(url_for('faculty_att.marking_session', session_id=existing['id']))
        
    # Create new session
    # Note: Using slot data for branch/division
    session_id = safe_fetch_scalar("""
        INSERT INTO attendance_sessions 
        (faculty_id, subject, lecture_date, lecture_type, time_slot, timetable_id, division, branch, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'draft')
        RETURNING id
    """, (fid, slot['subject'], today, slot['slot_type'] or 'Theory', slot['time'], slot_id, slot['division'], slot['branch'],))
    
    return redirect(url_for('faculty_att.marking_session', session_id=session_id))

@faculty_att_bp.route("/faculty/create_session", methods=["POST"])
@login_required("faculty")
def create_session():
    fid = session.get("faculty_id")
    subject = request.form.get("subject")
    lecture_date = request.form.get("lecture_date") or datetime.now().strftime("%Y-%m-%d")
    lecture_type = request.form.get("lecture_type", "Theory")
    time_slot = request.form.get("time_slot", "")
    timetable_id = request.form.get("timetable_id")
    
    div = request.form.get("division")
    branch = request.form.get("department")
    
    if timetable_id:
        # Use timetable slot as reference
        tt = safe_fetch_one("SELECT * FROM timetable WHERE id = %s", (timetable_id,))
        if tt:
            div = tt['division']
            branch = tt['branch']
            subject = tt['subject'] # Ensure subject matches timetable
    
    if not div:
        flash("Could not determine class or division for this session", "error")
        return redirect(url_for('faculty_att.attendance_portal'))

    # If manual creation (no timetable_id), validate against weekly timetable
    if not timetable_id:
        try:
            dt = datetime.strptime(lecture_date, "%Y-%m-%d")
            day_of_week = dt.strftime("%A")
        except Exception:
            flash("Invalid lecture date format.", "error")
            return redirect(url_for('faculty_att.attendance_portal'))

        valid_slot = safe_fetch_one("""
            SELECT id FROM timetable 
            WHERE day = %s 
            AND TRIM(REPLACE(subject, ' ', '')) ILIKE TRIM(REPLACE(%s, ' ', ''))
            AND division = %s 
            AND (branch IS NULL OR %s IS NULL OR branch = '' OR %s = '' OR branch = %s)
            AND faculty_id = %s
        """, (day_of_week, subject, div, branch, branch, branch, fid))
        
        if not valid_slot:
            flash("Error: No matching slot found in the weekly timetable for this subject, division, and day.", "error")
            return redirect(url_for('faculty_att.attendance_portal'))
        
        timetable_id = valid_slot['id']

    # Prevent duplicate sessions (same subject + division + date)
    existing = safe_fetch_one("""
        SELECT id FROM attendance_sessions 
        WHERE subject = %s AND division = %s AND lecture_date = %s
    """, (subject, div, lecture_date))
    
    if existing:
        flash("Session already exists for this subject, division, and date.", "info")
        return redirect(url_for('faculty_att.marking_session', session_id=existing['id']))
    
    # Create new session
    session_id = safe_fetch_scalar("""
        INSERT INTO attendance_sessions (faculty_id, subject, division, branch, lecture_date, lecture_type, time_slot, status, timetable_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'draft', %s)
        RETURNING id
    """, (fid, subject, div, branch, lecture_date, lecture_type, time_slot, timetable_id))
    
    log_audit(fid, 'CREATED', f"Created attendance session ID {session_id} for {subject}")
    
    return redirect(url_for('faculty_att.marking_session', session_id=session_id))

@faculty_att_bp.route("/faculty/new_session", methods=["GET", "POST"])
@login_required("faculty")
def new_session():
    fid = session.get("faculty_id")
    subject = request.values.get("subject")
    division = request.values.get("division")
    
    if not subject or not division:
        flash("Subject and Division are required for manual marking.", "error")
        return redirect(url_for('faculty_att.attendance_portal'))
        
    # Verify faculty assignment
    assignment = safe_fetch_one("""
        SELECT * FROM faculty_subject_assignments 
        WHERE faculty_id = %s AND subject_name = %s AND division = %s
    """, (fid, subject, division))
    
    if not assignment:
        flash("Error: You are not assigned to this subject and division.", "error")
        return redirect(url_for('faculty_att.attendance_portal'))

    today = datetime.now().strftime("%Y-%m-%d")
    day_of_week = datetime.now().strftime("%A")
    branch = assignment.get('department')

    valid_slot = safe_fetch_one("""
        SELECT id FROM timetable 
        WHERE day = %s 
        AND TRIM(REPLACE(subject, ' ', '')) ILIKE TRIM(REPLACE(%s, ' ', ''))
        AND division = %s 
        AND (branch IS NULL OR %s IS NULL OR branch = '' OR %s = '' OR branch = %s)
        AND faculty_id = %s
    """, (day_of_week, subject, division, branch, branch, branch, fid))
    
    if not valid_slot:
        flash("Error: No matching slot found in the weekly timetable for today.", "error")
        return redirect(url_for('faculty_att.attendance_portal'))
        
    # Prevent duplicate sessions (same subject + division + date)
    existing = safe_fetch_one("""
        SELECT id FROM attendance_sessions 
        WHERE subject = %s AND division = %s AND lecture_date = %s
    """, (subject, division, today))
    
    if existing:
        return redirect(url_for('faculty_att.marking_session', session_id=existing['id']))
        
    # Create new manual session
    session_id = safe_fetch_scalar("""
        INSERT INTO attendance_sessions (faculty_id, subject, division, branch, lecture_date, status, timetable_id)
        VALUES (%s, %s, %s, %s, %s, 'draft', %s)
        RETURNING id
    """, (fid, subject, division, branch, today, valid_slot['id']))
    
    if session_id:
        log_audit(fid, 'MANUAL_SESSION_CREATED', f"Created manual session {session_id} for {subject} ({division})")
        return redirect(url_for('faculty_att.marking_session', session_id=session_id))
    else:
        flash("Critical Error: Failed to initialize attendance session.", "error")
        return redirect(url_for('faculty_att.attendance_portal'))


@faculty_att_bp.route("/faculty/marking_session/<int:session_id>")
@login_required("faculty")
def marking_session(session_id):
    fid = session.get("faculty_id")
    sess = safe_fetch_one("SELECT * FROM attendance_sessions WHERE id = %s", (session_id,))
    
    if not sess or sess['faculty_id'] != fid:
        flash("Unauthorized or session not found", "error")
        return redirect(url_for('faculty_att.attendance_portal'))
    
    # --- RESILIENT STUDENT FETCH ---
    norm_branch = normalize_branch(sess.get('branch'))
    norm_div = normalize_division(sess.get('division'))
            
    logger.info(f"Marking session {session_id}: Original=(Branch '{sess['branch']}', Div '{sess['division']}') -> Normalized=(Branch '{norm_branch}', Div '{norm_div}')")
    
    # Try exact match with normalized strings
    students = safe_query("""
        SELECT id, name, roll, prn 
        FROM students 
        WHERE TRIM(UPPER(division)) = TRIM(UPPER(%s)) 
        AND TRIM(UPPER(department)) = TRIM(UPPER(%s)) 
        ORDER BY roll, name
    """, (norm_div, norm_branch))
    
    # Fallback 1: Division & partial branch
    if not students:
        logger.warning(f"ZERO STUDENTS found for exact match. Trying fuzzy match.")
        students = safe_query("""
            SELECT id, name, roll, prn 
            FROM students 
            WHERE TRIM(UPPER(division)) = TRIM(UPPER(%s))
            AND (TRIM(UPPER(department)) ILIKE '%%' || TRIM(UPPER(%s)) || '%%' OR TRIM(UPPER(%s)) ILIKE '%%' || TRIM(UPPER(department)) || '%%')
            ORDER BY roll, name
        """, (norm_div, norm_branch, norm_branch))
        
    # Fallback 2: Division only
    if not students:
        logger.warning(f"ZERO STUDENTS found for partial match. Falling back to division-only.")
        students = safe_query("""
            SELECT id, name, roll, prn 
            FROM students 
            WHERE TRIM(UPPER(division)) = TRIM(UPPER(%s))
            ORDER BY roll, name
        """, (norm_div,))
        
        if not students:
            logger.error(f"CRITICAL: No students found even after division-only fallback for normalized division '{norm_div}'.")
        else:
            logger.info(f"Fallback successful: Found {len(students)} students in division '{norm_div}'.")
    
    # Fetch existing markings
    marks = safe_query("SELECT student_id, status FROM attendance WHERE lecture_id = %s", (session_id,))
    mark_map = {m['student_id']: m['status'] for m in marks}

    # Allow editing submitted sessions within 24 hours only
    from datetime import timedelta
    can_edit_submitted = False
    if sess['status'] == 'submitted':
        time_ref = sess.get('updated_at') or sess.get('created_at')
        if time_ref and (datetime.now() - time_ref) <= timedelta(hours=24):
            can_edit_submitted = True
    
    return render_template("faculty/marking_session.html", 
                         sess=sess, 
                         students=students, 
                         mark_map=mark_map,
                         can_edit_submitted=can_edit_submitted)

@faculty_att_bp.route("/faculty/api/save_attendance", methods=["POST"])
@login_required("faculty")
def api_save_attendance():
    data = request.get_json()
    session_id = data.get("session_id")
    markings = data.get("markings", {}) # student_id -> status
    fid = session.get("faculty_id")
    
    sess = safe_fetch_one("SELECT * FROM attendance_sessions WHERE id = %s", (session_id,))
    if not sess or sess['faculty_id'] != fid:
        return jsonify({"ok": False, "error": "Unauthorized"}), 403

    # Allow editing submitted session within 24 hours only
    from datetime import timedelta
    can_edit = False
    if sess['status'] == 'draft':
        can_edit = True
    elif sess['status'] == 'submitted':
        time_ref = sess.get('updated_at') or sess.get('created_at')
        if time_ref and (datetime.now() - time_ref) <= timedelta(hours=24):
            can_edit = True

    if not can_edit:
        return jsonify({"ok": False, "error": "This session is locked and cannot be edited anymore (24-hour window passed)."}), 403
    
    for sid, status in markings.items():
        # Get old status for audit
        old = safe_fetch_one("SELECT status FROM attendance WHERE lecture_id = %s AND student_id = %s", (session_id, sid))
        old_status = old['status'] if old else None
        
        if old_status != status:
            safe_execute("""
                INSERT INTO attendance (student_id, student_name, subject, date, status, faculty_id, lecture_id, branch, division)
                SELECT %s, name, %s, %s, %s, %s, %s, %s, %s FROM students WHERE id = %s
                ON CONFLICT (student_id, lecture_id) DO UPDATE SET status = EXCLUDED.status, updated_at = CURRENT_TIMESTAMP
            """, (sid, sess['subject'], sess['lecture_date'], status, fid, session_id, sess['branch'], sess['division'], sid))
            
            # Specific audit log
            safe_execute("""
                INSERT INTO attendance_audit (faculty_id, session_id, student_id, action, prev_status, new_status)
                VALUES (%s, %s, %s, 'STATUS_CHANGE', %s, %s)
            """, (fid, session_id, sid, old_status, status))
            
    # Update session updated_at
    safe_execute("UPDATE attendance_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = %s", (session_id,))
    
    return jsonify({"ok": True})

@faculty_att_bp.route("/faculty/submit_session", methods=["POST"])
@login_required("faculty")
def submit_session():
    session_id = request.form.get("session_id")
    fid = session.get("faculty_id")
    
    sess = safe_fetch_one("SELECT * FROM attendance_sessions WHERE id = %s", (session_id,))
    if not sess or sess['faculty_id'] != fid:
        return "Unauthorized", 403
        
    safe_execute("UPDATE attendance_sessions SET status = 'submitted', updated_at = CURRENT_TIMESTAMP, is_locked = TRUE WHERE id = %s", (session_id,))
    log_audit(fid, 'SUBMITTED', f"Submitted session {session_id}")
    
    # Trigger background tasks
    from tasks.attendance_tasks import process_submitted_attendance
    process_submitted_attendance.delay(session_id)
    
    flash("Attendance submitted and locked successfully", "success")
    return redirect(url_for('faculty_att.attendance_portal'))

@faculty_att_bp.route("/faculty/session_history")
@login_required("faculty")
def session_history():
    fid = session.get("faculty_id")
    subject = request.args.get("subject", "").strip()
    class_name = request.args.get("class", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    
    sql = "SELECT * FROM attendance_sessions WHERE faculty_id = %s"
    params = [fid]
    
    if subject: sql += " AND subject = %s"; params.append(subject)
    if class_name: sql += " AND division = %s"; params.append(class_name)
    if start_date: sql += " AND lecture_date >= %s"; params.append(start_date)
    if end_date: sql += " AND lecture_date <= %s"; params.append(end_date)
    
    sql += " ORDER BY lecture_date DESC"
    sessions = safe_query(sql, params)
    
    # Calculate attendance % for each session
    enhanced = []
    for s in sessions:
        total = safe_fetch_scalar("SELECT COUNT(*) FROM attendance WHERE lecture_id = %s", (s['id'],))
        present = safe_fetch_scalar("SELECT COUNT(*) FROM attendance WHERE lecture_id = %s AND status = 'Present'", (s['id'],))
        s_dict = dict(s)
        s_dict['attendance_pct'] = round(present/total*100, 1) if total > 0 else 0
        s_dict['total_students'] = total
        s_dict['present_students'] = present
        enhanced.append(s_dict)
        
    my_subjects = safe_query("SELECT DISTINCT subject_name FROM faculty_subject_assignments WHERE faculty_id = %s", (fid,))
    
    return render_template("faculty/session_history.html", sessions=enhanced, subjects=my_subjects)

@faculty_att_bp.route("/faculty/export_session/<int:session_id>")
@login_required("faculty")
def export_session(session_id):
    fid = session.get("faculty_id")
    sess = safe_fetch_one("SELECT * FROM attendance_sessions WHERE id = %s", (session_id,))
    if not sess or sess['faculty_id'] != fid:
        return "Unauthorized", 403
        
    records = safe_query("""
        SELECT s.name, s.roll, s.prn, a.status 
        FROM attendance a 
        JOIN students s ON a.student_id = s.id 
        WHERE a.lecture_id = %s 
        ORDER BY s.roll, s.name
    """, (session_id,))
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance"
    
    ws.append([f"Attendance Report: {sess['subject']} ({sess['lecture_type']})"])
    ws.append([f"Date: {sess['lecture_date']}", f"Class: {sess['branch']} {sess['division']}"])
    ws.append([]) # Blank
    
    headers = ["Roll No", "PRN", "Student Name", "Status"]
    ws.append(headers)
    for cell in ws[4]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="E5E7EB")
        
    for r in records:
        ws.append([r['roll'], r['prn'], r['name'], r['status']])
        
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    
    filename = f"Attendance_{sess['subject']}_{sess['lecture_date']}.xlsx"
    return send_file(buf, as_attachment=True, download_name=filename, 
                   mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@faculty_att_bp.route("/faculty/my_students")
@login_required("faculty")
def my_students():
    fid = session.get("faculty_id")
    # Get all students in classes assigned to this faculty
    students = safe_query("""
        SELECT DISTINCT s.id, s.name, s.roll, s.prn, s.department, s.division, s.year
        FROM students s
        JOIN faculty_subject_assignments a ON s.division = a.division AND s.department = a.department
        WHERE a.faculty_id = %s
        ORDER BY s.division, s.roll
    """, (fid,))
    
    # Calculate attendance % across all subjects taught by this faculty for each student
    enhanced = []
    for s in students:
        stats = safe_fetch_one("""
            SELECT COUNT(*) as total, 
                   SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present
            FROM attendance
            WHERE student_id = %s AND faculty_id = %s
        """, (s['id'], fid))
        s_dict = dict(s)
        s_dict['attendance_pct'] = round(stats['present']/stats['total']*100, 1) if stats['total'] > 0 else 0
        enhanced.append(s_dict)
        
    return render_template("faculty/my_students.html", students=enhanced)

@faculty_att_bp.route("/faculty/student_report/<int:student_id>")
@login_required("faculty")
def faculty_student_report(student_id):
    fid = session.get("faculty_id")
    student = safe_fetch_one("SELECT * FROM students WHERE id = %s", (student_id,))
    
    # Subject breakdown directly from attendance table
    subjects_data_raw = safe_query("""
        SELECT subject, 
             COUNT(*) as total,
             COUNT(*) FILTER (WHERE status='Present') as present,
             COUNT(*) FILTER (WHERE status='Absent') as absent,
             COUNT(*) FILTER (WHERE status='Leave') as leave,
             ROUND(COUNT(*) FILTER (WHERE status='Present') * 100.0 / NULLIF(COUNT(*),0), 1) as percentage
        FROM attendance 
        WHERE student_id = %s AND faculty_id = %s
        GROUP BY subject
    """, (student_id, fid))
    
    subjects_data = []
    total_sessions = 0
    total_present = 0
    total_absent = 0
    total_leave = 0
    
    for row in subjects_data_raw:
        total_sessions += row['total']
        total_present += row['present']
        total_absent += row['absent']
        total_leave += row['leave']
        row_dict = dict(row)
        row_dict['percentage'] = float(row['percentage']) if row['percentage'] is not None else 0.0
        subjects_data.append(row_dict)
        
    overall_pct = round((total_present / total_sessions * 100.0), 1) if total_sessions > 0 else 0.0
    
    if total_sessions == 0:
        grade = "no_data"
    elif overall_pct >= 75:
        grade = "good"
    elif overall_pct >= 60:
        grade = "warning"
    else:
        grade = "defaulter"
        
    recent_history = safe_query("""
        SELECT date, subject, status 
        FROM attendance 
        WHERE student_id = %s AND faculty_id = %s
        ORDER BY date DESC, id DESC LIMIT 10
    """, (student_id, fid))

    return render_template("faculty/student_report.html", 
        student=student, 
        subjects_data=subjects_data, 
        overall_pct=overall_pct, 
        total_sessions=total_sessions,
        total_present=total_present, 
        total_absent=total_absent,
        total_leave=total_leave,
        grade=grade,
        history=recent_history
    )
