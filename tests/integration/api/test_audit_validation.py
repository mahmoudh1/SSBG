from __future__ import annotations

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

    async def list_entries(self, offset: int = 0, limit: int = 100) -> list[Any]:
        return self.entries[offset : offset + limit]


def _override_admin_auth(app: FastAPI) -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            _ = (raw_key, client_ip)
            return ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT')

    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()


async def _seed_chain(service: AuditService) -> None:
    await service.record_backup_event(
        action='backup_processing_started',
        backup_id='backup-001',
        actor_key_id='admin-key',
        actor_role='admin',
        status='PROCESSING',
        reason=None,
    )
    await service.record_backup_event(
        action='backup_processing_succeeded',
        backup_id='backup-001',
        actor_key_id='admin-key',
        actor_role='admin',
        status='ACTIVE',
        reason=None,
    )


def test_validate_audit_chain_reports_valid_machine_readable_result() -> None:
    app = create_app()
    _override_admin_auth(app)
    repository = InMemoryAuditRepository()
    audit_service = AuditService(cast(Any, repository))
    import asyncio

    asyncio.run(_seed_chain(audit_service))
    app.dependency_overrides[get_audit_service] = lambda: audit_service
    client = TestClient(app)

    response = client.get('/api/v1/audit/chain/validate', headers={'X-API-Key': 'valid'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['data']['valid'] is True
    assert payload['data']['checked_entries'] == 2
    assert payload['data']['failure'] is None
    assert payload['meta']['request_id'] == 'generated-placeholder-id'


def test_validate_audit_chain_reports_tamper_with_failure_pointer() -> None:
    app = create_app()
    _override_admin_auth(app)
    repository = InMemoryAuditRepository()
    audit_service = AuditService(cast(Any, repository))
    import asyncio

    asyncio.run(_seed_chain(audit_service))
    repository.entries[1].reason = 'tampered'
    app.dependency_overrides[get_audit_service] = lambda: audit_service
    client = TestClient(app)

    response = client.get('/api/v1/audit/chain/validate', headers={'X-API-Key': 'valid'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['data']['valid'] is False
    assert payload['data']['failure']['reason'] == 'entry_hash_mismatch'
    assert payload['data']['failure']['chain_index'] == 2
    assert payload['data']['failure']['event_id']


def test_validate_audit_chain_output_is_stable_and_non_mutating() -> None:
    app = create_app()
    _override_admin_auth(app)
    repository = InMemoryAuditRepository()
    audit_service = AuditService(cast(Any, repository))
    import asyncio

    asyncio.run(_seed_chain(audit_service))
    before = [
        (entry.chain_index, entry.prev_hash, entry.entry_hash, entry.reason)
        for entry in repository.entries
    ]
    app.dependency_overrides[get_audit_service] = lambda: audit_service
    client = TestClient(app)

    response = client.get('/api/v1/audit/chain/validate', headers={'X-API-Key': 'valid'})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload['data'].keys()) == {'valid', 'checked_entries', 'failure'}
    after = [
        (entry.chain_index, entry.prev_hash, entry.entry_hash, entry.reason)
        for entry in repository.entries
    ]
    assert before == after


def test_validate_audit_chain_detects_created_at_tampering() -> None:
    app = create_app()
    _override_admin_auth(app)
    repository = InMemoryAuditRepository()
    audit_service = AuditService(cast(Any, repository))
    import asyncio
    from datetime import UTC, datetime

    asyncio.run(_seed_chain(audit_service))
    repository.entries[1].created_at = datetime(2030, 1, 1, tzinfo=UTC)
    app.dependency_overrides[get_audit_service] = lambda: audit_service
    client = TestClient(app)

    response = client.get('/api/v1/audit/chain/validate', headers={'X-API-Key': 'valid'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['data']['valid'] is False
    assert payload['data']['failure']['reason'] == 'entry_hash_mismatch'


def test_validate_audit_chain_scans_entire_chain_not_fixed_window() -> None:
    app = create_app()
    _override_admin_auth(app)
    repository = InMemoryAuditRepository()
    audit_service = AuditService(cast(Any, repository))
    import asyncio

    async def _seed_large_chain() -> None:
        for index in range(1205):
            await audit_service.record_backup_event(
                action='backup_processing_started',
                backup_id=f'backup-{index:04d}',
                actor_key_id='admin-key',
                actor_role='admin',
                status='PROCESSING',
                reason=None,
            )

    asyncio.run(_seed_large_chain())
    app.dependency_overrides[get_audit_service] = lambda: audit_service
    client = TestClient(app)

    response = client.get('/api/v1/audit/chain/validate', headers={'X-API-Key': 'valid'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['data']['valid'] is True
    assert payload['data']['checked_entries'] == 1205
