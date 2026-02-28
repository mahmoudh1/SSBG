from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class AlertModel(Base):
    __tablename__ = 'alerts'
    __table_args__ = (
        UniqueConstraint('dedupe_key', name='uq_alerts_dedupe_key'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    rule_id: Mapped[str] = mapped_column(String(100), index=True)
    severity: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default='OPEN')
    source_event: Mapped[str] = mapped_column(String(100), index=True)
    actor_key_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    related_backup_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reason: Mapped[str] = mapped_column(String(255))
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
    )
