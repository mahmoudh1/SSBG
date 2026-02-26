from __future__ import annotations

from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import get_backup_service, get_request_id
from app.schemas.backups import BackupRequest
from app.services.backup_service import (
    BackupPolicyDenied,
    BackupProcessingError,
    BackupService,
    BackupValidationError,
)

router = APIRouter()


def _success_payload(data: Mapping[str, object], request_id: str) -> dict[str, object]:
    return {'data': data, 'meta': {'request_id': request_id}}


def _error_payload(
    code: str,
    message: str,
    request_id: str,
    details: list[dict[str, object]],
) -> dict[str, object]:
    return {
        'error': {'code': code, 'message': message},
        'data': {'details': details},
        'meta': {'request_id': request_id},
    }


@router.post('')
async def submit_backup(
    payload: BackupRequest,
    request: Request,
    request_id: str = Depends(get_request_id),
    backup_service: BackupService = Depends(get_backup_service),
) -> dict[str, object]:
    try:
        principal = getattr(request.state, 'principal', None)
        client_ip = request.client.host if request.client else None
        data = await backup_service.submit_backup(payload, principal, client_ip)
    except BackupValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=_error_payload(
                code='VALIDATION_ERROR',
                message=exc.message,
                request_id=request_id,
                details=exc.details,
            ),
        ) from exc
    except BackupPolicyDenied as exc:
        raise HTTPException(
            status_code=403,
            detail=_error_payload(
                code='POLICY_DENIED',
                message=exc.message,
                request_id=request_id,
                details=[{'reason_category': exc.reason_category}],
            ),
        ) from exc
    except BackupProcessingError as exc:
        raise HTTPException(
            status_code=500,
            detail=_error_payload(
                code=exc.code,
                message=exc.message,
                request_id=request_id,
                details=[],
            ),
        ) from exc
    return _success_payload(data=data, request_id=request_id)
