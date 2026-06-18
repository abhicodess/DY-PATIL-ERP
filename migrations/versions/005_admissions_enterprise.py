"""Enterprise Admissions Module Update

Revision ID: 005
Revises: 004
Create Date: 2026-05-28 19:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None

def upgrade():
    # Safely drop existing applications table
    op.execute("DROP TABLE IF EXISTS applications CASCADE")

    # Recreate applications table with enterprise fields
    op.create_table(
        'applications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('token', sa.String(8), unique=True, nullable=False),
        sa.Column('applicant_name', sa.String(100), nullable=False),
        sa.Column('applicant_email', sa.String(100), unique=True, nullable=False),
        sa.Column('applicant_phone', sa.String(20), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=False),
        sa.Column('gender', sa.String(10), nullable=False),
        sa.Column('category', sa.String(10), nullable=False), # OPEN/OBC/SC/ST/NT/EWS
        sa.Column('domicile_state', sa.String(50), nullable=False),
        sa.Column('applied_department', sa.String(50), nullable=False),
        sa.Column('applied_year', sa.String(10), nullable=False),
        sa.Column('status', sa.String(20), server_default='PENDING', nullable=False),
        sa.Column('remarks', sa.Text()),
        sa.Column('submitted_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime()),
        sa.Column('reviewed_by', sa.Integer()),
        sa.Column('merit_score', sa.Float()),
        sa.Column('rank_in_department', sa.Integer()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)
    )

    # application_documents
    op.create_table(
        'application_documents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('application_id', sa.Integer(), sa.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_type', sa.String(50), nullable=False), # SSC_MARKSHEET/HSC_MARKSHEET/...
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(255), nullable=False), # S3 key
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('verified_by', sa.Integer()),
        sa.Column('verified_at', sa.DateTime())
    )

    # merit_lists
    op.create_table(
        'merit_lists',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('department', sa.String(50), nullable=False),
        sa.Column('category', sa.String(10), nullable=False),
        sa.Column('academic_year', sa.String(10), nullable=False),
        sa.Column('application_id', sa.Integer(), sa.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False),
        sa.Column('merit_score', sa.Float(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), server_default='PROVISIONAL', nullable=False), # PROVISIONAL/FINAL
        sa.Column('generated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('generated_by', sa.Integer())
    )

    # seat_matrix
    op.create_table(
        'seat_matrix',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('department', sa.String(50), nullable=False),
        sa.Column('category', sa.String(10), nullable=False),
        sa.Column('total_seats', sa.Integer(), nullable=False),
        sa.Column('filled_seats', sa.Integer(), server_default='0', nullable=False),
        sa.Column('available_seats', sa.Integer(), nullable=False),
        sa.Column('academic_year', sa.String(10), nullable=False),
        sa.Column('last_updated', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)
    )

    # application_timeline
    op.create_table(
        'application_timeline',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('application_id', sa.Integer(), sa.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('action_by', sa.String(100), nullable=False),
        sa.Column('action_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('notes', sa.Text())
    )


def downgrade():
    op.drop_table('application_timeline')
    op.drop_table('seat_matrix')
    op.drop_table('merit_lists')
    op.drop_table('application_documents')
    op.drop_table('applications')
