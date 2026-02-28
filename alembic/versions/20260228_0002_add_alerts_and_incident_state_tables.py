"""Add alerts and incident_states tables for monitoring and incident workflows.

Revision ID: 20260228_0002
Revises: 20260228_0001
Create Date: 2026-02-28 00:10:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '20260228_0002'
down_revision = '20260228_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'alerts' not in tables:
        op.create_table(
            'alerts',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('alert_id', sa.String(length=64), nullable=False),
            sa.Column('rule_id', sa.String(length=100), nullable=False),
            sa.Column('severity', sa.String(length=32), nullable=False),
            sa.Column('status', sa.String(length=32), nullable=False),
            sa.Column('source_event', sa.String(length=100), nullable=False),
            sa.Column('actor_key_id', sa.String(length=64), nullable=True),
            sa.Column('related_backup_id', sa.String(length=64), nullable=True),
            sa.Column('reason', sa.String(length=255), nullable=False),
            sa.Column('metadata_json', sa.Text(), nullable=True),
            sa.Column('dedupe_key', sa.String(length=255), nullable=False),
            sa.Column(
                'created_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('CURRENT_TIMESTAMP'),
                nullable=False,
            ),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('alert_id'),
            sa.UniqueConstraint('dedupe_key', name='uq_alerts_dedupe_key'),
        )
        op.create_index('ix_alerts_alert_id', 'alerts', ['alert_id'], unique=True)
        op.create_index('ix_alerts_rule_id', 'alerts', ['rule_id'], unique=False)
        op.create_index('ix_alerts_severity', 'alerts', ['severity'], unique=False)
        op.create_index('ix_alerts_status', 'alerts', ['status'], unique=False)
        op.create_index('ix_alerts_source_event', 'alerts', ['source_event'], unique=False)
        op.create_index('ix_alerts_actor_key_id', 'alerts', ['actor_key_id'], unique=False)
        op.create_index(
            'ix_alerts_related_backup_id',
            'alerts',
            ['related_backup_id'],
            unique=False,
        )
        op.create_index('ix_alerts_dedupe_key', 'alerts', ['dedupe_key'], unique=False)

    if 'incident_states' not in tables:
        op.create_table(
            'incident_states',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('level', sa.String(length=32), nullable=False),
            sa.Column('changed_by_key_id', sa.String(length=64), nullable=True),
            sa.Column('reason', sa.String(length=255), nullable=True),
            sa.Column(
                'changed_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('CURRENT_TIMESTAMP'),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_incident_states_level', 'incident_states', ['level'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'incident_states' in tables:
        indexes = {idx['name'] for idx in inspector.get_indexes('incident_states')}
        if 'ix_incident_states_level' in indexes:
            op.drop_index('ix_incident_states_level', table_name='incident_states')
        op.drop_table('incident_states')

    if 'alerts' in tables:
        indexes = {idx['name'] for idx in inspector.get_indexes('alerts')}
        for index_name in (
            'ix_alerts_dedupe_key',
            'ix_alerts_related_backup_id',
            'ix_alerts_actor_key_id',
            'ix_alerts_source_event',
            'ix_alerts_status',
            'ix_alerts_severity',
            'ix_alerts_rule_id',
            'ix_alerts_alert_id',
        ):
            if index_name in indexes:
                op.drop_index(index_name, table_name='alerts')
        op.drop_table('alerts')
