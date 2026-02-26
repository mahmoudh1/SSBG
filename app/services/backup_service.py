from __future__ import annotations

from app.schemas.backups import BackupRequest


class BackupService:
    async def submit_backup(self, request: BackupRequest) -> dict[str, object]:
        return {
            'status': 'accepted',
            'classification': request.classification.value,
            'source_system': request.source_system,
        }
