from __future__ import annotations

from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import get_audit_service, get_incident_service, get_request_id
from app.core.enums import IncidentLevel
from app.schemas.admin import IncidentStateResponse, IncidentTransitionRequest
from app.services.audit_service import AuditService
from app.services.incident_service import IncidentService, InvalidIncidentTransition

router = APIRouter()


def _success_payload(data: Mapping[str, object], request_id: str) -> dict[str, object]:
    return {'data': data, 'meta': {'request_id': request_id}}


def _error_payload(
    code: str,
    message: str,
    request_id: str,
    details: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        'error': {'code': code, 'message': message},
        'data': {'details': details or []},
        'meta': {'request_id': request_id},
    }


@router.get('')
async def get_incident_state(
    request: Request,
    request_id: str = Depends(get_request_id),
    incident_service: IncidentService = Depends(get_incident_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, object]:
    state = await incident_service.get_state()
    principal = getattr(request.state, 'principal', None)
    await audit_service.record_admin_action(
        actor_key_id=principal.key_id if principal else None,
        action='incident_state_viewed',
        resource='incident',
        resource_id=None,
        client_ip=request.client.host if request.client else None,
    )
    response = IncidentStateResponse(
        level=state.level.value,
        changed_by_key_id=state.changed_by_key_id,
        reason=state.reason,
        changed_at=state.changed_at,
    )
    return _success_payload(data=response.model_dump(mode='json'), request_id=request_id)


@router.put('')
async def update_incident_state(
    payload: IncidentTransitionRequest,
    request: Request,
    request_id: str = Depends(get_request_id),
    incident_service: IncidentService = Depends(get_incident_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, object]:
    principal = getattr(request.state, 'principal', None)
    try:
        new_level = IncidentLevel(payload.level)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=_error_payload(
                code='INCIDENT_TRANSITION_INVALID',
                message='Invalid incident level',
                request_id=request_id,
                details=[{'reason_category': 'invalid_level'}],
            ),
        ) from exc
    try:
        updated = await incident_service.transition_to(
            new_level=new_level,
            changed_by_key_id=principal.key_id if principal else None,
            reason=payload.reason,
        )
    except InvalidIncidentTransition as exc:
        raise HTTPException(
            status_code=400,
            detail=_error_payload(
                code='INCIDENT_TRANSITION_INVALID',
                message=exc.message,
                request_id=request_id,
                details=[{'reason_category': exc.reason_category}],
            ),
        ) from exc
    await audit_service.record_admin_action(
        actor_key_id=principal.key_id if principal else None,
        action='incident_level_changed',
        resource='incident',
        resource_id=updated.level.value,
        client_ip=request.client.host if request.client else None,
    )
    response = IncidentStateResponse(
        level=updated.level.value,
        changed_by_key_id=updated.changed_by_key_id,
        reason=updated.reason,
        changed_at=updated.changed_at,
    )
    return _success_payload(data=response.model_dump(mode='json'), request_id=request_id)
