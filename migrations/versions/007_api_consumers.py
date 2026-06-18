"""Create api_consumers table

Revision ID: 007_api_consumers
Revises: 006_audit_log
Create Date: 2026-05-30 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '007_api_consumers'
down_revision = '006_audit_log'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'api_consumers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('public.tenants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('api_key', sa.Text(), unique=True, nullable=False),
        sa.Column('contact_email', sa.Text(), nullable=False),
        sa.Column('current_version', sa.Text(), server_default='v1', nullable=False),
        sa.Column('last_seen_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        schema='public'
    )

def downgrade():
    op.drop_table('api_consumers', schema='public')
