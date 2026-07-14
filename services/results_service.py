from repositories.results_repository import ResultsRepository

class ResultsService:
    def __init__(self):
        self.repository = ResultsRepository()

    def get_student_results(self, student_id):
        return self.repository.get_by_student(student_id)

    def calculate_gpa(self, student_id, semester):
        # GP calculation logic
        pass

    def calculate_grade(self, score):
        if score >= 75: return "O"
        if score >= 65: return "A"
        if score >= 55: return "B"
        if score >= 45: return "C"
        if score >= 35: return "D"
        return "F"

def calculate_result(assignment=0.0, attendance=0.0, teaching=0.0, ut=0.0, mse=0.0, tw=0.0, pr_or=0.0, max_total=60.0, is_absent=False):
    if is_absent:
        return None, 'AB', 'Absent', False
        
    def _val(v):
        if v is None: return 0.0
        try: return float(v)
        except: return 0.0
        
    total = _val(assignment) + _val(attendance) + _val(teaching) + _val(ut) + _val(mse) + _val(tw) + _val(pr_or)
    pct = (total / max_total * 100.0) if max_total > 0 else 0.0
    passed = pct >= 40.0
    
    if not passed:
        grade = 'F'
        result = 'Fail'
    elif pct >= 75: grade, result = 'O', 'Pass'
    elif pct >= 70: grade, result = 'A+', 'Pass'
    elif pct >= 60: grade, result = 'A', 'Pass'
    elif pct >= 55: grade, result = 'B+', 'Pass'
    elif pct >= 50: grade, result = 'B', 'Pass'
    else:           grade, result = 'C', 'Pass'
    
    return total, grade, result, passed


def get_ca_total(student_name, subject_name, semester):
    """
    Calculates the sum of all CA component marks entered for a student, subject,
    and semester — capped per-component to the subject's max_marks.

    Uses subject_id (AND) so marks from another subject in the same semester
    are never included. This is the regression guard for the original OR bug.
    """
    from utils.pg_wrapper import qone, qry
    try:
        # Resolve student_id
        stud = qone("SELECT id FROM students WHERE name = %s LIMIT 1", (student_name,))
        if not stud:
            return 0.0
        student_id = stud['id']

        # Resolve subject_id — must match BOTH name AND semester to be unique
        sub = qone(
            "SELECT id FROM subjects WHERE name = %s AND semester = %s LIMIT 1",
            (subject_name, semester)
        )
        if not sub:
            # Fallback: match by name only
            sub = qone("SELECT id FROM subjects WHERE name = %s LIMIT 1", (subject_name,))
        if not sub:
            return 0.0
        subject_id = sub['id']

        # Fetch marks strictly by student_id AND subject_id AND semester (never OR)
        components = qry(
            """
            SELECT component_type, max_marks, obtained_marks
            FROM marks_components
            WHERE student_id = %s AND subject_id = %s AND semester = %s
            """,
            (student_id, subject_id, semester)
        )
        if not components:
            return 0.0

        ca_sum = 0.0
        for comp in components:
            obtained = comp['obtained_marks'] if comp['obtained_marks'] is not None else 0.0
            cap      = comp['max_marks']      if comp['max_marks']      is not None else obtained
            ca_sum  += min(obtained, cap)

        return ca_sum
    except Exception:
        return 0.0


def get_components_for_subject(subject_name, department=None, semester=None):
    """
    Returns component configuration for a subject from subject_mark_components
    (the unified schema). Falls back to subjects_master flat columns if not found.
    Always returns a dict with 'components' list and 'max_total'.
    """
    from utils.pg_wrapper import qry, qone
    try:
        # Try subject_mark_components first (new unified schema)
        sql = """
            SELECT smc.* 
            FROM subject_mark_components smc
            JOIN subjects_master sm ON smc.subject_id = sm.id
            WHERE sm.subject_name = %s
        """
        params = [subject_name]
        if department:
            sql += " AND sm.department = %s"
            params.append(department)
        if semester:
            sql += " AND sm.semester = %s"
            params.append(semester)
        rows = qry(sql, params)
        if rows:
            max_total = sum(r.get('max_marks', 0) for r in rows)
            return {'components': rows, 'max_total': max_total}
    except Exception:
        pass

    # Fallback: subjects_master flat columns
    try:
        from utils.pg_wrapper import qone
        sm_sql = "SELECT * FROM subjects_master WHERE subject_name = %s"
        sm_params = [subject_name]
        if department:
            sm_sql += " AND department = %s"
            sm_params.append(department)
        if semester:
            sm_sql += " AND semester = %s"
            sm_params.append(semester)
        sm_sql += " LIMIT 1"
        row = qone(sm_sql, sm_params)
        if row:
            components = [
                {'component_name': 'Assignment',        'max_marks': row.get('max_assignment', 5)},
                {'component_name': 'Attendance',        'max_marks': row.get('max_attendance', 5)},
                {'component_name': 'Teacher Assessment','max_marks': row.get('max_teaching', 10)},
                {'component_name': 'Unit Test',         'max_marks': row.get('max_ut', 20)},
                {'component_name': 'Mid-Sem',           'max_marks': row.get('max_mse', 20)},
                {'component_name': 'Term Work',         'max_marks': row.get('max_tw', 0)},
                {'component_name': 'Practical/Oral',    'max_marks': row.get('max_pr_or', 0)},
            ]
            max_total = row.get('max_total', 60)
            return {'components': components, 'max_total': max_total}
    except Exception:
        pass

    # Hard fallback defaults
    return {
        'components': [
            {'component_name': 'Assignment',        'max_marks': 5},
            {'component_name': 'Attendance',        'max_marks': 5},
            {'component_name': 'Teacher Assessment','max_marks': 10},
            {'component_name': 'Unit Test',         'max_marks': 20},
            {'component_name': 'Mid-Sem',           'max_marks': 20},
        ],
        'max_total': 60
    }


def get_subject_max_marks(subject_name, department=None, semester=None):
    """Thin wrapper for backward compat — returns {'max_total': N}."""
    info = get_components_for_subject(subject_name, department, semester)
    return {'max_total': info['max_total']}


def parse_marks_value(raw):
    """
    Parses a raw marks cell value from form input or Excel.
    Returns (float_value, is_absent).
    AB / ABSENT / absent → (0.0, True)
    Numeric string        → (float, False)
    Empty / None          → (0.0, False)
    """
    if raw is None:
        return 0.0, False
    s = str(raw).strip().upper()
    if s in ('AB', 'ABSENT', 'A'):
        return 0.0, True
    try:
        return float(s), False
    except (ValueError, TypeError):
        return 0.0, False


def write_audit_log(result_id, action, actor_id=None, notes=None):
    """
    Writes one row to results_audit_log.
    Silently swallows errors so audit failures never break the main flow.

    Column mapping (DDL): performed_by=actor_id, performed_at=NOW(), reason=notes
    """
    try:
        from utils.pg_wrapper import exe
        exe(
            """
            INSERT INTO results_audit_log (result_id, action, performed_by, reason, performed_at)
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (result_id, action, actor_id, notes)
        )
    except Exception:
        pass

