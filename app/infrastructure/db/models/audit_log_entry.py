from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class AuditLogEntryModel(Base):
    __tablename__ = 'audit_log_entries'
    __table_args__ = (
        UniqueConstraint('chain_index', name='uq_audit_log_entries_chain_index'),
        UniqueConstraint('entry_hash', name='uq_audit_log_entries_entry_hash'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chain_index: Mapped[int] = mapped_column(Integer, index=True)
    prev_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    entry_hash: Mapped[str] = mapped_column(String(128), index=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource: Mapped[str] = mapped_column(String(200), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_key_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
