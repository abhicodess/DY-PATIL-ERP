import re

def patch():
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update save_timetable
    save_target = """    if division:
        s_row = qone("SELECT department, year FROM students WHERE division=%s LIMIT 1", (division,))
        if s_row:
            branch = s_row["department"]
            year = s_row["year"]

    # --- CLASH DETECTION LOGIC ---"""
    
    save_repl = """    if division:
        s_row = qone("SELECT department, year FROM students WHERE division=%s LIMIT 1", (division,))
        if s_row:
            branch = s_row["department"]
            year = s_row["year"]

    # Parse start and end time
    start_time = None
    end_time = None
    if time_s:
        import re as re_mod
        m = re_mod.match(r"(\\d+):(\\d+)\\s*-\\s*(\\d+):(\\d+)", time_s)
        if m:
            h1, m1, h2, m2 = map(int, m.groups())
            if h1 < 7: h1 += 12
            if h2 < 7: h2 += 12
            start_time = f"{h1:02d}:{m1:02d}:00"
            end_time = f"{h2:02d}:{m2:02d}:00"

    sub_row = qone("SELECT id FROM subjects WHERE name=%s LIMIT 1", (subject,))
    subject_id = sub_row["id"] if sub_row else None

    # --- CLASH DETECTION LOGIC ---"""
    
    content = content.replace(save_target, save_repl)

    clash_target = """    if faculty_id:
        if qone("SELECT 1 FROM timetable WHERE day=%s AND time=%s AND faculty_id=%s", (day, time_s, faculty_id)):
            return redirect("/timetable?error=" + "Teacher clash: Faculty is already assigned here.")
    if branch and year and division:
        if qone("SELECT 1 FROM timetable WHERE day=%s AND time=%s AND branch=%s AND year=%s AND division=%s", (day, time_s, branch, year, division)):
            return redirect("/timetable?error=" + f"Class clash: {division} is busy at {time_s}.")
    if room:
        if qone("SELECT 1 FROM timetable WHERE day=%s AND time=%s AND room=%s", (day, time_s, room)):
            return redirect("/timetable?error=" + f"Room clash: {room} is already booked.")"""
            
    clash_repl = """    clash_cond = "NOT (end_time <= %s OR start_time >= %s)"
    if faculty_id and start_time and end_time:
        if qone(f"SELECT 1 FROM timetable WHERE day=%s AND faculty_id=%s AND {clash_cond}", (day, faculty_id, start_time, end_time)):
            return redirect("/timetable?error=" + "Teacher clash: Faculty is already assigned here.")
    if branch and year and division and start_time and end_time:
        if qone(f"SELECT 1 FROM timetable WHERE day=%s AND branch=%s AND year=%s AND division=%s AND {clash_cond}", (day, branch, year, division, start_time, end_time)):
            return redirect("/timetable?error=" + f"Class clash: {division} is busy at {time_s}.")
    if room and start_time and end_time:
        if qone(f"SELECT 1 FROM timetable WHERE day=%s AND room=%s AND {clash_cond}", (day, room, start_time, end_time)):
            return redirect("/timetable?error=" + f"Room clash: {room} is already booked.")"""

    content = content.replace(clash_target, clash_repl)

    insert_target = """    exe("INSERT INTO timetable(day,time,subject,teacher,room,division,semester,slot_type,color,faculty_id,branch,year) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (day,time_s,subject,teacher,room,division,semester,slot_type,color,faculty_id,branch,year))"""
    
    insert_repl = """    exe("INSERT INTO timetable(day,time,start_time,end_time,subject_id,subject,teacher,room,division,semester,slot_type,color,faculty_id,branch,year) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (day,time_s,start_time,end_time,subject_id,subject,teacher,room,division,semester,slot_type,color,faculty_id,branch,year))"""
        
    content = content.replace(insert_target, insert_repl)
    
    # 2. Update Student and Faculty Timetable queries
    stud_target = """f"SELECT * FROM timetable WHERE branch=%s AND year=%s AND division=%s ORDER BY {DAY_ORD},time","""
    stud_repl = """f"SELECT * FROM timetable WHERE branch=%s AND year=%s AND division=%s ORDER BY {DAY_ORD}, start_time","""
    content = content.replace(stud_target, stud_repl)
    
    fac_target = """f"SELECT * FROM timetable WHERE faculty_id=%s ORDER BY {DAY_ORD},time","""
    fac_repl = """f"SELECT * FROM timetable WHERE faculty_id=%s ORDER BY {DAY_ORD}, start_time","""
    content = content.replace(fac_target, fac_repl)
    
    pdf_target = """entries = qry("SELECT day, time, subject, teacher, room, division FROM timetable ORDER BY day, time")"""
    pdf_repl = """entries = qry("SELECT day, time, subject, teacher, room, division FROM timetable ORDER BY day, start_time")"""
    content = content.replace(pdf_target, pdf_repl)
    
    # 3. Attendance integration check
    att_target = """        valid_slot = qone(
            "SELECT id FROM timetable WHERE faculty_id=%s AND subject=%s AND division=%s AND day=%s", 
            (faculty_id, subject, division, day_str)
        )"""
    
    att_repl = """        sub_row = qone("SELECT id FROM subjects WHERE name=%s LIMIT 1", (subject,))
        subject_id = sub_row["id"] if sub_row else None
        
        valid_slot = qone(
            "SELECT id FROM timetable WHERE faculty_id=%s AND subject_id=%s AND division=%s AND day=%s AND start_time <= localtime AND end_time >= localtime", 
            (faculty_id, subject_id, division, day_str)
        )"""
    content = content.replace(att_target, att_repl)
    
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Patch applied successfully.")

if __name__ == "__main__":
    patch()
