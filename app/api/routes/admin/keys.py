from __future__ import annotations

import secrets
from collections.abc import Mapping
from datetime import datetime
from hashlib import sha512
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import (
    get_api_keys_repository,
    get_app_settings,
    get_audit_service,
    get_key_management_service,
    get_request_id,
)
from app.core.config import Settings
from app.infrastructure.db.models.api_key import ApiKeyModel
from app.repositories.api_keys_repository import ApiKeysRepository
from app.schemas.admin import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyResponse,
    CryptoShredOutcomeResponse,
    CryptoShredRequest,
    CryptoShredResponse,
    KeyRotationRequest,
    KeyVersionResponse,
)
from app.services.audit_service import AuditService
from app.services.key_management_service import (
    CryptoShredError,
    KeyManagementService,
    KeyRotationError,
    KeyVersionNotFoundError,
    KeyVersionSnapshot,
)

router = APIRouter()


def _success_payload(data: Mapping[str, object], request_id: str) -> dict[str, object]:
    return {'data': data, 'meta': {'request_id': request_id}}


def _error_payload(code: str, message: str, request_id: str) -> dict[str, object]:
    return {
        'error': {'code': code, 'message': message},
        'data': None,
        'meta': {'request_id': request_id},
    }


def _as_int(value: object) -> int:
    return value if isinstance(value, int) else 0


def _key_to_response(record: ApiKeyModel) -> ApiKeyResponse:
    return ApiKeyResponse(
        key_id=record.key_id,
        key_prefix=record.key_prefix,
        role=record.role,
        department=record.department,
        description=record.description,
        created_at=record.created_at,
        expires_at=record.expires_at,
        is_active=record.is_active,
        allowed_ips=record.allowed_ips,
    )


def _version_to_response(version: KeyVersionSnapshot) -> KeyVersionResponse:
    return KeyVersionResponse(
        version_id=version.version_id,
        is_active=version.is_active,
        is_destroyed=version.is_destroyed,
        rotated_from_version=version.rotated_from_version,
        created_by_key_id=version.created_by_key_id,
        rotation_reason=version.rotation_reason,
        created_at=version.created_at,
        activated_at=version.activated_at,
        destroyed_at=version.destroyed_at,
    )


