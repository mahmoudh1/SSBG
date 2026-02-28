"""Add tamper-evident chain fields to audit_log_entries.

Revision ID: 20260228_0001
Revises:
Create Date: 2026-02-28 00:00:00.000000
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha512
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

# revision identifiers, used by Alembic.
revision = '20260228_0001'
down_revision = None
branch_labels = None
depends_on = None


def _as_utc_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        else:
            value = value.astimezone(UTC)
        return value.isoformat()
    return str(value)


def _build_entry_hash(
    chain_index: int,
    prev_hash: str | None,
    created_at: Any,
    event_id: str,
    action: str,
    resource: str,
    resource_id: str | None,
    actor_key_id: str | None,
    actor_role: str | None,
    status: str | None,
    reason: str | None,
) -> str:
    payload = {
        'chain_index': chain_index,
        'prev_hash': prev_hash,
        'created_at': _as_utc_iso(created_at),
        'event_id': event_id,
        'action': action,
        'resource': resource,
        'resource_id': resource_id,
        'actor_key_id': actor_key_id,
        'actor_role': actor_role,
        'status': status,
        'reason': reason,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return sha512(canonical.encode()).hexdigest()


def _has_column(connection: Connection, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(connection)
    return any(col['name'] == column_name for col in inspector.get_columns(table_name))


def _has_unique(connection: Connection, table_name: str, constraint_name: str) -> bool:
    inspector = sa.inspect(connection)
    return any(
        item['name'] == constraint_name
        for item in inspector.get_unique_constraints(table_name)
    )


def _has_index(connection: Connection, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(connection)
    return any(item['name'] == index_name for item in inspector.get_indexes(table_name))


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if 'audit_log_entries' not in inspector.get_table_names():
        return

    if not _has_column(connection, 'audit_log_entries', 'chain_index'):
        op.add_column(
            'audit_log_entries',
            sa.Column('chain_index', sa.Integer(), nullable=True),
        )
    if not _has_column(connection, 'audit_log_entries', 'prev_hash'):
        op.add_column(
            'audit_log_entries',
            sa.Column('prev_hash', sa.String(length=128), nullable=True),
        )
    if not _has_column(connection, 'audit_log_entries', 'entry_hash'):
        op.add_column(
            'audit_log_entries',
            sa.Column('entry_hash', sa.String(length=128), nullable=True),
        )

    rows = connection.execute(
        sa.text(
            """
            SELECT id, created_at, event_id, action, resource, resource_id,
                   actor_key_id, actor_role, status, reason
            FROM audit_log_entries
            ORDER BY created_at ASC, id ASC
            """,
        ),
    ).mappings().all()

    prev_hash: str | None = None
    for chain_index, row in enumerate(rows, start=1):
        entry_hash = _build_entry_hash(
            chain_index=chain_index,
            prev_hash=prev_hash,
            created_at=row['created_at'],
            event_id=row['event_id'],
            action=row['action'],
            resource=row['resource'],
            resource_id=row['resource_id'],
            actor_key_id=row['actor_key_id'],
            actor_role=row['actor_role'],
            status=row['status'],
            reason=row['reason'],
        )
        connection.execute(
            sa.text(
                """
                UPDATE audit_log_entries
                SET chain_index = :chain_index,
                    prev_hash = :prev_hash,
                    entry_hash = :entry_hash
                WHERE id = :id
                """,
            ),
            {
                'chain_index': chain_index,
                'prev_hash': prev_hash,
                'entry_hash': entry_hash,
                'id': row['id'],
            },
        )
        prev_hash = entry_hash

    op.alter_column('audit_log_entries', 'chain_index', nullable=False)
    op.alter_column('audit_log_entries', 'entry_hash', nullable=False)

    if not _has_unique(connection, 'audit_log_entries', 'uq_audit_log_entries_chain_index'):
        op.create_unique_constraint(
            'uq_audit_log_entries_chain_index',
            'audit_log_entries',
            ['chain_index'],
        )
    if not _has_unique(connection, 'audit_log_entries', 'uq_audit_log_entries_entry_hash'):
        op.create_unique_constraint(
            'uq_audit_log_entries_entry_hash',
            'audit_log_entries',
            ['entry_hash'],
        )
    if not _has_index(connection, 'audit_log_entries', 'ix_audit_log_entries_chain_index'):
        op.create_index(
            'ix_audit_log_entries_chain_index',
            'audit_log_entries',
            ['chain_index'],
            unique=False,
        )
    if not _has_index(connection, 'audit_log_entries', 'ix_audit_log_entries_entry_hash'):
        op.create_index(
            'ix_audit_log_entries_entry_hash',
            'audit_log_entries',
            ['entry_hash'],
            unique=False,
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if 'audit_log_entries' not in inspector.get_table_names():
        return

    if _has_index(connection, 'audit_log_entries', 'ix_audit_log_entries_entry_hash'):
        op.drop_index('ix_audit_log_entries_entry_hash', table_name='audit_log_entries')
    if _has_index(connection, 'audit_log_entries', 'ix_audit_log_entries_chain_index'):
        op.drop_index('ix_audit_log_entries_chain_index', table_name='audit_log_entries')
    if _has_unique(connection, 'audit_log_entries', 'uq_audit_log_entries_entry_hash'):
        op.drop_constraint(
            'uq_audit_log_entries_entry_hash',
            'audit_log_entries',
            type_='unique',
        )
    if _has_unique(connection, 'audit_log_entries', 'uq_audit_log_entries_chain_index'):
        op.drop_constraint(
            'uq_audit_log_entries_chain_index',
            'audit_log_entries',
            type_='unique',
        )
    if _has_column(connection, 'audit_log_entries', 'entry_hash'):
        op.drop_column('audit_log_entries', 'entry_hash')
    if _has_column(connection, 'audit_log_entries', 'prev_hash'):
        op.drop_column('audit_log_entries', 'prev_hash')
    if _has_column(connection, 'audit_log_entries', 'chain_index'):
        op.drop_column('audit_log_entries', 'chain_index')
