from __future__ import annotations

import secrets
from collections.abc import Mapping
from hashlib import sha512
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import get_api_keys_repository, get_audit_service, get_request_id
from app.infrastructure.db.models.api_key import ApiKeyModel
from app.repositories.api_keys_repository import ApiKeysRepository
from app.schemas.admin import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyResponse
from app.services.audit_service import AuditService

router = APIRouter()


def _success_payload(data: Mapping[str, object], request_id: str) -> dict[str, object]:
    return {'data': data, 'meta': {'request_id': request_id}}


def _error_payload(code: str, message: str, request_id: str) -> dict[str, object]:
    return {
        'error': {'code': code, 'message': message},
        'data': None,
        'meta': {'request_id': request_id},
    }


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
