from flask import current_app, session
from datetime import datetime
import json
import os
import math
from models.attendance_model import (
    ensure_attendance_engine_schema,
    log_attendance_action,
    create_attendance_backup,
    latest_attendance_backup,
    load_attendance_backup,
    export_attendance_snapshot,
)
from models.attendance import ensure_attendance_upload_tables
from utils.pg_wrapper import qry, qone, exe, get_db, qry_read
from utils.cache import cache_result
from datetime import timedelta

ATTENDANCE_LOCK_HOURS = int(os.environ.get("ATTENDANCE_LOCK_HOURS", "24"))

def is_attendance_locked(session_id):
    if not session_id: return False
    row = qone("SELECT locked_at, lecture_date FROM attendance_sessions WHERE id=%s", (session_id,))
    if not row:
        return True  # session not found = locked by default
    if row.get("locked_at") or row.get("is_locked"):
        return True  # already explicitly locked
        
    # Auto-lock after ATTENDANCE_LOCK_HOURS since lecture date
    lecture_dt = row["lecture_date"]
    if isinstance(lecture_dt, str):
        try:
            lecture_dt = datetime.strptime(lecture_dt, "%Y-%m-%d")
        except:
            return True # Parse error = safe lock
    
    # Combined with min time (00:00:00) as per request
    cutoff = datetime.combine(lecture_dt, datetime.min.time()) + timedelta(hours=ATTENDANCE_LOCK_HOURS)
    return datetime.now() > cutoff

def init_attendance_engine():
    """Initializes schema and tables for both attendance systems."""
    ensure_attendance_engine_schema()
    ensure_attendance_upload_tables()

def attendance_page_context(role="admin", actor_id=None, actor_name="", **kwargs):
    """Returns data needed for attendance-related UI pages."""
    # Capture common aliases for actor_id
    if not actor_id and "faculty_id" in kwargs:
        actor_id = kwargs["faculty_id"]
    if not actor_id and "student_id" in kwargs:
        actor_id = kwargs["student_id"]
        
    from config import DEPARTMENTS, DIVISIONS, SEMESTERS, YEARS
    from datetime import datetime
    
    # 1. Fetch Students
    all_students = qry("SELECT id, name, roll, division, department FROM students ORDER BY name")
    
    # 2. Fetch Subjects
    # Global subjects list
    global_subjects = [r["subject"] for r in qry("SELECT DISTINCT subject FROM attendance ORDER BY subject") if r["subject"]]
    
    # Actor-specific subjects (especially for faculty)
    my_subjects = []
    if role == "faculty" and actor_name:
        # Try to find subjects assigned to this faculty in the subjects table
        assign_rows = qry("SELECT name FROM subjects WHERE teacher LIKE %s", (f"%{actor_name}%",))
        my_subjects = [{"name": r["name"]} for r in assign_rows]
        
        # If no explicit assignments, check history
        if not my_subjects:
            hist_rows = qry("SELECT DISTINCT subject FROM attendance WHERE faculty_id = %s", (actor_id,))
            my_subjects = [{"name": r["subject"]} for r in hist_rows if r["subject"]]
    else:
        my_subjects = [{"name": s} for s in global_subjects]
    
    return {
        "students": all_students,
        "all_students": all_students,
        "subjects": global_subjects,
        "my_subjects": my_subjects,
        "divs": DIVISIONS,
        "DEPARTMENTS": DEPARTMENTS,
        "DIVISIONS": DIVISIONS,
        "SEMESTERS": SEMESTERS,
        "YEARS": YEARS,
        "today": datetime.now().strftime("%Y-%m-%d")
    }

def get_students_for_filters(dept=None, division=None, search=None):
    """Fetches students matching department, division, and search string."""
    sql = "SELECT id, name, roll, prn, department, division, year FROM students WHERE 1=1"
    params = []
    if dept:
        sql += " AND department = %s"
        params.append(dept)
    if division:
        sql += " AND division = %s"
        params.append(division)
    if search:
        sql += " AND (name ILIKE %s OR roll ILIKE %s OR prn ILIKE %s)"
        params.append(f"%{search}%")
        params.append(f"%{search}%")
        params.append(f"%{search}%")
    sql += " ORDER BY name ASC LIMIT 100"
    return qry(sql, params)

