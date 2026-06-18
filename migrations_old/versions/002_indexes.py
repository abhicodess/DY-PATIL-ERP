"""Performance Indexes

Revision ID: 002
Revises: 001
Create Date: 2026-05-21 15:25:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade():
    # Attendance queries (most frequent)
    op.create_index('idx_att_session_student', 'attendance', ['session_id', 'student_id'])
    
    # Covering index for student status lookups
    op.execute("CREATE INDEX idx_att_student_date ON attendance(student_id) INCLUDE (status)")
    
    # Session filtering by date and timetable
    op.create_index('idx_att_session_date', 'attendance_sessions', ['lecture_date', 'timetable_id'])
    
    # Student lookups by cohort
    op.create_index('idx_students_dept_div', 'students', ['dept', 'division', 'year', 'semester'])
    
    # Fast roll number lookups
    op.create_index('idx_students_roll', 'students', ['roll_no'])
    
    # Results per student/semester
    op.create_index('idx_results_student_sem', 'results', ['student_id', 'semester'])
    
    # Time-series audit logs (descending for latest first)
    op.create_index('idx_audit_created', 'audit_logs', [sa.text('created_at DESC')])
    
    # Partial index for unread messages (significant size reduction)
    op.execute("CREATE INDEX idx_messages_receiver_unread ON messages(receiver_id, is_read) WHERE is_read = false")
    
    # Timetable lookups for faculty
    op.create_index('idx_tt_faculty_day', 'timetable', ['faculty_id', 'day'])

def downgrade():
    op.drop_index('idx_tt_faculty_day', table_name='timetable')
    op.execute("DROP INDEX idx_messages_receiver_unread")
    op.drop_index('idx_audit_created', table_name='audit_logs')
    op.drop_index('idx_results_student_sem', table_name='results')
    op.drop_index('idx_students_roll', table_name='students')
    op.drop_index('idx_students_dept_div', table_name='students')
    op.drop_index('idx_att_session_date', table_name='attendance_sessions')
    op.execute("DROP INDEX idx_att_student_date")
    op.drop_index('idx_att_session_student', table_name='attendance')
