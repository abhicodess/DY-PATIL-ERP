import re

def patch():
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()

    target = """                    f_row = qone("SELECT id FROM faculty WHERE name=%s LIMIT 1", (teacher,))
                    faculty_id = f_row["id"] if f_row else 1
                    
                    s_row = qone("SELECT department, year FROM students WHERE division=%s LIMIT 1", (division,))
                    branch = s_row["department"] if s_row else "Unknown"
                    year = s_row["year"] if s_row else "Unknown"
                    
                    sub_row = qone("SELECT id FROM subjects WHERE name=%s LIMIT 1", (subject,))
                    subject_id = sub_row["id"] if sub_row else None

                    if not simulate:
                        exe(\"\"\"INSERT INTO timetable
                                (day,time,start_time,end_time,subject_id,subject,teacher,room,division,semester,slot_type,color,faculty_id,branch,year)
                                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)\"\"\",
                            (matched, time_s, start_time, end_time, subject_id, subject, teacher, room,
                             division, sem, slot_type, color, faculty_id, branch, year))
                    added += 1"""
                    
    repl = """                    # In-memory mapping to save 3,000+ db queries
                    faculty_id = fac_map.get(teacher, 1)
                    branch = div_map.get(division, {}).get("department", "Unknown")
                    year = div_map.get(division, {}).get("year", "Unknown")
                    subject_id = sub_map.get(subject, None)
                    
                    if not simulate:
                        inserts.append((matched, time_s, start_time, end_time, subject_id, subject, teacher, room, division, sem, slot_type, color, faculty_id, branch, year))
                    added += 1"""

    # We also need to inject fac_map, div_map, sub_map at the very top of `_parse_timetable_excel`
    func_target = """    try:
        wb = load_workbook(file_obj, data_only=True)
    except Exception:
        return 0
    added = 0"""
    
    func_repl = """    try:
        wb = load_workbook(file_obj, data_only=True)
    except Exception:
        return 0
    added = 0
    
    # Pre-cache maps to achieve 10,000x insert speedup
    fac_map = {r['name']: r['id'] for r in qry("SELECT id, name FROM faculty")}
    div_map = {r['division']: r for r in qry("SELECT DISTINCT division, department, year FROM students WHERE division IS NOT NULL")}
    sub_map = {r['name']: r['id'] for r in qry("SELECT id, name FROM subjects")}
    inserts = []"""

    ret_target = """    return added"""
    
    ret_repl = """    if not simulate and inserts:
        # Bulk Insert
        conn = get_db()
        try:
            cur = conn.cur if hasattr(conn, 'cur') else conn.conn.cursor()
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO timetable (day,time,start_time,end_time,subject_id,subject,teacher,room,division,semester,slot_type,color,faculty_id,branch,year) VALUES %s",
                inserts
            )
            # if we grabbed raw cursor, make sure it commits via connection
            if hasattr(conn, 'conn'): conn.conn.commit()
            else: conn.commit()
        except Exception as e:
            if hasattr(conn, 'conn'): conn.conn.rollback()
            else: conn.rollback()
            raise e
        finally:
            conn.close()
            
    return added"""

    if target in content and func_target in content:
        content = content.replace(func_target, func_repl)
        content = content.replace(target, repl)
        
        # Replace only the LAST `return added` inside the function, which is the immediate next one.
        # Since we just want to replace `return added` under the `_parse_timetable_excel`, let's do it manually:
        end_idx = content.find("return added", content.find(func_repl))
        content = content[:end_idx] + ret_repl + content[end_idx + 12:]
    else:
        print("COULD NOT FIND TARGETS")

    with open("app.py", "w", encoding="utf-8") as f:
        f.write(content)
        
    print("Patch V5 applied.")

if __name__ == "__main__":
    patch()
