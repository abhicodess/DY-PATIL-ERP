import logging
from flask import Blueprint, render_template, request, session, jsonify, flash, redirect
from services.timetable_service import TimetableService
from repositories.timetable_repository import TimetableRepository
from models.timetable_model import TimetableEntry
from config import DAYS, DAY_ORD, DEPARTMENTS, DIVISIONS
from blueprints.auth.decorators import login_required
from datetime import date
from utils.pg_wrapper import qry, qone, exe
from utils.helpers import safe_int
from routes.features import log_audit

logger = logging.getLogger(__name__)

timetable_v2_bp = Blueprint('timetable_v2', __name__)

# Manual Dependency Injection (Simple for monolithic migration)
_repo = TimetableRepository()
_service = TimetableService(_repo)

@timetable_v2_bp.route("/timetable_v2")
@login_required(role=['admin', 'faculty', 'student'])
def timetable_view():
    """
    Renders the timetable grid and list views.
    Transferred from app.py to modular blueprint.
    """
    # 1. Capture Filters
    q = request.args.get("q", "").strip()
    f_day = request.args.get("day", "")
    f_subj = request.args.get("subject", "")
    f_teach = request.args.get("teacher", "")
    f_div = request.args.get("division", "")
    f_sem = request.args.get("semester", "")
    f_type = request.args.get("slot_type", "")
    view = request.args.get("view", "grid")
    
    # 2. Domain Logic via Service
    # Note: For the aggregate UI view, the service returns the raw domain entities.
    all_entries = _service.get_timetable_grid()
    
    # UI Aggregation logic (keeping it here since it's View-Specific)
    time_slots = sorted(list(set(e.time for e in all_entries if e.time)), key=lambda x: x)
    grid = {d: {ts: [] for ts in time_slots} for d in DAYS}
    for e in all_entries:
        if e.day in grid and e.time in grid[e.day]:
            grid[e.day][e.time].append(e)

    # 3. Handle specific results (simplified for V2)
    filtered_entries = _repo.get_all({
        "day": f_day,
        "semester": f_sem
        # add more filters to repo
    })

    return render_template(
        "common/timetable.html",
        entries=filtered_entries, 
        grid=grid, 
        time_slots=time_slots,
        q=q, f_day=f_day, f_subj=f_subj, f_teach=f_teach,
        f_div=f_div, f_sem=f_sem, f_type=f_type, view=view,
        DAYS=DAYS,
        today_name=date.today().strftime("%A")
    )

@timetable_v2_bp.route("/api/add_time_slot", methods=["POST"])
@login_required(role=['admin'])
def api_add_slot():
    data = request.json
    if not data or 'slot' not in data:
        return jsonify({"ok": False, "error": "Missing slot data"}), 400
    
    # Construct Domain Model
    # Here we might be creating a placeholder slot
    entry = TimetableEntry(
        id=None,
        day=data.get('day', 'Monday'),
        time=data['slot'],
        subject=data.get('subject', 'New Slot'),
        department='General'
    )
    
    result = _service.add_or_update_slot(entry)
    return jsonify(result)

@timetable_v2_bp.route("/api/copy_day", methods=["POST"])
@login_required(role=['admin'])
def api_copy_day():
    data = request.json
    from_day = data.get('from_day')
    to_day = data.get('to_day')
    
    if not from_day or not to_day:
        return jsonify({"ok": False, "error": "Missing day parameters"}), 400
        
    result = _service.copy_day_schedule(from_day, to_day)
    return jsonify(result)

