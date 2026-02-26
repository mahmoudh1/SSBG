from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from app.api.dependencies import get_audit_service, get_auth_service, get_policies_repository
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


class FakePoliciesRepository:
    def __init__(self) -> None:
        self.records: list[Any] = []

    async def create_policy(self, record: Any) -> Any:
        if record.created_at is None:
            record.created_at = datetime.now(timezone.utc)
        if record.updated_at is None:
            record.updated_at = record.created_at
        self.records.append(record)
        return record

    async def list_policies(self) -> list[Any]:
        return list(self.records)

    async def update_policy(
        self,
        policy_id: str,
        name: str | None,
        description: str | None,
        rule_json: dict[str, object] | None,
        is_active: bool | None,
    ) -> Any | None:
        for record in self.records:
            if record.policy_id == policy_id:
                if name is not None:
                    record.name = name
                if description is not None:
                    record.description = description
                if rule_json is not None:
                    record.rule_json = rule_json
                if is_active is not None:
                    record.is_active = is_active
                record.updated_at = datetime.now(timezone.utc)
                return record
        return None


def test_admin_policy_create_list_update() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            return ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT')

    app = create_app()
    audit = FakeAuditService()
    repo = FakePoliciesRepository()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_policies_repository] = lambda: repo
    app.dependency_overrides[get_audit_service] = lambda: audit
    client = TestClient(app)

    response = client.post(
        '/api/v1/admin/policies',
        json={'name': 'baseline', 'description': 'seed', 'rule_json': {'limit': 'daily'}},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 200
    policy_id = response.json()['data']['policy']['policy_id']

    response = client.get('/api/v1/admin/policies', headers={'X-API-Key': 'valid'})

    assert response.status_code == 200
    assert response.json()['data']['policies'][0]['policy_id'] == policy_id

    response = client.put(
        f'/api/v1/admin/policies/{policy_id}',
        json={'description': 'updated'},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 200
    assert response.json()['data']['policy']['description'] == 'updated'
    assert {'action': 'policy_created'} in [{'action': item['action']} for item in audit.actions]
    assert {'action': 'policy_listed'} in [{'action': item['action']} for item in audit.actions]
    assert {'action': 'policy_updated'} in [{'action': item['action']} for item in audit.actions]


def test_operator_denied_admin_policy_create() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            return ApiKeyPrincipal(key_id='op-key', role='operator', department='IT')

    app = create_app()
    audit = FakeAuditService()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_audit_service] = lambda: audit
    client = TestClient(app)

    response = client.post(
        '/api/v1/admin/policies',
        json={'name': 'baseline', 'rule_json': {'limit': 'daily'}},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 403
    assert response.json() == {
        'error': {'code': 'POLICY_DENIED', 'message': 'Not authorized for this operation'},
        'data': None,
        'meta': {'request_id': 'generated-placeholder-id'},
    }
    assert audit.denies
    assert audit.denies[0]['permission'] == 'admin'


def test_operator_denied_admin_policy_list_and_update() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            return ApiKeyPrincipal(key_id='op-key', role='operator', department='IT')

    app = create_app()
    audit = FakeAuditService()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_audit_service] = lambda: audit
    client = TestClient(app)

    list_response = client.get('/api/v1/admin/policies', headers={'X-API-Key': 'valid'})
    update_response = client.put(
        '/api/v1/admin/policies/policy-1',
        json={'description': 'updated'},
        headers={'X-API-Key': 'valid'},
    )

    assert list_response.status_code == 403
    assert update_response.status_code == 403
    assert len(audit.denies) == 2
