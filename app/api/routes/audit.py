from collections.abc import Mapping

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import get_audit_service, get_request_id
from app.services.audit_service import AuditService

router = APIRouter()


def _success_payload(data: Mapping[str, object], request_id: str) -> dict[str, object]:
    return {'data': data, 'meta': {'request_id': request_id}}


@router.get('/chain/validate')
async def validate_audit_chain(
    request_id: str = Depends(get_request_id),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, object]:
    result = await audit_service.validate_chain()
    return _success_payload(data=result.model_dump(mode='json'), request_id=request_id)


@router.get('/entries')
async def list_audit_entries(
    request: Request,
    request_id: str = Depends(get_request_id),
    audit_service: AuditService = Depends(get_audit_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    action: str | None = Query(default=None),
    resource: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> dict[str, object]:
    entries = await audit_service.list_audit_entries(
        offset=offset,
        limit=limit,
        action=action,
        resource=resource,
        status=status,
    )
    principal = getattr(request.state, 'principal', None)
    await audit_service.record_admin_action(
        actor_key_id=principal.key_id if principal else None,
        action='audit_review_accessed',
        resource='audit',
        resource_id=None,
        client_ip=request.client.host if request.client else None,
    )
    return _success_payload(
        data={
            'entries': [entry.model_dump(mode='json') for entry in entries],
            'paging': {'offset': offset, 'limit': limit},
            'filters': {'action': action, 'resource': resource, 'status': status},
        },
        request_id=request_id,
    )


@router.get('/summary')
async def get_audit_validation_summary(
    request: Request,
    request_id: str = Depends(get_request_id),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, object]:
    result = await audit_service.validate_chain()
    principal = getattr(request.state, 'principal', None)
    await audit_service.record_admin_action(
        actor_key_id=principal.key_id if principal else None,
        action='audit_validation_reviewed',
        resource='audit',
        resource_id=None,
        client_ip=request.client.host if request.client else None,
    )
    return _success_payload(
        data={'validation': result.model_dump(mode='json')},
        request_id=request_id,
    )
