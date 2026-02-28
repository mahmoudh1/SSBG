from __future__ import annotations

import asyncio
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_audit_service, get_auth_service
from app.main import create_app
from app.schemas.auth import ApiKeyPrincipal
from app.services.audit_service import AuditService


class InMemoryAuditRepository:
    def __init__(self) -> None:
        self._entries: list[Any] = []

    @property
    def entries(self) -> list[Any]:
        return sorted(self._entries, key=lambda item: item.chain_index)

    async def get_latest_chain_cursor(self) -> tuple[int, str] | None:
        if not self._entries:
            return None
        latest = max(self._entries, key=lambda item: item.chain_index)
        return latest.chain_index, latest.entry_hash

    async def create_entry(self, record: Any) -> Any:
        self._entries.append(record)
        return record

    async def list_entries(
        self,
        offset: int = 0,
        limit: int = 100,
        action: str | None = None,
        resource: str | None = None,
        status: str | None = None,
    ) -> list[Any]:
        items = self.entries
        if action:
            items = [item for item in items if item.action == action]
        if resource:
            items = [item for item in items if item.resource == resource]
        if status:
            items = [item for item in items if item.status == status]
        return items[offset : offset + limit]


class FakeDenyAuditService:
    def __init__(self) -> None:
        self.denies: list[dict[str, Any]] = []

    async def record_authorization_denied(
        self,
        key_id: str | None,
        role: str,
        permission: str,
        reason: str,
        client_ip: str | None,
    ) -> None:
        self.denies.append(
            {
                'key_id': key_id,
                'role': role,
                'permission': permission,
                'reason': reason,
                'client_ip': client_ip,
            },
        )


def _override_auth(app: FastAPI, role: str) -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            _ = (raw_key, client_ip)
            return ApiKeyPrincipal(key_id='key-1', role=role, department='IT')

    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()


async def _seed_events(service: AuditService) -> None:
    await service.record_backup_event(
        action='backup_processing_succeeded',
        backup_id='backup-001',
        actor_key_id='admin-key',
        actor_role='admin',
        status='ACTIVE',
        reason=None,
    )
    await service.record_restore_event(
        action='restore_completed',
        backup_id='backup-001',
        actor_key_id='admin-key',
        actor_role='admin',
        status='COMPLETED',
        reason=None,
    )


def test_authorized_admin_can_review_audit_entries_and_summary() -> None:
    app = create_app()
    _override_auth(app, role='admin')
    repository = InMemoryAuditRepository()
    audit_service = AuditService(cast(Any, repository))
    asyncio.run(_seed_events(audit_service))
    app.dependency_overrides[get_audit_service] = lambda: audit_service
    client = TestClient(app)

    entries_response = client.get(
        '/api/v1/audit/entries?offset=0&limit=1&resource=backup',
        headers={'X-API-Key': 'valid'},
    )
    summary_response = client.get('/api/v1/audit/summary', headers={'X-API-Key': 'valid'})

    assert entries_response.status_code == 200
    entries_payload = entries_response.json()
    assert entries_payload['data']['paging'] == {'offset': 0, 'limit': 1}
    assert entries_payload['data']['filters']['resource'] == 'backup'
    assert len(entries_payload['data']['entries']) == 1
    assert entries_payload['data']['entries'][0]['resource'] == 'backup'

    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload['data']['validation']['valid'] is True
    assert 'checked_entries' in summary_payload['data']['validation']

    actions = [entry.action for entry in repository.entries]
    assert 'audit_review_accessed' in actions
    assert 'audit_validation_reviewed' in actions


def test_unauthorized_caller_is_denied_for_audit_review_endpoints() -> None:
    app = create_app()
    _override_auth(app, role='operator')
    deny_audit = FakeDenyAuditService()
    app.dependency_overrides[get_audit_service] = lambda: deny_audit
    client = TestClient(app)

    response = client.get('/api/v1/audit/entries', headers={'X-API-Key': 'valid'})

    assert response.status_code == 403
    assert response.json() == {
        'error': {'code': 'POLICY_DENIED', 'message': 'Not authorized for this operation'},
        'data': None,
        'meta': {'request_id': 'generated-placeholder-id'},
    }
    assert deny_audit.denies
    assert deny_audit.denies[0]['permission'] == 'audit'
