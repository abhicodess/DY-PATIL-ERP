"""
Centralized Query Registry
Stabilizes SQL joins, aliases, and naming across the ERP.
"""


FACULTY_SESSIONS_HISTORY = """
    SELECT 
        MIN(a.id) as id, 
        f.name as faculty_name, 
        f.department as faculty_dept,
        f.department as branch,
        a.subject,
        a.division,
        a.date as lecture_date,
        a.time_slot,
        a.time_slot as start_time,
        a.semester as year,
        'Submitted' as status,
        'Theory' as method,
        NULL as created_at,
        COUNT(a.id) as total_students,
        SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present,
        SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as absent
    FROM attendance a
    LEFT JOIN faculty f ON f.id::TEXT = a.faculty OR f.name = a.faculty
    WHERE 1=1
    {filters}
    GROUP BY f.id, f.name, f.department, a.subject, a.division, a.date, a.time_slot, a.semester
    ORDER BY a.date DESC LIMIT %s
"""

# ATTENDANCE QUERIES
ATTENDANCE_SESSION_DETAIL = """
    SELECT asess.*, f.name as faculty_name
    FROM attendance_sessions asess
    JOIN faculty f ON asess.faculty_id = f.id
    WHERE asess.id = %s
"""

STUDENT_RECORDS_BY_SESSION = """
    SELECT a.id as att_id, a.status, s.name as student_name, s.roll, s.id as student_id
    FROM attendance a
    JOIN students s ON a.student_id = s.id
    WHERE a.lecture_id = %s
    ORDER BY s.roll
"""

def get_query(name, **kwargs):
    """
    Safely retrieves and formats a centralized query.
    """
    queries = {
        "faculty_sessions_history": FACULTY_SESSIONS_HISTORY,
        "attendance_session_detail": ATTENDANCE_SESSION_DETAIL,
        "student_records_by_session": STUDENT_RECORDS_BY_SESSION,
    }
    
    query = queries.get(name)
    if not query:
        raise ValueError(f"Query {name} not found in registry.")
        
    if kwargs:
        return query.format(**kwargs)
    return query
