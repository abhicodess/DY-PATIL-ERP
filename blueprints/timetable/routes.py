from flask import render_template, request, session, redirect, url_for
from blueprints.timetable import timetable_bp
from blueprints.auth.decorators import login_required
from services.timetable_service import TimetableService

timetable_service = TimetableService()

@timetable_bp.route("/")
@login_required
def index():
    role = session.get("role")
    if role == "admin":
        return redirect("/timetable_v2")
    elif role == "faculty":
        return redirect("/faculty_timetable")
    elif role == "student":
        from utils.pg_wrapper import qry, qone
        from config import DAYS, DAY_ORD
        import re
        
        student_id = session.get("student_id")
        student = qone("SELECT * FROM students WHERE id = %s", (student_id,))
        if not student:
            return redirect("/logout")
            
        student_branch = session.get("student_branch", "")
        student_year = session.get("student_year", "")
        student_div = session.get("student_division", "")
        
        all_entries = [dict(e) for e in qry(
            f"SELECT t.*, f.name as teacher FROM timetable t LEFT JOIN faculty f ON t.faculty_id = f.id WHERE t.branch=%s AND t.year=%s AND t.division=%s AND t.published=TRUE ORDER BY {DAY_ORD}, t.start_time",
            (student_branch, student_year, student_div)
        )]
        for e in all_entries:
            # Safely normalize or format time if needed
            e["time"] = e.get("time", "") or ""
            
        seen = set()
        raw = []
        for e in all_entries:
            t = e["time"]
            if t and t not in seen:
                seen.add(t)
                raw.append(t)
                
        def _sk(ts):
            m = re.match(r"(\d+):(\d+)", ts)
            if not m: return 999
            h = int(m.group(1))
            mn = int(m.group(2))
            if h < 7: h += 12
            return h * 60 + mn
            
        time_slots = sorted(raw, key=_sk)
        grid = {d: {t: [] for t in time_slots} for d in DAYS}
        for e in all_entries:
            if e["day"] in grid and e["time"] in grid[e["day"]]:
                grid[e["day"]][e["time"]].append(e)
                
        return render_template("student/student_timetable.html",
                               student=student,
                               grid=grid,
                               time_slots=time_slots,
                               DAYS=DAYS)
    else:
        return redirect("/login")
