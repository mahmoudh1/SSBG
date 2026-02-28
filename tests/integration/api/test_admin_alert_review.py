from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from app.api.dependencies import get_alerts_repository, get_audit_service, get_auth_service
from app.main import create_app
from app.schemas.auth import ApiKeyPrincipal


class FakeAuditService:
    def __init__(self) -> None:
        self.actions: list[dict[str, Any]] = []
        self.denies: list[dict[str, Any]] = []

    async def record_admin_action(
        self,
        actor_key_id: str | None,
        action: str,
        resource: str,
        resource_id: str | None,
        client_ip: str | None,
    ) -> None:
        self.actions.append(
            {
                'actor_key_id': actor_key_id,
                'action': action,
                'resource': resource,
                'resource_id': resource_id,
                'client_ip': client_ip,
            },
        )

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


class FakeAlertsRepository:
    def __init__(self) -> None:
        self.records: list[Any] = [
            SimpleNamespace(
                alert_id='alert-001',
                rule_id='RESTORE_RESTRICTED_SPIKE',
                severity='HIGH',
                status='OPEN',
                source_event='restore_restricted_blocked',
                actor_key_id='admin-key',
                related_backup_id='backup-0001',
                reason='Repeated restore restrictions detected',
                metadata_json='{}',
                created_at=datetime.now(timezone.utc),
                updated_at=None,
            ),
        ]

    async def list_alerts(
        self,
        offset: int = 0,
        limit: int = 100,
        status: str | None = None,
        severity: str | None = None,
        rule_id: str | None = None,
    ) -> list[Any]:
        _ = (offset, limit)
        items = list(self.records)
        if status:
            items = [item for item in items if item.status == status]
        if severity:
            items = [item for item in items if item.severity == severity]
        if rule_id:
            items = [item for item in items if item.rule_id == rule_id]
        return items

    async def update_status(self, alert_id: str, status: str) -> Any | None:
        for record in self.records:
            if record.alert_id == alert_id:
                record.status = status
                record.updated_at = datetime.now(timezone.utc)
                return record
        return None


def test_admin_can_review_and_acknowledge_alerts_with_audit_events() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            _ = (raw_key, client_ip)
            return ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT')

    app = create_app()
    audit = FakeAuditService()
    repo = FakeAlertsRepository()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_audit_service] = lambda: audit
    app.dependency_overrides[get_alerts_repository] = lambda: repo
    client = TestClient(app)

    list_response = client.get('/api/v1/admin/alerts', headers={'X-API-Key': 'valid'})
    assert list_response.status_code == 200
    alerts = list_response.json()['data']['alerts']
    assert len(alerts) == 1
    assert alerts[0]['alert_id'] == 'alert-001'

    update_response = client.put(
        '/api/v1/admin/alerts/alert-001/status',
        json={'status': 'ACKNOWLEDGED'},
        headers={'X-API-Key': 'valid'},
    )
    assert update_response.status_code == 200
    assert update_response.json()['data']['alert']['status'] == 'ACKNOWLEDGED'
    assert {'action': 'alert_reviewed'} in [{'action': item['action']} for item in audit.actions]
    assert {'action': 'alert_status_updated'} in [
        {'action': item['action']} for item in audit.actions
    ]


def test_operator_denied_admin_alert_review_endpoints() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            _ = (raw_key, client_ip)
            return ApiKeyPrincipal(key_id='op-key', role='operator', department='IT')

    app = create_app()
    audit = FakeAuditService()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_audit_service] = lambda: audit
    client = TestClient(app)

    list_response = client.get('/api/v1/admin/alerts', headers={'X-API-Key': 'valid'})
    update_response = client.put(
        '/api/v1/admin/alerts/alert-001/status',
        json={'status': 'ACKNOWLEDGED'},
        headers={'X-API-Key': 'valid'},
    )

    assert list_response.status_code == 403
    assert update_response.status_code == 403
    assert audit.denies and all(item['permission'] == 'admin' for item in audit.denies)
