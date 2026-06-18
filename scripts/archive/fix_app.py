import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1
bad_block_1 = '''@app.route("/bulk_delete_students", methods=["POST"])
@login_required("admin")
def bulk_delete_students():
    ids = request.form.getlist("ids[]")
        params.extend(marks_match_student_params(sid, student))'''

good_block_1 = '''@app.route("/bulk_delete_students", methods=["POST"])
@login_required("admin")
def bulk_delete_students():
    ids = request.form.getlist("ids[]")
    for i in ids:
        exe("DELETE FROM students WHERE id=%s", (i,))
    return redirect(f"/students?deleted={len(ids)}")

@app.route("/bulk_delete_faculty", methods=["POST"])
@login_required("admin")
def bulk_delete_faculty():
    ids = request.form.getlist("ids[]")
    for i in ids:
        exe("DELETE FROM faculty WHERE id=%s", (i,))
    return redirect(f"/faculty?deleted={len(ids)}")

# ════════════════════════════════════════════════════════════
#  QUICK WIN 5 — MARKS EXPORT
# ════════════════════════════════════════════════════════════
@app.route("/export_marks_excel")
@login_required("faculty")
def export_marks_excel():
    fid     = session["faculty_id"]
    subject = request.args.get("subject","").strip()
    student = request.args.get("student","").strip()

    sql = "SELECT * FROM marks WHERE faculty_id=%s"
    params = [fid]
    if subject: sql += " AND subject=%s"; params.append(subject)
    if student:
        sid = resolve_student_id(student)
        sql += f" AND ({marks_match_student_sql()})"
        params.extend(marks_match_student_params(sid, student))'''

if bad_block_1 in content:
    content = content.replace(bad_block_1, good_block_1)
    print("Fix 1 applied")
else:
    print("Fix 1 not needed or didn't match exactly. Doing regex fallback...")
    res = re.sub(r'def bulk_delete_students\(\):\n\s*ids = request\.form\.getlist\("ids\[\]"\)\n\s*params\.extend', good_block_1.replace('@app.route("/bulk_delete_students", methods=["POST"])\n@login_required("admin")\ndef bulk_delete_students():\n    ids = request.form.getlist("ids[]")\n        params.extend', '...'), content)
    # Actually just simple replace
    content = content.replace('def bulk_delete_students():\n    ids = request.form.getlist("ids[]")\n        params.extend(marks_match_student_params(sid, student))', good_block_1.split('@login_required("admin")\n')[1])
    if 'DELETE FROM faculty' in content: 
         print("Fix 1 applied fallback")

# Fix 2
bad_block_2 = '''@app.route("/search_faculty")
@login_required("faculty")
def search_faculty():
        return render_template("shortage_report.html", report=report, threshold=threshold)

    ids = [int(s["id"]) for s in students]'''

good_block_2 = '''@app.route("/search_faculty")
@login_required("faculty")
def search_faculty():
    q = request.args.get("q","").strip()
    return redirect(f"/faculty_attendance?q={q}" if q else "/faculty_attendance")

# ════════════════════════════════════════════════════════════
#  HIGH VALUE 1 — ATTENDANCE SHORTAGE ALERT
# ════════════════════════════════════════════════════════════
@app.route("/shortage_report")
@login_required("admin")
def shortage_report():
    threshold = safe_int(request.args.get("threshold","75"))
    students  = qry("SELECT id,name,roll,department,year FROM students ORDER BY name")
    report = []
    if not students:
        return render_template("shortage_report.html", report=report, threshold=threshold)

    ids = [int(s["id"]) for s in students]'''

if bad_block_2 in content:
    content = content.replace(bad_block_2, good_block_2)
    print("Fix 2 applied")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Done fixing app.py")
