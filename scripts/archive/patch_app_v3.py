def patch():
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update duplicate_timetable
    dup_target = """@app.route("/duplicate_timetable", methods=["POST"])
@login_required("admin")
def duplicate_timetable():
    r = qone("SELECT * FROM timetable WHERE id=?", (request.form.get("tt_id",""),))
    if r:
        exe("INSERT INTO timetable(day,time,subject,teacher,room,division,semester,slot_type,color) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (r["day"],r["time"],r["subject"],r["teacher"],r["room"] or "",
             r["division"] or "",r["semester"] or "",r["slot_type"] or "Theory",r["color"] or ""))
    return redirect("/timetable?added=1")"""

    dup_repl = """@app.route("/duplicate_timetable", methods=["POST"])
@login_required("admin")
def duplicate_timetable():
    r = qone("SELECT * FROM timetable WHERE id=%s", (request.form.get("tt_id",""),))
    if r:
        exe("INSERT INTO timetable(day,time,start_time,end_time,subject_id,subject,teacher,room,division,semester,slot_type,color,faculty_id,branch,year) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (r["day"],r["time"],r.get("start_time"),r.get("end_time"),r.get("subject_id"),r["subject"],r["teacher"],r["room"] or "",
             r["division"] or "",r["semester"] or "",r["slot_type"] or "Theory",r["color"] or "", r.get("faculty_id"), r.get("branch"), r.get("year")))
    return redirect("/timetable?added=1")"""

    if dup_target in content:
        content = content.replace(dup_target, dup_repl)

    # 2. Update move_timetable
    move_target = """@app.route("/move_timetable", methods=["POST"])
@login_required("admin")
def move_timetable():
    data  = request.get_json() or {}
    tid   = data.get("id","")
    day   = data.get("day","")
    time_s= normalize_time(data.get("time",""))
    r = qone("SELECT * FROM timetable WHERE id=?", (tid,))
    if not r: return jsonify({"ok":False}), 404
    exe("UPDATE timetable SET day=?,time=? WHERE id=?", (day,time_s,tid))
    return jsonify({"ok":True})"""

    move_repl = """@app.route("/move_timetable", methods=["POST"])
@login_required("admin")
def move_timetable():
    data  = request.get_json() or {}
    tid   = data.get("id","")
    day   = data.get("day","")
    time_s= normalize_time(data.get("time",""))
    r = qone("SELECT * FROM timetable WHERE id=%s", (tid,))
    if not r: return jsonify({"ok":False}), 404
    start_time, end_time = None, None
    import re
    m = re.match(r"(\\d+):(\\d+)\\s*-\\s*(\\d+):(\\d+)", time_s)
    if m:
        h1, m1, h2, m2 = map(int, m.groups())
        if h1 < 7: h1 += 12
        if h2 < 7: h2 += 12
        start_time = f"{h1:02d}:{m1:02d}:00"
        end_time = f"{h2:02d}:{m2:02d}:00"
    exe("UPDATE timetable SET day=%s,time=%s,start_time=%s,end_time=%s WHERE id=%s", (day,time_s,start_time,end_time,tid))
    return jsonify({"ok":True})"""

    if move_target in content:
        content = content.replace(move_target, move_repl)

    # 3. patch _parse_timetable_excel
    excel_target = """                for subject, teacher, room, slot_type in _slot(raw, sl, fl):
                    color = assign_color(subject, slot_type)
                    exe(\"\"\"INSERT INTO timetable
                            (day,time,subject,teacher,room,division,semester,slot_type,color)
                            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)\"\"\",
                        (matched, normalize_time(ts), subject, teacher, room,
                         division, sem, slot_type, color))"""

    excel_repl = """                for subject, teacher, room, slot_type in _slot(raw, sl, fl):
                    color = assign_color(subject, slot_type)
                    time_s = normalize_time(ts)
                    start_time, end_time = None, None
                    m = _re.match(r"(\\d+):(\\d+)\\s*-\\s*(\\d+):(\\d+)", time_s)
                    if m:
                        h1, m1, h2, m2 = map(int, m.groups())
                        if h1 < 7: h1 += 12
                        if h2 < 7: h2 += 12
                        start_time = f"{h1:02d}:{m1:02d}:00"
                        end_time = f"{h2:02d}:{m2:02d}:00"

                    f_row = qone("SELECT id FROM faculty WHERE name=%s LIMIT 1", (teacher,))
                    faculty_id = f_row["id"] if f_row else 1
                    
                    s_row = qone("SELECT department, year FROM students WHERE division=%s LIMIT 1", (division,))
                    branch = s_row["department"] if s_row else "Unknown"
                    year = s_row["year"] if s_row else "Unknown"
                    
                    sub_row = qone("SELECT id FROM subjects WHERE name=%s LIMIT 1", (subject,))
                    subject_id = sub_row["id"] if sub_row else None

                    exe(\"\"\"INSERT INTO timetable
                            (day,time,start_time,end_time,subject_id,subject,teacher,room,division,semester,slot_type,color,faculty_id,branch,year)
                            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)\"\"\",
                        (matched, time_s, start_time, end_time, subject_id, subject, teacher, room,
                         division, sem, slot_type, color, faculty_id, branch, year))"""
                         
    if excel_target in content:
        content = content.replace(excel_target, excel_repl)

    with open("app.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Patch OK")

if __name__ == "__main__":
    patch()
