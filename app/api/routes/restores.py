from __future__ import annotations

from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import (
    get_app_settings,
    get_request_id,
    get_restore_access_token_service,
    get_restore_service,
)
from app.core.config import Settings
from app.schemas.restores import RestoreRequest
from app.services.auth_service import MfaFailure
from app.services.restore_access_token_service import (
    RestoreAccessTokenExpired,
    RestoreAccessTokenForbidden,
    RestoreAccessTokenInvalid,
    RestoreAccessTokenService,
)
from app.services.restore_service import (
    RestoreExecutionUnavailable,
    RestoreIncidentRestricted,
    RestoreIntegrityFailed,
    RestoreIrreversible,
    RestoreMetadataNotFound,
    RestorePolicyDenied,
    RestoreService,
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
async def submit_restore(
    payload: RestoreRequest,
    request: Request,
    request_id: str = Depends(get_request_id),
    settings: Settings = Depends(get_app_settings),
    restore_service: RestoreService = Depends(get_restore_service),
) -> dict[str, object]:
    try:
        principal = getattr(request.state, 'principal', None)
        client_ip = request.client.host if request.client else None
        mfa_token = request.headers.get(settings.mfa_header)
        data = await restore_service.load_restore_metadata(payload, principal, client_ip, mfa_token)
    except MfaFailure as exc:
        raise HTTPException(
            status_code=401,
            detail=_error_payload(
                code=exc.code,
                message=exc.message,
                request_id=request_id,
                details=[],
            ),
        ) from exc
    except RestoreMetadataNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=_error_payload(
                code='RESTORE_BACKUP_NOT_FOUND',
                message='Backup metadata not found',
                request_id=request_id,
                details=[{'backup_id': exc.backup_id}],
            ),
        ) from exc
    except RestorePolicyDenied as exc:
        raise HTTPException(
            status_code=403,
            detail=_error_payload(
                code='POLICY_DENIED',
                message=exc.message,
                request_id=request_id,
                details=[{'reason_category': exc.reason_category}],
            ),
        ) from exc
    except RestoreIncidentRestricted as exc:
        raise HTTPException(
            status_code=403,
            detail=_error_payload(
                code='RESTORE_RESTRICTED',
                message=exc.message,
                request_id=request_id,
                details=[{'reason_category': exc.reason_category}],
            ),
        ) from exc
    except RestoreIrreversible as exc:
        raise HTTPException(
            status_code=410,
            detail=_error_payload(
                code='RESTORE_IRREVERSIBLE',
                message=exc.message,
                request_id=request_id,
                details=[{'reason_category': exc.reason_category}],
            ),
        ) from exc
    except RestoreIntegrityFailed as exc:
        raise HTTPException(
            status_code=409,
            detail=_error_payload(
                code='RESTORE_INTEGRITY_FAILED',
                message=exc.message,
                request_id=request_id,
                details=[],
            ),
        ) from exc
    except RestoreExecutionUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail=_error_payload(
                code='RESTORE_UNAVAILABLE',
                message=exc.message,
                request_id=request_id,
                details=[],
            ),
        ) from exc
    return _success_payload(data=data, request_id=request_id)


@router.get('/access/{restore_token}')
async def use_restore_access_token(
    restore_token: str,
    request: Request,
    request_id: str = Depends(get_request_id),
    token_service: RestoreAccessTokenService = Depends(get_restore_access_token_service),
) -> dict[str, object]:
    try:
        principal = getattr(request.state, 'principal', None)
        actor_key_id = principal.key_id if principal is not None else None
        record = token_service.validate_token(restore_token, actor_key_id=actor_key_id)
    except RestoreAccessTokenExpired as exc:
        raise HTTPException(
            status_code=401,
            detail=_error_payload(
                code='RESTORE_TOKEN_EXPIRED',
                message=exc.message,
                request_id=request_id,
                details=[],
            ),
        ) from exc
    except RestoreAccessTokenForbidden as exc:
        raise HTTPException(
            status_code=403,
            detail=_error_payload(
                code='RESTORE_TOKEN_FORBIDDEN',
                message=exc.message,
                request_id=request_id,
                details=[],
            ),
        ) from exc
    except RestoreAccessTokenInvalid as exc:
        raise HTTPException(
            status_code=401,
            detail=_error_payload(
                code='RESTORE_TOKEN_INVALID',
                message=exc.message,
                request_id=request_id,
                details=[],
            ),
        ) from exc
    return _success_payload(
        data={
            'status': 'restore_access_granted',
            'backup_id': record.backup_id,
            'expires_at': record.expires_at.isoformat(),
        },
        request_id=request_id,
    )
