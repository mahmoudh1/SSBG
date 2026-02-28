"""Add key lifecycle and crypto-shred schema changes.

Revision ID: 20260228_0003
Revises: 20260228_0002
Create Date: 2026-02-28 20:10:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

# revision identifiers, used by Alembic.
revision = '20260228_0003'
down_revision = '20260228_0002'
branch_labels = None
depends_on = None


def _has_column(connection: Connection, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(connection)
    return any(col['name'] == column_name for col in inspector.get_columns(table_name))


def _has_index(connection: Connection, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(connection)
    return any(item['name'] == index_name for item in inspector.get_indexes(table_name))


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())

    if 'key_versions' not in tables:
        op.create_table(
            'key_versions',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('version_id', sa.String(length=64), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('is_destroyed', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('rotated_from_version', sa.String(length=64), nullable=True),
            sa.Column('created_by_key_id', sa.String(length=64), nullable=True),
            sa.Column('rotation_reason', sa.String(length=255), nullable=True),
            sa.Column(
                'created_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('CURRENT_TIMESTAMP'),
                nullable=False,
            ),
            sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('destroyed_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('version_id'),
        )
        op.create_index('ix_key_versions_version_id', 'key_versions', ['version_id'], unique=True)
        op.create_index('ix_key_versions_is_active', 'key_versions', ['is_active'], unique=False)
        op.create_index(
            'ix_key_versions_is_destroyed',
            'key_versions',
            ['is_destroyed'],
            unique=False,
        )

    if 'backup_metadata' in tables:
        if not _has_column(connection, 'backup_metadata', 'irreversible_reason'):
            op.add_column(
                'backup_metadata',
                sa.Column('irreversible_reason', sa.String(length=255), nullable=True),
            )
        if not _has_column(connection, 'backup_metadata', 'shredded_at'):
            op.add_column(
                'backup_metadata',
                sa.Column('shredded_at', sa.DateTime(timezone=True), nullable=True),
            )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())

    if 'backup_metadata' in tables:
        if _has_column(connection, 'backup_metadata', 'shredded_at'):
            op.drop_column('backup_metadata', 'shredded_at')
        if _has_column(connection, 'backup_metadata', 'irreversible_reason'):
            op.drop_column('backup_metadata', 'irreversible_reason')

    if 'key_versions' in tables:
        if _has_index(connection, 'key_versions', 'ix_key_versions_is_destroyed'):
            op.drop_index('ix_key_versions_is_destroyed', table_name='key_versions')
        if _has_index(connection, 'key_versions', 'ix_key_versions_is_active'):
            op.drop_index('ix_key_versions_is_active', table_name='key_versions')
        if _has_index(connection, 'key_versions', 'ix_key_versions_version_id'):
            op.drop_index('ix_key_versions_version_id', table_name='key_versions')
        op.drop_table('key_versions')
