import re

def patch():
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Target 1: tshare singles
    tshare_target = """        slots = []
        if name_parts:
            slots = qry("SELECT * FROM timetable WHERE teacher LIKE %s ORDER BY day,time",
                        ("%" + name_parts[0] + "%",))"""
    tshare_repl = """        slots = qry("SELECT t.*, f.name as teacher FROM timetable t JOIN faculty f ON t.faculty_id = f.id WHERE t.faculty_id=%s ORDER BY t.day, t.start_time", (fac_id,))"""
        
    tshare_target2 = """            if name_parts:
                selected_slots = qry("SELECT * FROM timetable WHERE teacher LIKE %s ORDER BY day,time",
                                     ("%" + name_parts[0] + "%",))"""
    tshare_repl2 = """            selected_slots = qry("SELECT t.*, f.name as teacher FROM timetable t JOIN faculty f ON t.faculty_id = f.id WHERE t.faculty_id=%s ORDER BY t.day, t.start_time", (fac_id_sel,))"""
    
    # Notice: It seems they might be using `?` or `%s` depending on my prior changes! I will use regex:
    content = re.sub(r'slots\s*=\s*qry\("SELECT \* FROM timetable WHERE teacher LIKE[^)]+\)', 
                     r'slots = qry("SELECT t.*, f.name as teacher FROM timetable t JOIN faculty f ON t.faculty_id = f.id WHERE t.faculty_id=%s ORDER BY t.day, t.start_time", (fac_id,))', content)

    content = re.sub(r'selected_slots\s*=\s*qry\("SELECT \* FROM timetable WHERE teacher LIKE[^)]+\)', 
                     r'selected_slots = qry("SELECT t.*, f.name as teacher FROM timetable t JOIN faculty f ON t.faculty_id = f.id WHERE t.faculty_id=%s ORDER BY t.day, t.start_time", (fac_id_sel,))', content)

    # 2. timetable_send_all loop replacment:
    # Safely find timetable_send_all block and replace completely
    tsend_all_regex = r'@app\.route\("/timetable_send_all", methods=\["POST"\]\)\s*@login_required\("admin"\)\s*def timetable_send_all\(\):.*?return redirect\(f"/timetable_share\?bulk_sent=\{sent\}&bulk_skip=\{skipped\}"\)'
    
    tsend_all_repl_str = """@app.route("/timetable_send_all", methods=["POST"])
@login_required("admin")
def timetable_send_all():
    sent = skipped = 0
    distinct_faculties = qry("SELECT DISTINCT faculty_id FROM timetable WHERE faculty_id IS NOT NULL")
    for row in distinct_faculties:
        fac_id = row["faculty_id"]
        f = qone("SELECT name FROM faculty WHERE id=%s", (fac_id,))
        if not f: 
            skipped += 1
            continue
        fac_name = f["name"]
        
        slots = qry("SELECT t.*, f2.name as teacher FROM timetable t JOIN faculty f2 ON t.faculty_id=f2.id WHERE t.faculty_id=%s ORDER BY day, start_time", (fac_id,))
        if not slots: 
            continue
            
        body = _build_tt_body(fac_name, slots)
        subj = f"Your Weekly Timetable — {len(slots)} slots"
        exe(\"\"\"INSERT INTO messages(from_role,from_id,from_name,to_role,to_id,to_name,subject,body)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s)\"\"\",
            ("admin", 1, "Administrator", "faculty", fac_id, fac_name, subj, body))
        sent += 1
    return redirect(f"/timetable_share?bulk_sent={sent}&bulk_skip={skipped}")"""

    content = re.sub(tsend_all_regex, tsend_all_repl_str, content, flags=re.DOTALL)

    # 3. Disable manual attendance routes
    content = content.replace('def save_attendance():\n    student_name', 'def save_attendance():\n    return redirect("/attendance?error=Manual entry disabled inside zero-trust architecture")\n    student_name')
    content = content.replace('def faculty_save_attendance():\n    subject', 'def faculty_save_attendance():\n    return redirect("/faculty_attendance?error=Manual entry disabled inside zero-trust architecture")\n    subject')

    # 4. Analytics Endpoint
    if "/api/timetable_analytics" not in content:
        analytics_str = """
@app.route("/api/timetable_analytics", methods=["POST"])
@login_required("admin")
def api_timetable_analytics():
    f = request.files.get("file")
    if not f: return jsonify({"error": "No file uploaded"})
    
    # Parse excel for analytics WITHOUT saving
    added = _parse_timetable_excel(f, simulate=True)
    
    # Calculate stats from currently loaded DB
    total_classes = qone("SELECT COUNT(*) as c FROM timetable")["c"]
    sub_count = qone("SELECT COUNT(DISTINCT subject_id) as c FROM timetable")["c"]
    
    # Faculty load
    f_rows = qry("SELECT f.name as teacher, COUNT(t.id) as loads FROM timetable t JOIN faculty f ON t.faculty_id=f.id GROUP BY f.name")
    fac_load = {}
    for r in f_rows:
        fac_load[r["teacher"]] = r["loads"]
        
    return jsonify({
        "success": True,
        "simulated_slots_parsed_from_file": added,
        "total_classes": total_classes,
        "subject_count": sub_count,
        "faculty_load": fac_load
    })
"""
        # Append before main
        content = content.replace('if __name__ == "__main__":', analytics_str + '\nif __name__ == "__main__":')

    # We need to change _parse_timetable_excel signature
    content = content.replace('def _parse_timetable_excel(file_obj):', 'def _parse_timetable_excel(file_obj, simulate=False):')
    content = content.replace('added += 1\n    return added', 'added += 1\n    return added')
    
    # Intercept execute in parse excel!
    excel_insert = """                    exe(\"\"\"INSERT INTO timetable
                            (day,time,start_time,end_time,subject_id,subject,teacher,room,division,semester,slot_type,color,faculty_id,branch,year)
                            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)\"\"\",
                        (matched, time_s, start_time, end_time, subject_id, subject, teacher, room,
                         division, sem, slot_type, color, faculty_id, branch, year))"""
                         
    excel_insert_repl = """                    if not simulate:
                        exe(\"\"\"INSERT INTO timetable
                                (day,time,start_time,end_time,subject_id,subject,teacher,room,division,semester,slot_type,color,faculty_id,branch,year)
                                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)\"\"\",
                            (matched, time_s, start_time, end_time, subject_id, subject, teacher, room,
                             division, sem, slot_type, color, faculty_id, branch, year))"""
    
    content = content.replace(excel_insert, excel_insert_repl)

    # 5. Fix timetable global queries to map `teacher` via JOIN
    import_queries = [
        (r'all_rows = qry\(f"SELECT \* FROM timetable ORDER BY \{DAY_ORD\}, time"\)', 
         r'all_rows = qry(f"SELECT t.*, f.name as teacher FROM timetable t LEFT JOIN faculty f ON t.faculty_id = f.id ORDER BY t.{DAY_ORD}, t.start_time")'),
        (r'sql = "SELECT \* FROM timetable WHERE 1=1"; params = \[\]\n    if q:\s+sql \+= " AND \(subject LIKE \? OR teacher LIKE \? OR room LIKE \? OR division LIKE \?\)"; params \+= \[f"%\{q\}%"\]\*4',
         r'sql = "SELECT t.*, f.name as teacher FROM timetable t LEFT JOIN faculty f ON t.faculty_id = f.id WHERE 1=1"; params = []\n    if q:       sql += " AND (t.subject LIKE %s OR f.name LIKE %s OR t.room LIKE %s OR t.division LIKE %s)"; params += [f"%{q}%"]*4'),
        (r'sql \+= " AND subject LIKE \?";\s+params\.append\(f"%\{f_subj\}%"\)', r'sql += " AND t.subject LIKE %s";  params.append(f"%{f_subj}%")'),
        (r'sql \+= " AND teacher LIKE \?";\s+params\.append\(f"%\{f_teach\}%"\)', r'sql += " AND f.name LIKE %s";  params.append(f"%{f_teach}%")'),
        (r'sql \+= f" ORDER BY \{DAY_ORD\}, time"', r'sql += f" ORDER BY t.{DAY_ORD}, t.start_time"'),
        (r'f"SELECT \* FROM timetable WHERE branch=%s AND year=%s AND division=%s ORDER BY \{DAY_ORD\}, start_time"', r'f"SELECT t.*, f.name as teacher FROM timetable t LEFT JOIN faculty f ON t.faculty_id = f.id WHERE t.branch=%s AND t.year=%s AND t.division=%s ORDER BY t.{DAY_ORD}, t.start_time"'),
        (r'f"SELECT \* FROM timetable WHERE faculty_id=%s ORDER BY \{DAY_ORD\}, start_time"', r'f"SELECT t.*, f.name as teacher FROM timetable t JOIN faculty f ON t.faculty_id = f.id WHERE t.faculty_id=%s ORDER BY t.{DAY_ORD}, t.start_time"'),
        (r'entries = qry\("SELECT day, time, subject, teacher, room, division FROM timetable ORDER BY day, start_time"\)', r'entries = qry("SELECT t.day, t.start_time, t.end_time, t.subject, f.name as teacher, t.room, t.division FROM timetable t LEFT JOIN faculty f ON t.faculty_id = f.id ORDER BY t.day, t.start_time")'),
    ]

    for targ, repl in import_queries:
        content = re.sub(targ, repl, content)

    # Convert e['time'] reference in pdf export as well
    content = content.replace("e['time']", 'e.get("time","") or f"{e.get(\'start_time\',\'\')}-{e.get(\'end_time\',\'\')}"')

    with open("app.py", "w", encoding="utf-8") as f:
        f.write(content)
        
    print("Patch V4 successfully applied.")

if __name__ == "__main__":
    patch()
