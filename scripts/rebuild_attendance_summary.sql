-- Rebuild Historical Attendance Data
-- This script synchronizes the `attendance_summary` table with existing data
-- from the `attendance` table. Execute this via pgAdmin.

INSERT INTO attendance_summary 
    (student_id, student_name, subject, attended, total, division, semester, department)
SELECT 
    a.student_id,
    MAX(s.name) as student_name,
    a.subject,
    COUNT(*) FILTER (WHERE a.status='Present') as attended,
    COUNT(*) as total,
    s.division,
    s.semester,
    s.department
FROM attendance a
JOIN students s ON a.student_id = s.id
GROUP BY a.student_id, a.subject, s.division, s.semester, s.department
ON CONFLICT (student_id, subject) DO UPDATE SET
    student_name = EXCLUDED.student_name,
    attended = EXCLUDED.attended,
    total = EXCLUDED.total,
    division = EXCLUDED.division,
    semester = EXCLUDED.semester,
    department = EXCLUDED.department;

-- Optional: Verify the update
-- SELECT * FROM attendance_summary LIMIT 10;
