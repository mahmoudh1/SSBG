from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class IncidentStateModel(Base):
    __tablename__ = 'incident_states'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