def mark_single_attendance(role, actor_id, form_data, actor_name=""):
    """Marks attendance for a single student in a specific session."""
    try:
        student_id = form_data.get("student_id")
        subject = form_data.get("subject")
        lecture_date = form_data.get("date") or datetime.now().strftime("%Y-%m-%d")
        status = form_data.get("status", "Present")
        
        # Check if session exists or create one
        session_row = qone(
            "SELECT id FROM attendance_sessions WHERE subject=%s AND lecture_date=%s AND faculty_id=%s",
            (subject, lecture_date, actor_id if role == "faculty" else None)
        )
        lecture_id = session_row["id"] if session_row else None
        
        if not lecture_id:
            # Simple session creation
            cur = exe(
                "INSERT INTO attendance_sessions (subject, lecture_date, faculty_id, created_role, created_by) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (subject, lecture_date, actor_id if role == "faculty" else None, role, actor_id)
            )
            lecture_id = cur.fetchone()["id"]

        exe(
            """INSERT INTO attendance (student_id, date, subject, status, lecture_id, faculty_id) 
               VALUES (%s,%s,%s,%s,%s,%s)
               ON CONFLICT (student_id, lecture_id) DO UPDATE SET status = EXCLUDED.status""",
            (student_id, lecture_date, subject, status, lecture_id, actor_id if role == "faculty" else None)
        )
        
        log_attendance_action(role, actor_id, "mark_single", {"student_id": student_id, "status": status})
        
        # UPSERT into attendance_summary
        exe("""
            INSERT INTO attendance_summary 
              (student_id, student_name, subject, attended, total, 
               division, semester, department)
            SELECT 
              student_id,
              student_name,
              subject,
              COUNT(*) FILTER (WHERE status='Present') as attended,
              COUNT(*) as total,
              division,
              semester,
              (SELECT department FROM students WHERE id=student_id) as department
            FROM attendance
            WHERE student_id = %s AND subject = %s
            GROUP BY student_id, student_name, subject, division, semester
            ON CONFLICT (student_id, subject) DO UPDATE SET
              attended = EXCLUDED.attended,
              total = EXCLUDED.total
        """, (student_id, subject))
        
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def mark_bulk_attendance(role, actor_id, form_data, actor_name=""):
    """Marks attendance for multiple students for a session."""
    try:
        subject = form_data.get("subject")
        lecture_date = form_data.get("date") or datetime.now().strftime("%Y-%m-%d")
        division = form_data.get("division", "")
        branch = form_data.get("branch", "")
        
        # Create/Get session
        cur = exe(
            """INSERT INTO attendance_sessions (subject, lecture_date, division, branch, faculty_id, created_role, created_by)
               VALUES (%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (subject, division, branch, lecture_date, faculty_id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
               RETURNING id""",
            (subject, lecture_date, division, branch, actor_id if role == "faculty" else None, role, actor_id)
        )
        lecture_id = cur.fetchone()["id"]

        # Parse student statuses from form
        saved = 0
        updated = 0
        for key, value in form_data.items():
            if key.startswith("status_"):
                sid = key.replace("status_", "")
                status = value
                res = exe(
                    """INSERT INTO attendance (student_id, date, subject, status, lecture_id, faculty_id, division, branch) 
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (student_id, lecture_id) DO UPDATE SET status = EXCLUDED.status, updated_at = CURRENT_TIMESTAMP
                       RETURNING (xmax = 0) AS is_insert""",
                    (sid, lecture_date, subject, status, lecture_id, actor_id if role == "faculty" else None, division, branch)
                )
                if res.fetchone()["is_insert"]:
                    saved += 1
                else:
                    updated += 1

        log_attendance_action(role, actor_id, "mark_bulk", {"lecture_id": lecture_id, "count": saved + updated})
        
        # Batch UPSERT into attendance_summary 
        for key, value in form_data.items():
            if key.startswith("status_"):
                sid = key.replace("status_", "")
                exe("""
                    INSERT INTO attendance_summary 
                      (student_id, student_name, subject, attended, total, 
                       division, semester, department)
                    SELECT 
                      student_id,
                      student_name,
                      subject,
                      COUNT(*) FILTER (WHERE status='Present') as attended,
                      COUNT(*) as total,
                      division,
                      semester,
                      (SELECT department FROM students WHERE id=student_id) as department
                    FROM attendance
                    WHERE student_id = %s AND subject = %s
                    GROUP BY student_id, student_name, subject, division, semester
                    ON CONFLICT (student_id, subject) DO UPDATE SET
                      attended = EXCLUDED.attended,
                      total = EXCLUDED.total
                """, (sid, subject))

        return {"ok": True, "saved": saved, "updated": updated}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def fetch_attendance_records(args, actor_role="admin", actor_id=None, actor_name=""):
    """Fetches attendance records based on filters and provides live analytics."""
    sql_base = """
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE 1=1
    """
    params = []
    
    if actor_role == "faculty":
        sql_base += " AND a.faculty_id = %s"
        params.append(actor_id)
    
    if args.get("dept"):
        sql_base += " AND s.department = %s"
        params.append(args.get("dept"))
    if args.get("div"):
        sql_base += " AND s.division = %s"
        params.append(args.get("div"))
    if args.get("division"): # Support both 'div' and 'division'
        sql_base += " AND s.division = %s"
        params.append(args.get("division"))
    if args.get("subject"):
        sql_base += " AND a.subject ILIKE %s"
        params.append(f"%{args.get('subject')}%")
    if args.get("student_name"):
        sql_base += " AND s.name ILIKE %s"
        params.append(f"%{args.get('student_name')}%")
    if args.get("date_from"):
        sql_base += " AND a.date >= %s"
        params.append(args.get("date_from"))
    if args.get("date_to"):
        sql_base += " AND a.date <= %s"
        params.append(args.get("date_to"))
    if args.get("status"):
        sql_base += " AND a.status = %s"
        params.append(args.get("status"))
    if args.get("faculty"):
        # Assuming there's a faculty table or name stored somewhere. 
        # If not stored, we search in metadata if available. 
        # For now, let's skip or try to match if stored in a.created_by or similar.
        pass

    # 1. Fetch Records with Pagination
    page = int(args.get("page", 1))
    per_page = int(args.get("per_page", 50))
    offset = (page - 1) * per_page
    
    records_sql = "SELECT a.*, s.name as student_name, s.roll as roll_no, s.prn as prn_no " + sql_base + " ORDER BY a.date DESC, s.name ASC LIMIT %s OFFSET %s"
    records = qry(records_sql, params + [per_page, offset])

    # Count total for pagination
    count_sql = "SELECT COUNT(*) as c " + sql_base
    total_count = qone(count_sql, params)["c"]
    total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1

    # 2. Calculate Stats
    stats_sql = "SELECT status, COUNT(*) as count " + sql_base + " GROUP BY status"
    stats_raw = qry(stats_sql, params)
    stats = {"total": 0, "present": 0, "absent": 0, "late": 0, "medical": 0, "leave": 0}
    for row in stats_raw:
        st = row["status"].lower()
        cnt = row["count"]
        stats["total"] += cnt
        if st in stats: stats[st] = cnt

    # 3. Calculate Analytics
    # Avg Attendance
    avg_attended = stats.get("present", 0)
    total_recs = stats.get("total", 1)
    avg_pct = round((avg_attended / total_recs) * 100, 1) if total_recs > 0 else 0

    # Student-wise Performance (top 10 from filtered)
    sw_sql = "SELECT s.name as student_name, COUNT(*) as total, SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as attended " + sql_base + " GROUP BY s.name ORDER BY (SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END)::float / COUNT(*)) DESC LIMIT 10"
    sw_raw = qry(sw_sql, params)
    student_wise = [{"student_name": r["student_name"], "percentage": round((r["attended"]/r["total"])*100, 1) if r["total"] > 0 else 0} for r in sw_raw]

    # Subject-wise
    sj_sql = "SELECT a.subject, COUNT(*) as total, SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as attended " + sql_base + " GROUP BY a.subject ORDER BY (SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END)::float / COUNT(*)) DESC"
    sj_raw = qry(sj_sql, params)
    subject_wise = [{"subject": r["subject"], "percentage": round((r["attended"]/r["total"])*100, 1) if r["total"] > 0 else 0} for r in sj_raw]

    # Defaulters (below 75%)
    defaulters = [s for s in student_wise if s["percentage"] < 75]

    # Monthly Trend (last 6 months)
    mt_sql = "SELECT TO_CHAR(a.date::DATE, 'Mon YYYY') as month, COUNT(*) as total, SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as attended " + sql_base + " GROUP BY TO_CHAR(a.date::DATE, 'Mon YYYY'), DATE_TRUNC('month', a.date::DATE) ORDER BY DATE_TRUNC('month', a.date::DATE) DESC LIMIT 6"
    mt_raw = qry(mt_sql, params)
    monthly_trends = [{"month": r["month"], "percentage": round((r["attended"]/r["total"])*100, 1) if r["total"] > 0 else 0} for r in mt_raw]

    # Weekly Activity (last 7 active days)
    wa_sql = "SELECT TO_CHAR(a.date::DATE, 'Mon DD') as day, COUNT(*) as total, SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as attended " + sql_base + " GROUP BY TO_CHAR(a.date::DATE, 'Mon DD'), a.date::DATE ORDER BY a.date::DATE DESC LIMIT 7"
    wa_raw = qry(wa_sql, params)
    weekly_activity = [{"day": r["day"], "count": r["total"], "percentage": round((r["attended"]/r["total"])*100, 1) if r["total"] > 0 else 0} for r in reversed(wa_raw)]

    # Attendance Distribution Brackets
    # For this, we need percentages of all students in current filter
    dist_sql = "SELECT s.name as student_name, (SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END)::float / COUNT(*)) * 100 as pct " + sql_base + " GROUP BY s.name"
    dist_raw = qry(dist_sql, params)
    distribution = {"excellent": 0, "good": 0, "average": 0, "critical": 0}
    for r in dist_raw:
        p = r["pct"]
        if p >= 90: distribution["excellent"] += 1
        elif p >= 75: distribution["good"] += 1
        elif p >= 60: distribution["average"] += 1
        else: distribution["critical"] += 1

    analytics = {
        "avg_attendance": avg_pct,
        "total_students": len(sw_raw),
        "monthly_trends": monthly_trends,
        "weekly_activity": weekly_activity,
        "distribution": distribution,
        "student_wise": student_wise,
        "subject_wise": subject_wise,
        "defaulters": defaulters
    }

    return {
        "records": records,
        "stats": stats,
        "analytics": analytics,
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page
    }

