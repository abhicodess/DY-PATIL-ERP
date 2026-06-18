"""Create tenants table

Revision ID: 005_tenants
Revises: 006
Create Date: 2026-05-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '005_tenants'
down_revision = '006'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'tenants',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('slug', sa.Text(), unique=True, nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('subdomain', sa.Text(), unique=True, nullable=False),
        sa.Column('schema_name', sa.Text(), unique=True, nullable=False),
        sa.Column('db_url', sa.Text()),
        sa.Column('plan', sa.Text(), server_default='standard'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('max_students', sa.Integer(), server_default='5000'),
        sa.Column('max_faculty', sa.Integer(), server_default='500'),
        sa.Column('custom_logo', sa.Text()),
        sa.Column('primary_color', sa.Text(), server_default='#800000'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime()),
        sa.CheckConstraint("plan IN ('standard','premium','enterprise')", name='chk_tenant_plan'),
        schema='public'
    )
    
    op.create_table(
        'tenant_configs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('public.tenants.id', ondelete='CASCADE')),
        sa.Column('key', sa.Text(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.UniqueConstraint('tenant_id', 'key', name='uq_tenant_config_key'),
        schema='public'
    )

def downgrade():
    op.drop_table('tenant_configs', schema='public')
    op.drop_table('tenants', schema='public')