@timetable_v2_bp.route("/public/timetable/<branch>/<year>/<division>")
def public_timetable(branch, year, division):
    """Generates a weekly timetable view accessible to anyone without log in."""
    from utils.pg_wrapper import qry
    from config import DAYS, DAY_ORD
    import re

    # Fetch published timetable entries for this division
    all_entries = [dict(e) for e in qry(
        f"SELECT t.*, f.name as teacher FROM timetable t LEFT JOIN faculty f ON t.faculty_id = f.id "
        f"WHERE t.branch=%s AND t.year=%s AND t.division=%s AND t.published=TRUE "
        f"ORDER BY {DAY_ORD}, t.start_time",
        (branch, year, division)
    )]

    # Extract all distinct time slots
    seen = set()
    raw = []
    for e in all_entries:
        t = e.get("time")
        if t and t not in seen:
            seen.add(t)
            raw.append(t)

    # Sort time slots
    def _sk(ts):
        m = re.match(r"(\d+):(\d+)", ts)
        if not m: return 999
        h = int(m.group(1))
        mn = int(m.group(2))
        if h < 7: h += 12
        return h * 60 + mn

    time_slots = sorted(raw, key=_sk)

    # Construct the grid
    grid = {d: {t: [] for t in time_slots} for d in DAYS}
    for e in all_entries:
        if e["day"] in grid and e["time"] in grid[e["day"]]:
            grid[e["day"]][e["time"]].append(e)

    # Render a beautiful standalone template
    return render_template(
        "timetable/public_timetable.html",
        branch=branch,
        year=year,
        division=division,
        grid=grid,
        time_slots=time_slots,
        DAYS=DAYS
    )


def _build_tt_body(teacher, slots):
    """Build formatted timetable message for a faculty member."""
    # Convert psycopg2.extras.DictCursor objects to dicts so .get() works
    slots = [dict(s) for s in slots]
    lines = ["Weekly Timetable - DY Patil University\n"]
    lines.append("Faculty: " + teacher)
    lines.append("=" * 42)
    by_day = {}
    for s in slots:
        by_day.setdefault(s["day"], []).append(s)
    for day in DAYS:
        if day not in by_day: continue
        lines.append("\n" + day + ":")
        for s in sorted(by_day[day], key=lambda x: x.get("time","") or ""):
            room = (" | Room: " + s["room"]) if s.get("room") else ""
            div  = (" | " + s["division"])  if s.get("division") else ""
            lines.append("  " + str(s["time"] or "").ljust(15) + " " + str(s["subject"]) + room + div)
    lines.append("\n\nSent from DY Patil ERP Admin.")
    return "\n".join(lines)


