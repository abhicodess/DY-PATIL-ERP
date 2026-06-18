"""API Keys and Logs

Revision ID: 006
Revises: 005
Create Date: 2026-05-28 19:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None

def upgrade():
    # api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('key_hash', sa.String(64), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=False), # JSON array of permissions
        sa.Column('rate_limit', sa.Integer(), nullable=False), # requests per hour
        sa.Column('last_used_at', sa.DateTime()),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('expires_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
    )

    # api_request_logs table
    op.create_table(
        'api_request_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('method', sa.String(10), nullable=False),
        sa.Column('path', sa.String(255), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('response_time_ms', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer()),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('user_agent', sa.String(255)),
        sa.Column('request_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
    )

    # notification_reads table to track read notifications per user
    op.create_table(
        'notification_reads',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('notification_id', sa.Integer(), sa.ForeignKey('notifications.id', ondelete='CASCADE'), nullable=False),
        sa.Column('read_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
    )
    # Unique constraint to prevent duplicate reads
    op.create_unique_constraint('uq_user_notification_read', 'notification_reads', ['user_id', 'role', 'notification_id'])

    # Add is_active column to students and faculty tables for soft deletes
    op.add_column('students', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('faculty', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))


def downgrade():
    op.drop_column('faculty', 'is_active')
    op.drop_column('students', 'is_active')
    op.drop_table('notification_reads')
    op.drop_table('api_request_logs')
    op.drop_table('api_keys')
