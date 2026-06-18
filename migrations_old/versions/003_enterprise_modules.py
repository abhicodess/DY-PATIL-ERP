"""Add Enterprise Modules

Revision ID: 003
Revises: 002
Create Date: 2026-05-21 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade():
    # Applications
    op.create_table(
        'applications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('applicant_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(100), unique=True, nullable=False),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('dept_preference', sa.String(50), nullable=False),
        sa.Column('score_10th', sa.Float(), nullable=False),
        sa.Column('score_12th', sa.Float(), nullable=False),
        sa.Column('entrance_score', sa.Float()),
        sa.Column('documents_url', sa.String(255)),
        sa.Column('status', sa.String(20), server_default='Pending'),
        sa.Column('applied_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('token', sa.String(100), unique=True)
    )

    # Exams
    op.create_table(
        'exams',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('exam_type', sa.String(50)),
        sa.Column('start_date', sa.Date()),
        sa.Column('end_date', sa.Date()),
        sa.Column('is_active', sa.Boolean(), server_default='true')
    )

    # Exam Slots
    op.create_table(
        'exam_slots',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('exam_id', sa.Integer(), sa.ForeignKey('exams.id', ondelete='CASCADE')),
        sa.Column('subject_id', sa.Integer()),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('room', sa.String(20))
    )

    # Faculty salary
    op.create_table(
        'faculty_salary',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('faculty_id', sa.Integer(), sa.ForeignKey('faculty.id', ondelete='CASCADE'), nullable=False),
        sa.Column('basic_salary', sa.Float(), nullable=False),
        sa.Column('hra', sa.Float(), server_default='0'),
        sa.Column('da', sa.Float(), server_default='0'),
        sa.Column('pf_deduction', sa.Float(), server_default='0'),
        sa.Column('net_salary', sa.Float()),
        sa.Column('effective_from', sa.Date(), server_default=sa.func.now())
    )

    # Payslips
    op.create_table(
        'payslips',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('faculty_id', sa.Integer(), sa.ForeignKey('faculty.id', ondelete='CASCADE'), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('gross_salary', sa.Float()),
        sa.Column('net_salary', sa.Float()),
        sa.Column('pdf_url', sa.String(255)),
        sa.Column('generated_at', sa.DateTime(), server_default=sa.func.now())
    )

def downgrade():
    op.drop_table('payslips')
    op.drop_table('faculty_salary')
    op.drop_table('exam_slots')
    op.drop_table('exams')
    op.drop_table('applications')
