"""Performance Indexes

Revision ID: 007
Revises: 006
Create Date: 2026-05-29 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None

def upgrade():
    # Attendance index optimizations (date & student/faculty links)
    op.create_index('idx_attendance_student_date', 'attendance', ['student_id', 'date'])
    op.create_index('idx_attendance_faculty_date', 'attendance', ['faculty_id', 'date'])
    
    # Partial index for active (unlocked) sessions
    op.create_index(
        'idx_attendance_sessions_timetable_unlocked', 
        'attendance_sessions', 
        ['timetable_id'], 
        postgresql_where=sa.text('is_locked = false')
    )
    
    # Session date/status covering index
    op.create_index('idx_sessions_date_status', 'attendance_sessions', ['lecture_date', 'status'])
    
    # Student dashboard filter covering index (using the actual column name 'department')
    op.create_index('idx_students_cohort', 'students', ['department', 'year', 'division'])
    
    # Timetable lookups (faculty schedule queries)
    op.create_index('idx_timetable_faculty_day', 'timetable', ['faculty_id', 'day'])
    
    # Subject lookup optimization (using the actual column name 'department')
    op.create_index('idx_subjects_dept_sem', 'subjects', ['department', 'semester'])
    
    # Unique constraint to prevent duplicate attendance sessions
    op.create_unique_constraint(
        'uq_attendance_sessions_timetable_date', 
        'attendance_sessions', 
        ['timetable_id', 'lecture_date']
    )

def downgrade():
    op.drop_constraint('uq_attendance_sessions_timetable_date', 'attendance_sessions', type_='unique')
    op.drop_index('idx_subjects_dept_sem', table_name='subjects')
    op.drop_index('idx_timetable_faculty_day', table_name='timetable')
    op.drop_index('idx_students_cohort', table_name='students')
    op.drop_index('idx_sessions_date_status', table_name='attendance_sessions')
    op.drop_index('idx_attendance_sessions_timetable_unlocked', table_name='attendance_sessions')
    op.drop_index('idx_attendance_faculty_date', table_name='attendance')
    op.drop_index('idx_attendance_student_date', table_name='attendance')
