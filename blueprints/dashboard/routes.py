from flask import render_template, session, redirect, url_for
from blueprints.dashboard import dashboard_bp
from blueprints.auth.decorators import login_required, student_required, faculty_required
from services.student_service import StudentService
from services.faculty_service import FacultyService
from services.attendance_service import AttendanceService

from datetime import datetime
from utils.pg_wrapper import qry, qone
from config import Config

student_service = StudentService()
faculty_service = FacultyService()
attendance_service = AttendanceService()

@dashboard_bp.route("/student_dashboard")
@student_required
def student():
    student_id = session.get("student_id")
    student = qone("SELECT * FROM students WHERE id=%s", (student_id,))
    if not student:
        return redirect(url_for('auth.logout'))
        
    # Cumulative attendance
    has_summary = qone("SELECT COUNT(*) as count FROM attendance_summary WHERE student_id=%s", (student_id,))['count'] > 0
    if has_summary:
        rows = qry("SELECT attended, total FROM attendance_summary WHERE student_id=%s", (student_id,))
        present = sum(r["attended"] for r in rows)
        total = sum(r["total"] for r in rows)
    else:
        rows = qry("SELECT status FROM attendance WHERE student_id=%s", (student_id,))
        total = len(rows)
        present = sum(1 for r in rows if r["status"] == "Present")
        
    cum_att_total = total
    cum_att_present = present
    cum_att_percentage = round(present / total * 100, 1) if total > 0 else 0
    
    if cum_att_percentage >= 75:
        cum_att_status = "Good"
    elif cum_att_percentage >= 50:
        cum_att_status = "Average"
    else:
        cum_att_status = "Low"
        
    # Timetable
    timetable = qry("""
        SELECT * FROM timetable 
        WHERE division=%s AND branch=%s AND year=%s 
        ORDER BY CASE day 
            WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 
            WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 
        END, time 
        LIMIT 10
    """, (student["division"], student["department"], student["year"]))
    
    # Notices
    admin_notifs = qry("""
        SELECT title, message, created_at, 'Admin' as faculty_name, attachment_path, attachment_name
        FROM notifications 
        WHERE role_target='student' or role_target='all' 
        ORDER BY id DESC LIMIT 5
    """)
    faculty_notifs = qry("""
        SELECT fn.title, fn.message, fn.created_at, f.name as faculty_name, NULL as attachment_path, NULL as attachment_name
        FROM faculty_notices fn JOIN faculty f ON fn.faculty_id=f.id
        ORDER BY fn.id DESC LIMIT 5
    """)
    
    combined_notices = []
    for r in admin_notifs:
        d = dict(r)
        if d.get("created_at"): d["created_at"] = str(d["created_at"])
        combined_notices.append(d)
    for r in faculty_notifs:
        d = dict(r)
        if d.get("created_at"): d["created_at"] = str(d["created_at"])
        combined_notices.append(d)
        
    combined_notices.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    notices = combined_notices[:5]
    
    today_name = datetime.now().strftime("%A")
    
    return render_template(
        "student/student_dashboard.html",
        cum_att_total=cum_att_total,
        cum_att_present=cum_att_present,
        cum_att_percentage=cum_att_percentage,
        cum_att_status=cum_att_status,
        timetable=[dict(t) for t in timetable],
        notices=[dict(n) for n in notices],
        today_name=today_name
    )

@dashboard_bp.route("/faculty_dashboard")
@faculty_required
def faculty():
    fid = session.get("faculty_id")
    _tt_name = session.get('name', '')
    
    profile = qone("SELECT * FROM faculty WHERE id=%s", (fid,))
    if profile is None:
        profile = {"name": session.get("name", "Faculty"), "department": "-", "designation": "-"}
    else:
        profile = dict(profile)
        
    DAY_ORD = Config.DAY_ORD
    # Fetch faculty specific timetable
    my_timetable = qry(
        f"SELECT * FROM timetable WHERE faculty_id=%s ORDER BY {DAY_ORD}, start_time",
        (fid,)
    )
    if not my_timetable:
        my_timetable = qry(f"SELECT * FROM timetable WHERE teacher LIKE %s ORDER BY {DAY_ORD}, time", (f"%{_tt_name}%",))
        if not my_timetable:
            _tt_parts = [p for p in _tt_name.replace("Prof.","").replace("Dr.","").strip().split() if len(p) > 3]
            for _part in _tt_parts:
                my_timetable = qry(f"SELECT * FROM timetable WHERE teacher LIKE %s ORDER BY {DAY_ORD}, time", (f"%{_part}%",))
                if my_timetable:
                    break

    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Fetch stats
    row_today_sessions = qone("SELECT COUNT(*) as count FROM attendance_sessions WHERE faculty_id=%s AND lecture_date=%s", (fid, today_str))
    today_sessions = row_today_sessions['count'] if row_today_sessions else 0
    
    row_pending_drafts = qone("SELECT COUNT(*) as count FROM attendance_sessions WHERE faculty_id=%s AND status='draft'", (fid,))
    pending_drafts = row_pending_drafts['count'] if row_pending_drafts else 0
    
    # Low attendance count (<75%)
    row_low_att = qone("""
        WITH student_stats AS (
            SELECT student_id, 
                   COUNT(*) as total, 
                   SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present
            FROM attendance
            WHERE faculty_id = %s
            GROUP BY student_id
        )
        SELECT COUNT(*) as count FROM student_stats WHERE total > 0 AND (present * 100.0 / total) < 75
    """, (fid,))
    low_att_count = row_low_att['count'] if row_low_att else 0
    
    # Study materials count
    row_notes = qone("SELECT COUNT(*) as count FROM faculty_notes WHERE faculty_id=%s", (fid,))
    notes_count = row_notes['count'] if row_notes else 0
    
    day_name = datetime.now().strftime("%A")
    
    # Find classes from timetable for today (including Substitutions)
    today_classes = qry("""
        SELECT t.* FROM timetable t 
        WHERE (t.faculty_id = %s OR t.id IN (
            SELECT timetable_id FROM timetable_substitutions 
            WHERE substitute_faculty_id = %s AND session_date = %s
        )) 
        AND t.day = %s AND t.published = TRUE
    """, (fid, fid, today_str, day_name))
    
    if not today_classes:
        today_classes = qry("""
            SELECT * FROM timetable 
            WHERE teacher LIKE %s AND day = %s AND published = TRUE
        """, (f"%{_tt_name}%", day_name))
    
    today_actions = []
    for tc in (today_classes or []):
        row_marked = qone("""
            SELECT COUNT(*) as count FROM attendance_sessions 
            WHERE faculty_id = %s AND subject = %s AND lecture_date = %s
        """, (fid, tc.get('subject', ''), today_str))
        marked = row_marked['count'] if row_marked else 0
        if marked == 0:
            today_actions.append(tc)

    # Legacy counts for chart/dashboard compatibility
    row_att_count = qone("SELECT COUNT(*) as count FROM attendance WHERE faculty_id=%s", (fid,))
    att_count = row_att_count['count'] if row_att_count else 0
    
    # Recent notices
    recent_notices = qry("SELECT * FROM faculty_notices WHERE faculty_id=%s ORDER BY id DESC LIMIT 5", (fid,))

    return render_template(
        "faculty/faculty_dashboard.html",
        profile=profile,
        my_timetable=[dict(e) for e in my_timetable],
        today_sessions=today_sessions,
        pending_drafts=pending_drafts,
        low_att_count=low_att_count,
        notes_count=notes_count,
        today_actions=[dict(e) for e in today_actions],
        att_count=att_count,
        recent_notices=[dict(e) for e in recent_notices]
    )
