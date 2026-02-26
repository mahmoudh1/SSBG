from __future__ import annotations

from collections.abc import Mapping
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import get_audit_service, get_policies_repository, get_request_id
from app.infrastructure.db.models.policy_record import PolicyRecordModel
from app.repositories.policies_repository import PoliciesRepository
from app.schemas.admin import PolicyCreateRequest, PolicyResponse, PolicyUpdateRequest
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


def _policy_to_response(record: PolicyRecordModel) -> PolicyResponse:
    return PolicyResponse(
        policy_id=record.policy_id,
        name=record.name,
        description=record.description,
        rule_json=record.rule_json,
        is_active=record.is_active,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post('')
async def create_policy(
    payload: PolicyCreateRequest,
    request: Request,
    request_id: str = Depends(get_request_id),
    repository: PoliciesRepository = Depends(get_policies_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, object]:
    record = PolicyRecordModel(
        policy_id=uuid4().hex,
        name=payload.name,
        description=payload.description,
        rule_json=payload.rule_json,
        is_active=payload.is_active,
    )
    record = await repository.create_policy(record)
    actor_key_id = getattr(request.state, 'principal', None)
    await audit_service.record_admin_action(
        actor_key_id=actor_key_id.key_id if actor_key_id else None,
        action='policy_created',
        resource='policy',
        resource_id=record.policy_id,
        client_ip=request.client.host if request.client else None,
    )
    data = {'policy': _policy_to_response(record).model_dump()}
    return _success_payload(data=data, request_id=request_id)


@router.get('')
async def list_policies(
    request: Request,
    request_id: str = Depends(get_request_id),
    repository: PoliciesRepository = Depends(get_policies_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, object]:
    records = await repository.list_policies()
    actor_key_id = getattr(request.state, 'principal', None)
    await audit_service.record_admin_action(
        actor_key_id=actor_key_id.key_id if actor_key_id else None,
        action='policy_listed',
        resource='policy',
        resource_id=None,
        client_ip=request.client.host if request.client else None,
    )
    data = {'policies': [_policy_to_response(record).model_dump() for record in records]}
    return _success_payload(data=data, request_id=request_id)


@router.put('/{policy_id}')
async def update_policy(
    policy_id: str,
    payload: PolicyUpdateRequest,
    request: Request,
    request_id: str = Depends(get_request_id),
    repository: PoliciesRepository = Depends(get_policies_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, object]:
    record = await repository.update_policy(
        policy_id=policy_id,
        name=payload.name,
        description=payload.description,
        rule_json=payload.rule_json,
        is_active=payload.is_active,
    )
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=_error_payload(
                code='POLICY_NOT_FOUND',
                message='Policy not found',
                request_id=request_id,
            ),
        )
    actor_key_id = getattr(request.state, 'principal', None)
    await audit_service.record_admin_action(
        actor_key_id=actor_key_id.key_id if actor_key_id else None,
        action='policy_updated',
        resource='policy',
        resource_id=record.policy_id,
        client_ip=request.client.host if request.client else None,
    )
    data = {'policy': _policy_to_response(record).model_dump()}
    return _success_payload(data=data, request_id=request_id)
