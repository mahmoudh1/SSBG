from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_auth_service, get_backup_service
from app.core.enums import ClassificationLevel
from app.infrastructure.crypto.key_store_fs import KeyMaterial
from app.main import create_app
from app.schemas.auth import ApiKeyPrincipal
from app.services.backup_service import BackupService
from app.services.policy_service import BackupPolicyDecision


class FakeBackupsRepository:
    def __init__(self) -> None:
        self.records: list[Any] = []

    async def create_metadata(self, record: object) -> object:
        self.records.append(record)
        return record

    async def get_by_backup_id(self, backup_id: str) -> Any | None:
        for record in self.records:
            if getattr(record, 'backup_id', None) == backup_id:
                return record
        return None

    async def update_metadata(self, backup_id: str, **fields: object) -> Any | None:
        record = await self.get_by_backup_id(backup_id)
        if record is None:
            return None
        for key, value in fields.items():
            setattr(record, key, value)
        return record


class FakePolicyService:
    def evaluate_backup(
        self,
        principal: ApiKeyPrincipal | None,
        classification: ClassificationLevel,
    ) -> BackupPolicyDecision:
        return BackupPolicyDecision(
            allowed=True,
            reason='Backup allowed',
            reason_category='allowed',
            role=principal.role if principal else 'unknown',
            classification=classification,
        )


class FakeAuditService:
    async def record_policy_decision(
        self,
        key_id: str | None,
        operation: str,
        allowed: bool,
        reason: str,
        reason_category: str,
        classification: str | None,
        client_ip: str | None,
    ) -> None:
        return None

    async def record_backup_event(
        self,
        action: str,
        backup_id: str,
        actor_key_id: str | None,
        actor_role: str | None,
        status: str,
        reason: str | None,
    ) -> None:
        return None


class FakeKeyStore:
    def get_active_key(self) -> KeyMaterial:
        return KeyMaterial(version_id='P-001', key_bytes=b'key-material')


class FakeStorage:
    async def put_object(self, bucket: str, object_name: str, data: bytes) -> None:
        return None


def _override_auth(app: FastAPI) -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            return ApiKeyPrincipal(key_id='key-1', role='operator', department='IT')

    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()


def test_missing_classification_uses_default_when_not_required() -> None:
    class FakeSettings:
        classification_required = False
        default_classification = 'INTERNAL'
        minio_bucket = 'unit-test'

    app = create_app()
    repository = FakeBackupsRepository()
    service = BackupService(
        repository,
        FakeSettings(),
        FakePolicyService(),
        FakeAuditService(),
        FakeKeyStore(),
        FakeStorage(),
    )
    _override_auth(app)
    app.dependency_overrides[get_backup_service] = lambda: service
    client = TestClient(app)

    response = client.post(
        '/api/v1/backups',
        json={'source_system': 'system-a'},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 200
    payload = response.json()
    backup_id = payload['data']['backup_id']
    assert payload['data']['classification'] == 'INTERNAL'
    record = repository.records[0]
    assert record.classification == 'INTERNAL'
    assert record.backup_id == backup_id


def test_invalid_default_classification_rejected() -> None:
    class FakeSettings:
        classification_required = False
        default_classification = 'INVALID'
        minio_bucket = 'unit-test'

    app = create_app()
    repository = FakeBackupsRepository()
    service = BackupService(
        repository,
        FakeSettings(),
        FakePolicyService(),
        FakeAuditService(),
        FakeKeyStore(),
        FakeStorage(),
    )
    _override_auth(app)
    app.dependency_overrides[get_backup_service] = lambda: service
    client = TestClient(app)

    response = client.post(
        '/api/v1/backups',
        json={'source_system': 'system-a'},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload['error']['code'] == 'VALIDATION_ERROR'
    assert payload['data']['details']
