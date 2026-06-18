"""Initial Schema

Revision ID: 001
Revises: 
Create Date: 2026-05-21 15:21:02.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Students
    op.create_table(
        'students',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('roll_no', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(100), unique=True, nullable=False),
        sa.Column('phone', sa.String(20)),
        sa.Column('dept', sa.String(50), nullable=False),
        sa.Column('division', sa.String(10), nullable=False),
        sa.Column('year', sa.String(10), nullable=False),
        sa.Column('semester', sa.String(10), nullable=False),
        sa.Column('photo_url', sa.String(255)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # Faculty
    op.create_table(
        'faculty',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('employee_id', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(100), unique=True, nullable=False),
        sa.Column('phone', sa.String(20)),
        sa.Column('dept', sa.String(50), nullable=False),
        sa.Column('designation', sa.String(100)),
        sa.Column('photo_url', sa.String(255))
    )

    # Subjects
    op.create_table(
        'subjects',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('code', sa.String(20), unique=True, nullable=False),
        sa.Column('dept', sa.String(50), nullable=False),
        sa.Column('semester', sa.String(10), nullable=False),
        sa.Column('credits', sa.Integer(), sa.CheckConstraint('credits >= 0'))
    )

    # Timetable
    op.create_table(
        'timetable',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('faculty_id', sa.Integer(), sa.ForeignKey('faculty.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dept', sa.String(50), nullable=False),
        sa.Column('division', sa.String(10), nullable=False),
        sa.Column('year', sa.String(10), nullable=False),
        sa.Column('semester', sa.String(10), nullable=False),
        sa.Column('day', sa.String(20), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.CheckConstraint('start_time < end_time')
    )

    # Attendance Sessions
    op.create_table(
        'attendance_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('timetable_id', sa.Integer(), sa.ForeignKey('timetable.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lecture_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(20), default='Scheduled'),
        sa.Column('is_locked', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )

    # Attendance
    op.create_table(
        'attendance',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('attendance_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('student_id', sa.Integer(), sa.ForeignKey('students.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('marked_by', sa.Integer(), sa.ForeignKey('faculty.id')),
        sa.Column('marked_at', sa.DateTime(), server_default=sa.func.now())
    )

    # Results
    op.create_table(
        'results',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('student_id', sa.Integer(), sa.ForeignKey('students.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('semester', sa.String(10), nullable=False),
        sa.Column('internal_marks', sa.Float()),
        sa.Column('external_marks', sa.Float()),
        sa.Column('total', sa.Float()),
        sa.Column('grade', sa.String(5)),
        sa.Column('is_published', sa.Boolean(), default=False)
    )

    # Messages
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('sender_role', sa.String(20), nullable=False),
        sa.Column('receiver_id', sa.Integer(), nullable=False),
        sa.Column('receiver_role', sa.String(20), nullable=False),
        sa.Column('subject', sa.String(200)),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )

    # Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer()),
        sa.Column('user_role', sa.String(20)),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(50)),
        sa.Column('entity_id', sa.Integer()),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )

    # SMS Logs
    op.create_table(
        'sms_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('recipient', sa.String(20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20)),
        sa.Column('provider_id', sa.String(100)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )

    # Parent Mappings
    op.create_table(
        'parent_mappings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('student_id', sa.Integer(), sa.ForeignKey('students.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_name', sa.String(100), nullable=False),
        sa.Column('parent_phone', sa.String(20), nullable=False),
        sa.Column('relationship_type', sa.String(20)),
        sa.Column('is_primary', sa.Boolean(), default=True)
    )

    # Fee Payments
    op.create_table(
        'fee_payments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('student_id', sa.Integer(), sa.ForeignKey('students.id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount', sa.Float(), sa.CheckConstraint('amount > 0'), nullable=False),
        sa.Column('fee_type', sa.String(50), nullable=False),
        sa.Column('academic_year', sa.String(20), nullable=False),
        sa.Column('payment_date', sa.Date(), server_default=sa.func.now()),
        sa.Column('transaction_id', sa.String(100), unique=True),
        sa.Column('status', sa.String(20), default='Pending')
    )

    # Leave Requests
    op.create_table(
        'leave_requests',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('requester_id', sa.Integer(), nullable=False),
        sa.Column('requester_role', sa.String(20), nullable=False),
        sa.Column('leave_type', sa.String(50), nullable=False),
        sa.Column('from_date', sa.Date(), nullable=False),
        sa.Column('to_date', sa.Date(), nullable=False),
        sa.Column('reason', sa.Text()),
        sa.Column('status', sa.String(20), default='Pending'),
        sa.CheckConstraint('from_date <= to_date')
    )

def downgrade():
    op.drop_table('leave_requests')
    op.drop_table('fee_payments')
    op.drop_table('parent_mappings')
    op.drop_table('sms_logs')
    op.drop_table('audit_logs')
    op.drop_table('messages')
    op.drop_table('results')
    op.drop_table('attendance')
    op.drop_table('attendance_sessions')
    op.drop_table('timetable')
    op.drop_table('subjects')
    op.drop_table('faculty')
    op.drop_table('students')
