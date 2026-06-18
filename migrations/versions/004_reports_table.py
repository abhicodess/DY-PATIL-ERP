"""Create reports table

Revision ID: 008
Revises: 007
Create Date: 2026-05-29 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'reports',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False, unique=True),
        sa.Column('report_type', sa.Text(), nullable=False),
        sa.Column('format', sa.Text(), nullable=False),
        sa.Column('filters', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.Text(), server_default='queued', nullable=False),
        sa.Column('progress', sa.Integer(), server_default='0', nullable=False),
        sa.Column('file_path', sa.Text()),
        sa.Column('file_size', sa.Integer()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('students.id', ondelete='SET NULL'), nullable=True), # Nullable for faculty/admins
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), server_default=sa.text("now() + interval '24 hours'"), nullable=False),
        sa.Column('error_msg', sa.Text())
    )
    op.create_index('idx_reports_creator', 'reports', ['created_by', 'created_at'])
    # partial index for queued/processing status
    op.execute("CREATE INDEX idx_reports_pending ON reports(status) WHERE status IN ('queued', 'processing')")

def downgrade():
    op.drop_table('reports')
