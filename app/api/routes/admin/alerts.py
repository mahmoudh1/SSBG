from __future__ import annotations

from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import get_alerts_repository, get_audit_service, get_request_id
from app.core.enums import AlertStatus
from app.infrastructure.db.models.alert import AlertModel
from app.repositories.alerts_repository import AlertsRepository
from app.schemas.admin import AlertResponse, AlertStatusUpdateRequest
from app.services.audit_service import AuditService

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


def _to_alert_response(record: AlertModel) -> AlertResponse:
    return AlertResponse(
        alert_id=record.alert_id,
        rule_id=record.rule_id,
        severity=record.severity,
        status=record.status,
        source_event=record.source_event,
        actor_key_id=record.actor_key_id,
        related_backup_id=record.related_backup_id,
        reason=record.reason,
        metadata_json=record.metadata_json,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get('')
async def list_alerts(
    request: Request,
    request_id: str = Depends(get_request_id),
    repository: AlertsRepository = Depends(get_alerts_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, object]:
    records = await repository.list_alerts()
    principal = getattr(request.state, 'principal', None)
    await audit_service.record_admin_action(
        actor_key_id=principal.key_id if principal else None,
        action='alert_reviewed',
        resource='alert',
        resource_id=None,
        client_ip=request.client.host if request.client else None,
    )
    return _success_payload(
        data={'alerts': [_to_alert_response(record).model_dump(mode='json') for record in records]},
        request_id=request_id,
    )


@router.put('/{alert_id}/status')
async def update_alert_status(
    alert_id: str,
    payload: AlertStatusUpdateRequest,
    request: Request,
    request_id: str = Depends(get_request_id),
    repository: AlertsRepository = Depends(get_alerts_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, object]:
    try:
        new_status = AlertStatus(payload.status)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=_error_payload(
                code='ALERT_STATUS_INVALID',
                message='Invalid alert status',
                request_id=request_id,
                details=[{'allowed': [status.value for status in AlertStatus]}],
            ),
        ) from exc
    updated = await repository.update_status(alert_id, new_status.value)
    if updated is None:
        raise HTTPException(
            status_code=404,
            detail=_error_payload(
                code='ALERT_NOT_FOUND',
                message='Alert not found',
                request_id=request_id,
            ),
        )
    principal = getattr(request.state, 'principal', None)
    await audit_service.record_admin_action(
        actor_key_id=principal.key_id if principal else None,
        action='alert_status_updated',
        resource='alert',
        resource_id=updated.alert_id,
        client_ip=request.client.host if request.client else None,
    )
    return _success_payload(
        data={'alert': _to_alert_response(updated).model_dump(mode='json')},
        request_id=request_id,
    )
