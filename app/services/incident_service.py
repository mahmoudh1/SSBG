from __future__ import annotations

from app.core.config import Settings
from app.core.enums import IncidentLevel


class IncidentService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_current_level(self) -> IncidentLevel:
        try:
            return IncidentLevel(self._settings.current_incident_level)
        except ValueError:
            return IncidentLevel.NORMAL
