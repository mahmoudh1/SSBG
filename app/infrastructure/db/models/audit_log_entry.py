from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class AuditLogEntryModel(Base):
    __tablename__ = 'audit_log_entries'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
