from __future__ import annotations

from collections.abc import Mapping

from fastapi import APIRouter, Depends

from app.api.dependencies import get_backup_service, get_request_id
from app.schemas.backups import BackupRequest
from app.services.backup_service import BackupService

router = APIRouter()


def _success_payload(data: Mapping[str, object], request_id: str) -> dict[str, object]:
    return {'data': data, 'meta': {'request_id': request_id}}


@router.post('')
async def submit_backup(
    payload: BackupRequest,
    request_id: str = Depends(get_request_id),
    backup_service: BackupService = Depends(get_backup_service),
) -> dict[str, object]:
    data = await backup_service.submit_backup(payload)
    return _success_payload(data=data, request_id=request_id)
