"""Create audit_log table

Revision ID: 006_audit_log
Revises: 005_tenants
Create Date: 2026-05-30 12:05:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '006_audit_log'
down_revision = '005_tenants'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('tenant_slug', sa.Text()),
        sa.Column('performed_by', sa.Text(), nullable=False),
        sa.Column('ip_address', sa.Text()),
        sa.Column('payload', sa.Text()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        schema='public'
    )

def downgrade():
    op.drop_table('audit_log', schema='public')