@timetable_v2_bp.route("/timetable_share", methods=["GET","POST"])
@login_required("admin")
def timetable_share():
    if request.method == "POST":
        target_role = request.form.get("target_role", "faculty")
        target_id   = safe_int(request.form.get("target_id","0"))
        
        if not target_id: return redirect(f"/timetable_share?error=no_{target_role}")

        if target_role == "faculty":
            row = qone("SELECT * FROM faculty WHERE id=%s", (target_id,))
            if not row: return redirect(f"/timetable_share?error=no_faculty")
            exact_name = row["name"]
            slots = qry("SELECT t.*, f.name as teacher FROM timetable t JOIN faculty f ON t.faculty_id = f.id WHERE t.faculty_id=%s ORDER BY t.day, t.start_time", (target_id,))
        else:
            row = qone("SELECT * FROM students WHERE id=%s", (target_id,))
            if not row: return redirect(f"/timetable_share?role=student&error=not_found")
            exact_name = row["name"]
            slots = qry("SELECT t.*, f.name as teacher FROM timetable t JOIN faculty f ON t.faculty_id = f.id WHERE t.branch=%s AND t.division=%s ORDER BY t.day, t.start_time", 
                        (row["department"], row["division"]))

        if not slots: return redirect(f"/timetable_share?role={target_role}&error=no_slots&id={target_id}")

        body = _build_tt_body(exact_name, slots)
        subj = f"Your Weekly Timetable — {len(slots)} slots"
        exe("""INSERT INTO messages(from_role,from_id,from_name,to_role,to_id,to_name,subject,body)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
            ("admin", 1, "Administrator", target_role, target_id, exact_name, subj, body))
        
        log_audit("Share Timetable", f"Sent individual timetable to {target_role}: {exact_name} (ID: {target_id})")
        return redirect(f"/timetable_share?role={target_role}&sent=1&to={exact_name}")

    # GET
    role_sel = request.args.get("role", "faculty")
    id_sel   = safe_int(request.args.get("id","0"))
    selected_slots = []
    matched_entity = None
    
    if id_sel:
        if role_sel == "faculty":
            matched_entity = qone("SELECT * FROM faculty WHERE id=%s", (id_sel,))
            if matched_entity:
                matched_entity = dict(matched_entity)
                selected_slots = qry("SELECT t.*, f.name as teacher FROM timetable t JOIN faculty f ON t.faculty_id = f.id WHERE t.faculty_id=%s ORDER BY t.day, t.start_time", (id_sel,))
        else:
            matched_entity = qone("SELECT * FROM students WHERE id=%s", (id_sel,))
            if matched_entity:
                matched_entity = dict(matched_entity)
                selected_slots = qry("SELECT t.*, f.name as teacher FROM timetable t JOIN faculty f ON t.faculty_id = f.id WHERE t.branch=%s AND t.division=%s ORDER BY t.day, t.start_time", 
                                    (matched_entity["department"], matched_entity["division"]))

    return render_template("common/timetable_share.html",
        role_sel=role_sel,
        selected_slots=selected_slots,
        matched_entity=matched_entity,
        faculty_list=qry("SELECT id,name,department FROM faculty ORDER BY name"),
        student_list=qry("SELECT id,name,department,division,roll FROM students ORDER BY department, division, name"),
        DEPARTMENTS=DEPARTMENTS,
        DIVISIONS=DIVISIONS,
        DAYS=DAYS,
        today_name=date.today().strftime("%A")
    )


@timetable_v2_bp.route("/timetable_send_all", methods=["POST"])
@login_required("admin")
def timetable_send_all():
    target_role = request.form.get("target_role", "faculty")
    sent = skipped = 0
    
    if target_role == "faculty":
        distinct_faculties = qry("SELECT DISTINCT faculty_id FROM timetable WHERE faculty_id IS NOT NULL")
        for row in distinct_faculties:
            fac_id = row["faculty_id"]
            filter_val = (fac_id,)
            f = qone("SELECT name FROM faculty WHERE id=%s", filter_val)
            if not f: 
                skipped += 1
                continue
            fac_name = f["name"]
            slots = qry("SELECT t.*, f2.name as teacher FROM timetable t JOIN faculty f2 ON t.faculty_id=f2.id WHERE t.faculty_id=%s ORDER BY t.day, t.start_time", (fac_id,))
            if not slots: continue
            
            body = _build_tt_body(fac_name, slots)
            subj = f"Your Weekly Timetable — {len(slots)} slots"
            exe("""INSERT INTO messages(from_role,from_id,from_name,to_role,to_id,to_name,subject,body)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                ("admin", 1, "Administrator", "faculty", fac_id, fac_name, subj, body))
            sent += 1
    else:
        students = qry("SELECT id, name, department, division FROM students")
        cache = {}
        for s in students:
            key = (s["department"], s["division"])
            if key not in cache:
                slots = qry("SELECT t.*, f.name as teacher FROM timetable t JOIN faculty f ON t.faculty_id = f.id WHERE t.branch=%s AND t.division=%s ORDER BY t.day, t.start_time", (key[0], key[1]))
                cache[key] = slots
            
            slots = cache[key]
            if not slots:
                skipped += 1
                continue
            
            body = _build_tt_body(s["name"], slots)
            subj = f"Your Class Timetable — {len(slots)} slots"
            exe("""INSERT INTO messages(from_role,from_id,from_name,to_role,to_id,to_name,subject,body)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                ("admin", 1, "Administrator", "student", s["id"], s["name"], subj, body))
            sent += 1

    log_audit("Bulk Share Timetable", f"Initiated bulk share for {target_role}s. Successfully sent: {sent}, Skipped: {skipped}")
    return redirect(f"/timetable_share?role={target_role}&bulk_sent={sent}&bulk_skip={skipped}")
