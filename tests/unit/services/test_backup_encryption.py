from __future__ import annotations

from typing import Any, cast

import pytest

from app.core.config import Settings
from app.core.enums import BackupStatus, ClassificationLevel
from app.infrastructure.crypto.key_store_fs import KeyMaterial
from app.infrastructure.storage.minio_client import ObjectStorageError
from app.repositories.backups_repository import BackupsRepository
from app.schemas.auth import ApiKeyPrincipal
from app.schemas.backups import BackupRequest
from app.services.audit_service import AuditService
from app.services.backup_service import BackupProcessingError, BackupService
from app.services.policy_service import BackupPolicyDecision, PolicyService


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


class FailingKeyStore:
    def get_active_key(self) -> KeyMaterial:
        raise RuntimeError('Key unavailable')


class FakeStorage:
    def __init__(self) -> None:
        self.objects: list[tuple[str, str, bytes]] = []

    async def put_object(self, bucket: str, object_name: str, data: bytes) -> None:
        self.objects.append((bucket, object_name, data))


class FailingStorage:
    async def put_object(self, bucket: str, object_name: str, data: bytes) -> None:
        raise ObjectStorageError('Storage unavailable')


@pytest.mark.asyncio
async def test_encrypts_payload_before_storage_and_tracks_key_version() -> None:
    repository = FakeBackupsRepository()
    storage = FakeStorage()
    service = BackupService(
        cast(BackupsRepository, repository),
        Settings(),
        cast(PolicyService, FakePolicyService()),
        cast(AuditService, FakeAuditService()),
        FakeKeyStore(),
        storage,
    )
    principal = ApiKeyPrincipal(key_id='key-1', role='operator', department='IT')
    request = BackupRequest(
        classification=ClassificationLevel.PUBLIC,
        source_system='system-a',
        payload='secret-payload',
    )

    result = await service.submit_backup(request, principal, None)

    assert result['status'] == 'accepted'
    assert storage.objects
    stored_data = storage.objects[0][2]
    assert len(stored_data) > len(b'secret-payload')
    record = repository.records[0]
    assert record.key_version == 'P-001'
    assert record.status == BackupStatus.ACTIVE.value


@pytest.mark.asyncio
async def test_encryption_failure_aborts_metadata_creation() -> None:
    repository = FakeBackupsRepository()
    service = BackupService(
        cast(BackupsRepository, repository),
        Settings(),
        cast(PolicyService, FakePolicyService()),
        cast(AuditService, FakeAuditService()),
        FailingKeyStore(),
        FakeStorage(),
    )
    principal = ApiKeyPrincipal(key_id='key-1', role='operator', department='IT')
    request = BackupRequest(
        classification=ClassificationLevel.PUBLIC,
        source_system='system-a',
        payload='secret-payload',
    )

    with pytest.raises(BackupProcessingError):
        await service.submit_backup(request, principal, None)

    assert len(repository.records) == 1
    assert repository.records[0].status == BackupStatus.FAILED.value


@pytest.mark.asyncio
async def test_storage_failure_aborts_metadata_creation() -> None:
    repository = FakeBackupsRepository()
    service = BackupService(
        cast(BackupsRepository, repository),
        Settings(),
        cast(PolicyService, FakePolicyService()),
        cast(AuditService, FakeAuditService()),
        FakeKeyStore(),
        FailingStorage(),
    )
    principal = ApiKeyPrincipal(key_id='key-1', role='operator', department='IT')
    request = BackupRequest(
        classification=ClassificationLevel.PUBLIC,
        source_system='system-a',
        payload='secret-payload',
    )

    with pytest.raises(BackupProcessingError):
        await service.submit_backup(request, principal, None)

    assert len(repository.records) == 1
    assert repository.records[0].status == BackupStatus.FAILED.value
