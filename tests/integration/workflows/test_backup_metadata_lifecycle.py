from __future__ import annotations

from typing import Any, cast

import pytest

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
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

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
        self.events.append(
            {
                'action': action,
                'backup_id': backup_id,
                'status': status,
                'reason': reason,
            },
        )


class FakeKeyStore:
    def get_active_key(self) -> KeyMaterial:
        return KeyMaterial(version_id='P-001', key_bytes=b'key-material')


class FakeSettings:
    classification_required = True
    default_classification = 'PUBLIC'
    minio_bucket = 'unit-test'


class FakeStorage:
    async def put_object(self, bucket: str, object_name: str, data: bytes) -> None:
        return None


class FailingStorage:
    async def put_object(self, bucket: str, object_name: str, data: bytes) -> None:
        raise ObjectStorageError('Storage unavailable')


@pytest.mark.asyncio
async def test_backup_lifecycle_persists_metadata_and_audit_events() -> None:
    repository = FakeBackupsRepository()
    audit = FakeAuditService()
    service = BackupService(
        cast(BackupsRepository, repository),
        FakeSettings(),
        cast(PolicyService, FakePolicyService()),
        cast(AuditService, audit),
        FakeKeyStore(),
        FakeStorage(),
    )
    principal = ApiKeyPrincipal(key_id='key-1', role='operator', department='IT')
    request = BackupRequest(
        classification=ClassificationLevel.PUBLIC,
        source_system='system-a',
        payload='payload',
    )

    result = await service.submit_backup(request, principal, None)

    assert result['backup_id']
    record = repository.records[0]
    assert record.backup_id == result['backup_id']
    assert record.status == BackupStatus.ACTIVE.value
    assert record.storage_path
    assert record.checksum_plaintext
    assert record.checksum_ciphertext
    assert audit.events[0]['action'] == 'backup_processing_started'
    assert audit.events[1]['action'] == 'backup_processing_succeeded'


@pytest.mark.asyncio
async def test_backup_lifecycle_records_failed_status_on_storage_failure() -> None:
    repository = FakeBackupsRepository()
    audit = FakeAuditService()
    service = BackupService(
        cast(BackupsRepository, repository),
        FakeSettings(),
        cast(PolicyService, FakePolicyService()),
        cast(AuditService, audit),
        FakeKeyStore(),
        FailingStorage(),
    )
    principal = ApiKeyPrincipal(key_id='key-1', role='operator', department='IT')
    request = BackupRequest(
        classification=ClassificationLevel.PUBLIC,
        source_system='system-a',
        payload='payload',
    )

    with pytest.raises(BackupProcessingError):
        await service.submit_backup(request, principal, None)

    record = repository.records[0]
    assert record.status == BackupStatus.FAILED.value
    assert audit.events[-1]['action'] == 'backup_processing_failed'