@router.post('')
async def create_key(
    payload: ApiKeyCreateRequest,
    request: Request,
    request_id: str = Depends(get_request_id),
    repository: ApiKeysRepository = Depends(get_api_keys_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, object]:
    raw_key = secrets.token_urlsafe(32)
    key_id = uuid4().hex
    key_prefix = raw_key[:8]
    key_hash = sha512(raw_key.encode()).hexdigest()
    record = ApiKeyModel(
        key_id=key_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        role=payload.role,
        department=payload.department,
        description=payload.description,
        expires_at=payload.expires_at,
        allowed_ips=payload.allowed_ips,
        is_active=True,
    )
    record = await repository.create_key(record)
    actor_key_id = getattr(request.state, 'principal', None)
    await audit_service.record_admin_action(
        actor_key_id=actor_key_id.key_id if actor_key_id else None,
        action='api_key_created',
        resource='api_key',
        resource_id=record.key_id,
        client_ip=request.client.host if request.client else None,
    )
    data = ApiKeyCreateResponse(api_key=raw_key, key=_key_to_response(record))
    return _success_payload(data=data.model_dump(), request_id=request_id)


@router.get('')
async def list_keys(
    request: Request,
    request_id: str = Depends(get_request_id),
    repository: ApiKeysRepository = Depends(get_api_keys_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, object]:
    records = await repository.list_keys()
    actor_key_id = getattr(request.state, 'principal', None)
    await audit_service.record_admin_action(
        actor_key_id=actor_key_id.key_id if actor_key_id else None,
        action='api_key_listed',
        resource='api_key',
        resource_id=None,
        client_ip=request.client.host if request.client else None,
    )
    data = {'keys': [_key_to_response(record).model_dump() for record in records]}
    return _success_payload(data=data, request_id=request_id)


@router.post('/{key_id}/revoke')
async def revoke_key(
    key_id: str,
    request: Request,
    request_id: str = Depends(get_request_id),
    repository: ApiKeysRepository = Depends(get_api_keys_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, object]:
    record = await repository.revoke_key(key_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=_error_payload(
                code='API_KEY_NOT_FOUND',
                message='API key not found',
                request_id=request_id,
            ),
        )
    actor_key_id = getattr(request.state, 'principal', None)
    await audit_service.record_admin_action(
        actor_key_id=actor_key_id.key_id if actor_key_id else None,
        action='api_key_revoked',
        resource='api_key',
        resource_id=record.key_id,
        client_ip=request.client.host if request.client else None,
    )
    data = {'key': _key_to_response(record).model_dump()}
    return _success_payload(data=data, request_id=request_id)


@router.get('/versions')
async def list_key_versions(
    request: Request,
    request_id: str = Depends(get_request_id),
    key_management_service: KeyManagementService = Depends(get_key_management_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, object]:
    versions = await key_management_service.list_versions()
    actor_key_id = getattr(request.state, 'principal', None)
    await audit_service.record_admin_action(
        actor_key_id=actor_key_id.key_id if actor_key_id else None,
        action='key_versions_reviewed',
        resource='key_version',
        resource_id=None,
        client_ip=request.client.host if request.client else None,
    )
    data = {
        'versions': [
            _version_to_response(version).model_dump(mode='json') for version in versions
        ],
    }
    return _success_payload(data=data, request_id=request_id)


@router.post('/versions/rotate')
async def rotate_key_version(
    payload: KeyRotationRequest,
    request: Request,
    request_id: str = Depends(get_request_id),
    key_management_service: KeyManagementService = Depends(get_key_management_service),
) -> dict[str, object]:
    actor = getattr(request.state, 'principal', None)
    try:
        rotated = await key_management_service.rotate_active_version(
            to_version_id=payload.to_version_id,
            actor_key_id=actor.key_id if actor else None,
            reason=payload.reason,
            client_ip=request.client.host if request.client else None,
        )
    except KeyRotationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                'error': {'code': 'KEY_ROTATION_INVALID', 'message': exc.message},
                'data': {'details': [{'reason_category': exc.reason_category}]},
                'meta': {'request_id': request_id},
            },
        ) from exc
    data = {'version': _version_to_response(rotated).model_dump(mode='json')}
    return _success_payload(data=data, request_id=request_id)


@router.post('/versions/{version_id}/crypto-shred')
async def crypto_shred_key_version(
    version_id: str,
    payload: CryptoShredRequest,
    request: Request,
    request_id: str = Depends(get_request_id),
    settings: Settings = Depends(get_app_settings),
    key_management_service: KeyManagementService = Depends(get_key_management_service),
) -> dict[str, object]:
    principal = getattr(request.state, 'principal', None)
    mfa_token = request.headers.get(settings.mfa_header)
    try:
        result = await key_management_service.execute_crypto_shred(
            version_id=version_id,
            principal=principal,
            mfa_token=mfa_token,
            confirmation=payload.confirmation,
            client_ip=request.client.host if request.client else None,
        )
    except CryptoShredError as exc:
        status_code = 404 if exc.reason_category == 'key_not_found' else 403
        raise HTTPException(
            status_code=status_code,
            detail={
                'error': {'code': 'CRYPTO_SHRED_DENIED', 'message': exc.message},
                'data': {'details': [{'reason_category': exc.reason_category}]},
                'meta': {'request_id': request_id},
            },
        ) from exc
    affected_raw = result.get('affected_backups')
    affected_backups = affected_raw if isinstance(affected_raw, int) else 0
    response = CryptoShredResponse(
        version_id=str(result['version_id']),
        destroyed=bool(result['destroyed']),
        affected_backups=affected_backups,
        incident_effect=str(result['incident_effect']),
    )
    return _success_payload(data=response.model_dump(mode='json'), request_id=request_id)


@router.get('/versions/{version_id}')
async def get_key_version(
    version_id: str,
    request: Request,
    request_id: str = Depends(get_request_id),
    key_management_service: KeyManagementService = Depends(get_key_management_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, object]:
    try:
        version = await key_management_service.get_version(version_id)
    except KeyVersionNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=_error_payload(
                code='KEY_VERSION_NOT_FOUND',
                message='Key version not found',
                request_id=request_id,
            ),
        ) from exc
    actor_key_id = getattr(request.state, 'principal', None)
    await audit_service.record_admin_action(
        actor_key_id=actor_key_id.key_id if actor_key_id else None,
        action='key_version_reviewed',
        resource='key_version',
        resource_id=version_id,
        client_ip=request.client.host if request.client else None,
    )
    data = {'version': _version_to_response(version).model_dump(mode='json')}
    return _success_payload(data=data, request_id=request_id)


@router.get('/versions/{version_id}/crypto-shred-outcome')
async def get_crypto_shred_outcome(
    version_id: str,
    request: Request,
    request_id: str = Depends(get_request_id),
    key_management_service: KeyManagementService = Depends(get_key_management_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, object]:
    try:
        outcome = await key_management_service.get_crypto_shred_outcome(version_id)
    except KeyVersionNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=_error_payload(
                code='KEY_VERSION_NOT_FOUND',
                message='Key version not found',
                request_id=request_id,
            ),
        ) from exc
    actor_key_id = getattr(request.state, 'principal', None)
    await audit_service.record_admin_action(
        actor_key_id=actor_key_id.key_id if actor_key_id else None,
        action='crypto_shred_outcome_reviewed',
        resource='key_version',
        resource_id=version_id,
        client_ip=request.client.host if request.client else None,
    )
    destroyed_at_raw = outcome.get('destroyed_at')
    destroyed_at = destroyed_at_raw if isinstance(destroyed_at_raw, datetime) else None
    last_shredded_raw = outcome.get('last_shredded_at')
    last_shredded_at = last_shredded_raw if isinstance(last_shredded_raw, datetime) else None
    response = CryptoShredOutcomeResponse(
        version_id=str(outcome['version_id']),
        key_destroyed=bool(outcome['key_destroyed']),
        destroyed_at=destroyed_at,
        total_backups=_as_int(outcome.get('total_backups')),
        irreversible_backups=_as_int(outcome.get('irreversible_backups')),
        active_backups=_as_int(outcome.get('active_backups')),
        processing_backups=_as_int(outcome.get('processing_backups')),
        failed_backups=_as_int(outcome.get('failed_backups')),
        last_shredded_at=last_shredded_at,
        irreversible_reason=(
            str(outcome['irreversible_reason'])
            if outcome.get('irreversible_reason') is not None
            else None
        ),
    )
    return _success_payload(data=response.model_dump(mode='json'), request_id=request_id)
