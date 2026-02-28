from __future__ import annotations

import asyncio
from typing import Any, cast

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.enums import ClassificationLevel
from app.infrastructure.crypto.key_store_fs import KeyMaterial
from app.schemas.auth import ApiKeyPrincipal
from app.schemas.backups import BackupRequest
from app.services.audit_service import AuditService, AuditWriteError
from app.services.backup_service import BackupService
from app.services.policy_service import BackupPolicyDecision, PolicyService


class InMemoryChainAuditRepository:
    def __init__(self, fail_writes: bool = False, delay_seconds: float = 0.0) -> None:
        self._entries: list[Any] = []
        self._fail_writes = fail_writes
        self._delay_seconds = delay_seconds

    @property
    def entries(self) -> list[Any]:
        return sorted(self._entries, key=lambda item: item.chain_index)

    async def get_latest_chain_cursor(self) -> tuple[int, str] | None:
        if not self._entries:
            return None
        latest = max(self._entries, key=lambda item: item.chain_index)
        return latest.chain_index, latest.entry_hash

    async def create_entry(self, record: Any) -> Any:
        if self._delay_seconds:
            await asyncio.sleep(self._delay_seconds)
        if self._fail_writes:
            raise RuntimeError('Audit store unavailable')
        for existing in self._entries:
            if existing.chain_index == record.chain_index:
                raise IntegrityError('duplicate chain index', {}, Exception('duplicate'))
            if existing.entry_hash == record.entry_hash:
                raise IntegrityError('duplicate entry hash', {}, Exception('duplicate'))
        self._entries.append(record)
        return record


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


class FakeKeyStore:
    def get_active_key(self) -> KeyMaterial:
        return KeyMaterial(version_id='P-001', key_bytes=b'key-material')


class FakeStorage:
    async def put_object(self, bucket: str, object_name: str, data: bytes) -> None:
        _ = (bucket, object_name, data)
        return None


class FakeSettings:
    classification_required = True
    default_classification = 'PUBLIC'
    minio_bucket = 'unit-test'


@pytest.mark.asyncio
async def test_security_events_append_with_tamper_evident_chain_fields() -> None:
    repository = InMemoryChainAuditRepository()
    service = AuditService(cast(Any, repository))

    await service.record_backup_event(
        action='backup_processing_started',
        backup_id='backup-001',
        actor_key_id='admin-key',
        actor_role='admin',
        status='PROCESSING',
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
    await service.record_admin_action(
        actor_key_id='admin-key',
        action='policy_updated',
        resource='policy',
        resource_id='policy-001',
        client_ip='127.0.0.1',
    )
    await service.record_authorization_denied(
        key_id='operator-key',
        role='operator',
        permission='admin',
        reason='permission_denied',
        client_ip='127.0.0.1',
    )

    entries = repository.entries
    assert len(entries) == 4
    assert [entry.chain_index for entry in entries] == [1, 2, 3, 4]
    assert entries[0].prev_hash is None
    assert all(entry.entry_hash for entry in entries)
    assert entries[1].prev_hash == entries[0].entry_hash
    assert entries[2].prev_hash == entries[1].entry_hash
    assert entries[3].prev_hash == entries[2].entry_hash


@pytest.mark.asyncio
async def test_concurrent_audit_writes_retry_and_preserve_chain_continuity() -> None:
    repository = InMemoryChainAuditRepository(delay_seconds=0.01)
    service = AuditService(cast(Any, repository))

    async def _emit(index: int) -> None:
        await service.record_backup_event(
            action='backup_processing_started',
            backup_id=f'backup-{index:03d}',
            actor_key_id='admin-key',
            actor_role='admin',
            status='PROCESSING',
            reason=None,
        )

    await asyncio.gather(*[_emit(i) for i in range(1, 11)])

    entries = repository.entries
    assert len(entries) == 10
    assert [entry.chain_index for entry in entries] == list(range(1, 11))
    for current, previous in zip(entries[1:], entries[:-1], strict=False):
        assert current.prev_hash == previous.entry_hash


@pytest.mark.asyncio
async def test_audit_failure_enforces_fail_secure_for_backup_flow() -> None:
    audit_service = AuditService(cast(Any, InMemoryChainAuditRepository(fail_writes=True)))
    service = BackupService(
        cast(Any, FakeBackupsRepository()),
        FakeSettings(),
        cast(PolicyService, FakePolicyService()),
        cast(Any, audit_service),
        FakeKeyStore(),
        FakeStorage(),
    )

    with pytest.raises(AuditWriteError):
        await service.submit_backup(
            BackupRequest(
                classification=ClassificationLevel.PUBLIC,
                source_system='system-a',
                payload='payload',
            ),
            ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT'),
            '127.0.0.1',
        )


@pytest.mark.asyncio
async def test_auth_audit_remains_best_effort_when_repository_is_unavailable() -> None:
    service = AuditService(cast(Any, InMemoryChainAuditRepository(fail_writes=True)))
    await service.record_auth_success('admin-key', '127.0.0.1')


@pytest.mark.asyncio
async def test_auth_failure_is_appended_to_tamper_evident_chain() -> None:
    repository = InMemoryChainAuditRepository()
    service = AuditService(cast(Any, repository))

    await service.record_auth_failure(
        key_prefix='deadbeef',
        reason='key_not_found',
        client_ip='127.0.0.1',
    )

    entries = repository.entries
    assert len(entries) == 1
    assert entries[0].action == 'auth_failure'
    assert entries[0].status == 'denied'
