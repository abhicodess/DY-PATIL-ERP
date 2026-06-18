"""Add Performance Materialized Views

Revision ID: 004
Revises: 003
Create Date: 2026-05-21 15:35:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '004'
down_revision = '003'

def upgrade():
    # Attendance Summary Materialized View for fast reporting
    op.execute("""
        CREATE MATERIALIZED VIEW attendance_summary_mv AS
        SELECT 
            student_id,
            count(*) as total_lectures,
            count(*) FILTER (WHERE status = 'Present') as present_count,
            (count(*) FILTER (WHERE status = 'Present')::float / NULLIF(count(*), 0) * 100)::decimal(5,2) as attendance_pct
        FROM attendance
        GROUP BY student_id
    """)
    op.execute("CREATE UNIQUE INDEX idx_mv_student_id ON attendance_summary_mv(student_id)")

def downgrade():
    op.execute("DROP MATERIALIZED VIEW IF EXISTS attendance_summary_mv")
