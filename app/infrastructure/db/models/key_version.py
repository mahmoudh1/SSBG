from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class KeyVersionModel(Base):
    __tablename__ = 'key_versions'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
