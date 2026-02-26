from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class BackupMetadataModel(Base):
    __tablename__ = 'backup_metadata'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    backup_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    key_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    classification: Mapped[str] = mapped_column(String(32), index=True)
    source_system: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    checksum_plaintext: Mapped[str | None] = mapped_column(String(128), nullable=True)
    checksum_ciphertext: Mapped[str | None] = mapped_column(String(128), nullable=True)
    nonce: Mapped[str | None] = mapped_column(String(64), nullable=True)
    original_size: Mapped[int | None] = mapped_column(nullable=True)
    encrypted_size: Mapped[int | None] = mapped_column(nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