def edit_attendance_record(role, actor_id, att_id, form_data):
    """Updates an existing attendance record."""
    try:
        status = form_data.get("status")
        exe("UPDATE attendance SET status = %s WHERE id = %s", (status, att_id))
        log_attendance_action(role, actor_id, "edit_record", {"att_id": att_id, "new_status": status})
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def delete_attendance_record(role, actor_id, att_id):
    """Deletes an attendance record."""
    try:
        exe("DELETE FROM attendance WHERE id = %s", (att_id,))
        log_attendance_action(role, actor_id, "delete_record", {"att_id": att_id})
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def process_attendance_import(file_storage, session_obj, subject_override=""):
    """Process excel/file import for attendance."""
    from routes.upload_attendance import process_attendance_upload
    return process_attendance_upload(file_storage, session_obj)

def backup_attendance_data(role, actor_id):
    """Creates a full backup of attendance data and returns the file path."""
    snapshot = export_attendance_snapshot()
    path = create_attendance_backup(snapshot)
    log_attendance_action(role, actor_id, "backup_engine", {"path": path})
    return path

def restore_attendance_data(role, actor_id, backup_path):
    """Restores attendance data from a backup file."""
    try:
        if not backup_path:
            latest = latest_attendance_backup()
            if not latest:
                return {"ok": False, "error": "No backup found"}
            backup_path = latest
        
        data = load_attendance_backup(backup_path)
        conn = get_db()
        try:
            # This is a destructive operation for the engine tables
            conn.execute("TRUNCATE TABLE attendance_sessions RESTART IDENTITY CASCADE")
            conn.execute("TRUNCATE TABLE attendance RESTART IDENTITY CASCADE")
            conn.execute("TRUNCATE TABLE attendance_summary RESTART IDENTITY CASCADE")
            
            # Simple restoration logic - ideally use bulk inserts
            for s in data.get("sessions", []):
                exe("INSERT INTO attendance_sessions (id, subject, division, branch, lecture_date, faculty_id, created_role, created_by, method, is_locked) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (s['id'], s['subject'], s['division'], s['branch'], s['lecture_date'], s['faculty_id'], s['created_role'], s['created_by'], s['method'], s['is_locked']))
            
            for a in data.get("attendance", []):
                 exe("INSERT INTO attendance (id, student_id, date, subject, status, lecture_id, faculty_id, method, branch, division) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                     (a['id'], a['student_id'], a['date'], a['subject'], a['status'], a['lecture_id'], a['faculty_id'], a['method'], a['branch'], a['division']))
            
            for su in data.get("summary", []):
                 exe("INSERT INTO attendance_summary (student_id, student_name, subject, attended, total, division, semester, department) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                     (su['student_id'], su['student_name'], su['subject'], su['attended'], su['total'], su['division'], su['semester'], su['department']))
            
            conn.commit()
            log_attendance_action(role, actor_id, "restore_engine", {"path": backup_path})
            return {"ok": True}
        except Exception as e:
            conn.rollback()
            return {"ok": False, "error": f"Restore failed during DB operations: {e}"}
        finally:
            conn.close()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def reset_attendance_data(role, actor_id):
    """Wipes all attendance engine data."""
    try:
        conn = get_db()
        conn.execute("TRUNCATE TABLE attendance_sessions RESTART IDENTITY CASCADE")
        conn.execute("TRUNCATE TABLE attendance RESTART IDENTITY CASCADE")
        conn.execute("TRUNCATE TABLE attendance_summary RESTART IDENTITY CASCADE")
        conn.commit()
        conn.close()
        log_attendance_action(role, actor_id, "reset_engine", {})
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def get_student_prediction_stats(student_id):
    """Calculates prediction data for a single student."""
    # This is a placeholder for real logic. Reusing get_cumulative logic style.
    stats = qone("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as attended
        FROM attendance WHERE student_id = %s
    """, (student_id,))
    
    total = stats["total"] or 0
    attended = stats["attended"] or 0
    pct = round(attended / total * 100, 1) if total > 0 else 0
    
    return {
        "ok": True,
        "current_pct": pct,
        "attended": attended,
        "total": total,
        "needed_for_75": max(0, int(0.75 * (total + 20) - attended)) # example projection
    }

def submit_correction_request(student_id, student_name, record_id, reason):
    """Submits a correction request to the disputes table and audit log."""
    from utils.pg_wrapper import exe
    try:
        # 1. Insert into formal disputes table
        exe("""
            INSERT INTO attendance_disputes (student_id, attendance_id, reason, status)
            VALUES (%s, %s, %s, 'pending')
        """, (student_id, record_id, reason))

        # 2. Log to audit for compatibility
        from services.attendance_service import log_attendance_action
        log_attendance_action("student", student_id, "correction_request", {
            "student_name": student_name,
            "record_id": record_id,
            "reason": reason
        })
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

class EnterpriseAttendanceService:
    """Modern service for Faculty Attendance Workflow."""

    @staticmethod
    @cache_result("timetable:{faculty_id}:{date}", ttl=3600)
    def get_todays_timetable(faculty_id, date=None):
        """Fetch today's schedule for the faculty."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Parse the day name from the date string
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
        except Exception:
            dt = datetime.now()
            
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        today_day = days[dt.weekday()]
        
        sql = """
            SELECT t.*, 
                   s.status as session_status,
                   s.id as session_id
            FROM timetable t
            LEFT JOIN attendance_sessions s ON t.id = s.timetable_id AND s.lecture_date = :date
            WHERE t.faculty_id = :faculty_id AND t.day = :day
            ORDER BY t.time
        """
        from utils.pg_wrapper import qry_read
        return qry_read(sql, {"faculty_id": faculty_id, "day": today_day, "date": date})

    @staticmethod
    @cache_result("students:{dept}:{year}:{div}", ttl=1800)
    def get_cached_students(dept, year, div):
        from utils.pg_wrapper import qry_read
        return qry_read("""
            SELECT id, roll, name 
            FROM students 
            WHERE division = :div AND year = :year AND department = :dept
            ORDER BY roll
        """, {"div": div, "year": year, "dept": dept})

    @staticmethod
    @cache_result("subjects:{dept}:{sem}", ttl=86400)
    def get_cached_subjects(dept, sem):
        from utils.pg_wrapper import qry_read
        return qry_read("SELECT id, name, code, credits FROM subjects WHERE dept = :dept AND semester = :sem", {"dept": dept, "sem": sem})

    @staticmethod
    def initialize_session(faculty_id, timetable_id):
        """One-click attendance initialization."""
        # 1. Fetch timetable details
        slot = qone("SELECT * FROM timetable WHERE id = %s", (timetable_id,))
        if not slot:
            return {"success": False, "error": "Timetable slot not found"}
        
        # 2. Check if session exists
        session = qone("SELECT id, status FROM attendance_sessions WHERE timetable_id = %s AND lecture_date = CURRENT_DATE", (timetable_id,))
        
        if session:
            session_id = session["id"]
        else:
            # 3. Auto-Create Session
            res = exe("""
                INSERT INTO attendance_sessions (
                    subject, division, branch, lecture_date, faculty_id, 
                    timetable_id, status, lecture_type
                ) VALUES (%s, %s, %s, CURRENT_DATE, %s, %s, 'draft', %s)
                RETURNING id
            """, (slot["subject"], slot["division"], slot["branch"], faculty_id, timetable_id, slot["slot_type"]))
            session_id = res.fetchone()["id"]
        
        # 4. Auto-Load Students (cached read)
        students = EnterpriseAttendanceService.get_cached_students(slot["branch"], slot["year"], slot["division"])
        
        # 5. Fetch existing attendance for this session if any
        existing_att = qry("SELECT student_id, status FROM attendance WHERE lecture_id = %s", (session_id,))
        att_map = {a["student_id"]: a["status"] for a in existing_att}
        
        return {
            "success": True,
            "session_id": session_id,
            "students": [
                {**s, "status": att_map.get(s["id"], "Present")} # Default to Present
                for s in students
            ],
            "details": slot
        }

    @staticmethod
    def submit_attendance(faculty_id, session_id, attendance_data, is_final=True):
        """Submit or save draft attendance."""
        # Check lock status
        if is_attendance_locked(session_id):
            return {"success": False, "error": "Session is locked. Contact administrator."}
        
        session_info = qone("SELECT * FROM attendance_sessions WHERE id = %s", (session_id,))
        if not session_info:
            return {"success": False, "error": "Session not found"}

        # Bulk save
        for record in attendance_data:
            student_id = record["student_id"]
            status = record["status"]
            
            exe("""
                INSERT INTO attendance (
                    student_id, date, subject, status, lecture_id, 
                    faculty_id, division, branch
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (student_id, lecture_id) 
                DO UPDATE SET status = EXCLUDED.status, updated_at = CURRENT_TIMESTAMP
            """, (
                student_id, session_info["lecture_date"], session_info["subject"], 
                status, session_id, faculty_id, session_info["division"], session_info["branch"]
            ))

        if is_final:
            exe("UPDATE attendance_sessions SET status = 'submitted', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (session_id,))
            
        # Batch UPSERT into attendance_summary 
        for record in attendance_data:
            student_id = record["student_id"]
            exe("""
                INSERT INTO attendance_summary 
                  (student_id, student_name, subject, attended, total, 
                   division, semester, department)
                SELECT 
                  student_id,
                  student_name,
                  subject,
                  COUNT(*) FILTER (WHERE status='Present') as attended,
                  COUNT(*) as total,
                  division,
                  semester,
                  (SELECT department FROM students WHERE id=student_id) as department
                FROM attendance
                WHERE student_id = %s AND subject = %s
                GROUP BY student_id, student_name, subject, division, semester
                ON CONFLICT (student_id, subject) DO UPDATE SET
                  attended = EXCLUDED.attended,
                  total = EXCLUDED.total
            """, (student_id, session_info["subject"]))
        
        # Cache Invalidation on Submission
        try:
            from utils.cache import erp_cache
            lecture_date_str = str(session_info["lecture_date"])
            
            # 1. Invalidate timetable cache for faculty
            erp_cache.delete(f"timetable:{faculty_id}:{lecture_date_str}")
            
            # 2. Invalidate admin stats cache for this date
            erp_cache.delete(f"admin_stats:{lecture_date_str}")
            
            # 3. Invalidate attendance summaries for students in current month
            try:
                if isinstance(session_info["lecture_date"], str):
                    dt = datetime.strptime(session_info["lecture_date"], "%Y-%m-%d")
                else:
                    dt = session_info["lecture_date"]
                month_str = dt.strftime("%Y-%m")
            except Exception:
                month_str = datetime.now().strftime("%Y-%m")
                
            for record in attendance_data:
                sid = record["student_id"]
                erp_cache.delete(f"att_summary:{sid}:{month_str}")
        except Exception as cache_err:
            current_app.logger.error(f"Cache invalidation failed: {cache_err}")

        return {"success": True, "message": "Attendance saved successfully"}

    @staticmethod
    def get_sessions_with_attendance(dept=None, division=None, date=None):
        """
        Fetches attendance sessions along with their student attendance records in a single JOIN query,
        preventing the N+1 query bottleneck.
        """
        sql = """
            SELECT s.id as session_id, s.subject, s.division, s.branch as dept, s.lecture_date::TEXT as date, s.status as session_status,
                   a.id as attendance_id, a.student_id, a.status as student_status, st.name as student_name, st.roll as roll_no
            FROM attendance_sessions s
            LEFT JOIN attendance a ON s.id = a.lecture_id
            LEFT JOIN students st ON a.student_id = st.id
            WHERE 1=1
        """
        params = {}
        if dept:
            sql += " AND s.branch = :dept"
            params["dept"] = dept
        if division:
            sql += " AND s.division = :division"
            params["division"] = division
        if date:
            sql += " AND s.lecture_date = :date"
            params["date"] = date
            
        sql += " ORDER BY s.lecture_date DESC, s.id, st.roll ASC"
        
        from utils.pg_wrapper import qry_read
        rows = qry_read(sql, params)
        
        sessions_map = {}
        for r in rows:
            sid = r["session_id"]
            if sid not in sessions_map:
                sessions_map[sid] = {
                    "id": sid,
                    "subject": r["subject"],
                    "division": r["division"],
                    "dept": r["dept"],
                    "date": r["date"],
                    "status": r["session_status"],
                    "records": []
                }
            
            if r["student_id"] is not None:
                sessions_map[sid]["records"].append({
                    "id": r["attendance_id"],
                    "student_id": r["student_id"],
                    "student_name": r["student_name"],
                    "roll_no": r["roll_no"],
                    "status": r["student_status"]
                })
                
        return list(sessions_map.values())


class AttendanceService:
    """Class wrapper for compatibility if needed."""
    def __init__(self):
        try:
            from repositories.attendance_repository import AttendanceRepository
            self.repository = AttendanceRepository()
        except ImportError:
            self.repository = None

    def mark_attendance(self, student_id, subject, status, faculty_id=None, date=None, time_slot=None):
        if self.repository:
            from models.student import Student
            student = Student.query.get(student_id)
            student_name = student.name if student else "Unknown"
            data = {
                'student_id': student_id,
                'student_name': student_name,
                'subject': subject,
                'status': status,
                'faculty_id': faculty_id,
                'date': date or datetime.utcnow().date(),
                'time_slot': time_slot
            }
            return self.repository.create(**data)
        return None

    def get_student_stats(self, student_id):
        if self.repository:
            return self.repository.get_stats_by_student(student_id)
        return None

    @staticmethod
    def get_defaulters(threshold=75, department=None):
        # Implementation of get_defaulters that was in the file
        sql = "SELECT id, name, roll, department FROM students"
        params = []
        if department:
            sql += " WHERE department = %s"
            params.append(department)
        
        students = qry_read(sql, params)
        if not students: return []

        stats_rows = qry_read("""
            SELECT student_id, 
                   COUNT(*) as total,
                   SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present
            FROM attendance
            GROUP BY student_id
        """)
        
        stats_map = {r['student_id']: r for r in stats_rows}
        defaulters = []
        for s in students:
            stat = stats_map.get(s['id'], {'total': 0, 'present': 0})
            total = stat['total']
            present = stat['present']
            
            if total > 0:
                percentage = round((present / total) * 100, 2)
                if percentage < threshold:
                    defaulters.append({
                        **s,
                        "total": total,
                        "present": present,
                        "percentage": percentage
                    })
            else:
                defaulters.append({
                    **s,
                    "total": 0,
                    "present": 0,
                    "percentage": 0.0
                })
        
        return sorted(defaulters, key=lambda x: x['percentage'])
