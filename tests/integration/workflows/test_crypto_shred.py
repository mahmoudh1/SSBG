from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.enums import IncidentLevel
from app.schemas.auth import ApiKeyPrincipal
from app.schemas.restores import RestoreRequest
from app.services.auth_service import MfaFailure
from app.services.key_management_service import CryptoShredError, KeyManagementService
from app.services.restore_service import RestoreIrreversible, RestoreService


@dataclass
class KeyVersionRecord:
    version_id: str
    is_active: bool
    is_destroyed: bool
    rotated_from_version: str | None = None
    created_by_key_id: str | None = None
    rotation_reason: str | None = None
    created_at: datetime | None = None
    activated_at: datetime | None = None
    destroyed_at: datetime | None = None


class InMemoryKeyVersionsRepository:
    def __init__(self, records: list[KeyVersionRecord]) -> None:
        self.records = records

    async def get_active(self) -> KeyVersionRecord | None:
        for record in self.records:
            if record.is_active:
                return record
        return None

    async def get_by_version_id(self, version_id: str) -> KeyVersionRecord | None:
        for record in self.records:
            if record.version_id == version_id:
                return record
        return None

    async def list_versions(self) -> list[KeyVersionRecord]:
        return self.records

    async def create_version(self, record: KeyVersionRecord) -> KeyVersionRecord:
        self.records.append(record)
        return record

    async def set_active(
        self,
        to_version_id: str,
        rotated_from_version: str | None,
        reason: str | None,
        actor_key_id: str | None,
    ) -> KeyVersionRecord | None:
        _ = (rotated_from_version, reason, actor_key_id)
        target = await self.get_by_version_id(to_version_id)
        if target is None:
            return None
        for record in self.records:
            record.is_active = False
        target.is_active = True
        target.activated_at = datetime.now(UTC)
        return target

    async def mark_destroyed(
        self,
        version_id: str,
        *,
        destroyed_at: datetime | None = None,
        commit: bool = True,
    ) -> KeyVersionRecord | None:
        _ = commit
        target = await self.get_by_version_id(version_id)
        if target is None:
            return None
        target.is_destroyed = True
        target.is_active = False
        target.destroyed_at = destroyed_at or datetime.now(UTC)
        return target


class InMemoryBackupsRepository:
    def __init__(self, records: list[Any]) -> None:
        self.records = records

    async def mark_irreversible_by_key_version(
        self,
        key_version: str,
        reason: str,
        *,
        shredded_at: datetime | None = None,
        commit: bool = True,
    ) -> int:
        _ = commit
        count = 0
        event_time = shredded_at or datetime.now(UTC)
        for record in self.records:
            if getattr(record, 'key_version', None) != key_version:
                continue
            record.status = 'IRREVERSIBLE'
            record.irreversible_reason = reason
            record.shredded_at = event_time
            count += 1
        return count

    async def get_by_backup_id(self, backup_id: str) -> Any | None:
        for record in self.records:
            if getattr(record, 'backup_id', None) == backup_id:
                return record
        return None


class FakeAuditService:
    def __init__(self) -> None:
        self.admin_actions: list[dict[str, Any]] = []
        self.restore_events: list[dict[str, Any]] = []

    async def record_admin_action(
        self,
        actor_key_id: str | None,
        action: str,
        resource: str,
        resource_id: str | None,
        client_ip: str | None,
    ) -> None:
        self.admin_actions.append(
            {
                'actor_key_id': actor_key_id,
                'action': action,
                'resource': resource,
                'resource_id': resource_id,
                'client_ip': client_ip,
            },
        )

    async def record_restore_event(
        self,
        action: str,
        backup_id: str,
        actor_key_id: str | None,
        actor_role: str | None,
        status: str,
        reason: str | None,
    ) -> None:
        self.restore_events.append(
            {
                'action': action,
                'backup_id': backup_id,
                'actor_key_id': actor_key_id,
                'actor_role': actor_role,
                'status': status,
                'reason': reason,
            },
        )

    async def record_policy_decision(self, **kwargs: object) -> None:
        _ = kwargs


class FakeAuthService:
    async def validate_mfa_token(
        self,
        principal: ApiKeyPrincipal | None,
        mfa_token: str | None,
        client_ip: str | None,
    ) -> None:
        _ = client_ip
        if principal is None or not mfa_token:
            raise MfaFailure('MFA_REQUIRED', 'MFA token required')
        if mfa_token != f'mfa:{principal.key_id}':
            raise MfaFailure('MFA_INVALID', 'Invalid MFA token')


class FakeIncidentService:
    def __init__(self, level: IncidentLevel = IncidentLevel.NORMAL) -> None:
        self.level = level

    async def get_current_level(self) -> IncidentLevel:
        return self.level

    async def transition_to(
        self,
        new_level: IncidentLevel,
        changed_by_key_id: str | None,
        reason: str | None,
    ) -> object:
        _ = (changed_by_key_id, reason)
        self.level = new_level
        return SimpleNamespace(level=new_level)


class FakePolicyService:
    def evaluate_restore(self, principal: ApiKeyPrincipal | None, classification: object) -> Any:
        _ = (principal, classification)
        return SimpleNamespace(allowed=True, reason='allowed', reason_category='allowed')


class FakeSettings:
    minio_bucket = 'test-bucket'
    restore_access_token_ttl_seconds = 300


class FakeKeyStore:
    def get_key(self, version_id: str) -> object:
        return SimpleNamespace(version_id=version_id, key_bytes=b'k')


class FakeStorage:
    async def get_object(self, bucket: str, object_name: str) -> bytes | None:
        _ = (bucket, object_name)
        return b'\x00' * 28


def _build_service(
    key_records: list[KeyVersionRecord],
    backup_records: list[Any],
    audit: FakeAuditService,
    incident_level: IncidentLevel = IncidentLevel.NORMAL,
) -> KeyManagementService:
    return KeyManagementService(
        repository=InMemoryKeyVersionsRepository(key_records),  # type: ignore[arg-type]
        key_store=FakeKeyStore(),  # type: ignore[arg-type]
        audit_service=audit,  # type: ignore[arg-type]
        backups_repository=InMemoryBackupsRepository(backup_records),  # type: ignore[arg-type]
        incident_service=FakeIncidentService(level=incident_level),  # type: ignore[arg-type]
        auth_service=FakeAuthService(),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_crypto_shred_denies_missing_privileged_role_mfa_or_confirmation() -> None:
    key_records = [KeyVersionRecord(version_id='P-001', is_active=True, is_destroyed=False)]
    backup_records = [
        SimpleNamespace(backup_id='b-1', key_version='P-001', status='ACTIVE'),
    ]
    audit = FakeAuditService()
    service = _build_service(key_records, backup_records, audit)

    with pytest.raises(CryptoShredError) as role_denied:
        await service.execute_crypto_shred(
            version_id='P-001',
            principal=ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT'),
            mfa_token='mfa:admin-key',
            confirmation='DESTROY P-001',
            client_ip='127.0.0.1',
        )
    assert role_denied.value.reason_category == 'insufficient_role'

    with pytest.raises(CryptoShredError) as confirmation_denied:
        await service.execute_crypto_shred(
            version_id='P-001',
            principal=ApiKeyPrincipal(
                key_id='super-key',
                role='super_admin',
                department='Security',
            ),
            mfa_token='mfa:super-key',
            confirmation='WRONG',
            client_ip='127.0.0.1',
        )
    assert confirmation_denied.value.reason_category == 'missing_confirmation'

    with pytest.raises(CryptoShredError) as mfa_denied:
        await service.execute_crypto_shred(
            version_id='P-001',
            principal=ApiKeyPrincipal(
                key_id='super-key',
                role='super_admin',
                department='Security',
            ),
            mfa_token=None,
            confirmation='DESTROY P-001',
            client_ip='127.0.0.1',
        )
    assert mfa_denied.value.reason_category == 'mfa_required'
    assert [event['action'] for event in audit.admin_actions].count('crypto_shred_denied') >= 3


@pytest.mark.asyncio
async def test_crypto_shred_success_marks_key_destroyed_and_backups_irreversible() -> None:
    key_records = [KeyVersionRecord(version_id='P-001', is_active=True, is_destroyed=False)]
    backup_records = [
        SimpleNamespace(backup_id='b-1', key_version='P-001', status='ACTIVE'),
        SimpleNamespace(backup_id='b-2', key_version='P-001', status='ACTIVE'),
    ]
    audit = FakeAuditService()
    service = _build_service(key_records, backup_records, audit)

    result = await service.execute_crypto_shred(
        version_id='P-001',
        principal=ApiKeyPrincipal(key_id='super-key', role='super_admin', department='Security'),
        mfa_token='mfa:super-key',
        confirmation='DESTROY P-001',
        client_ip='127.0.0.1',
    )

    assert result['destroyed'] is True
    assert result['affected_backups'] == 2
    assert result['incident_effect'] == 'escalated_to_lockdown'
    assert key_records[0].is_destroyed is True
    assert all(record.status == 'IRREVERSIBLE' for record in backup_records)
    actions = [event['action'] for event in audit.admin_actions]
    assert 'crypto_shred_started' in actions
    assert 'incident_effect_applied' in actions
    assert 'crypto_shred_completed' in actions


@pytest.mark.asyncio
async def test_future_restore_attempts_fail_for_crypto_shredded_backups() -> None:
    key_records = [KeyVersionRecord(version_id='P-001', is_active=True, is_destroyed=False)]
    backup_records = [
        SimpleNamespace(
            backup_id='backup-0001',
            key_version='P-001',
            classification='CONFIDENTIAL',
            source_system='system-a',
            status='ACTIVE',
            created_at=datetime.now(UTC),
        ),
    ]
    audit = FakeAuditService()
    service = _build_service(key_records, backup_records, audit)
    await service.execute_crypto_shred(
        version_id='P-001',
        principal=ApiKeyPrincipal(key_id='super-key', role='super_admin', department='Security'),
        mfa_token='mfa:super-key',
        confirmation='DESTROY P-001',
        client_ip='127.0.0.1',
    )
    restore_service = RestoreService(  # type: ignore[arg-type]
        backups_repository=InMemoryBackupsRepository(backup_records),
        auth_service=FakeAuthService(),  # type: ignore[arg-type]
        policy_service=FakePolicyService(),  # type: ignore[arg-type]
        audit_service=audit,  # type: ignore[arg-type]
        incident_service=FakeIncidentService(),  # type: ignore[arg-type]
        settings=FakeSettings(),  # type: ignore[arg-type]
        key_store=FakeKeyStore(),  # type: ignore[arg-type]
        storage=FakeStorage(),  # type: ignore[arg-type]
    )

    with pytest.raises(RestoreIrreversible) as exc_info:
        await restore_service.load_restore_metadata(
            request=RestoreRequest(backup_id='backup-0001'),
            principal=ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT'),
            client_ip='127.0.0.1',
            mfa_token='mfa:admin-key',
        )
    assert exc_info.value.reason_category == 'irreversible'
    assert audit.restore_events and audit.restore_events[-1]['reason'] == 'irreversible'


@pytest.mark.asyncio
async def test_crypto_shred_records_incident_effect_when_already_lockdown() -> None:
    key_records = [KeyVersionRecord(version_id='P-001', is_active=True, is_destroyed=False)]
    backup_records = [
        SimpleNamespace(backup_id='b-1', key_version='P-001', status='ACTIVE'),
    ]
    audit = FakeAuditService()
    service = _build_service(
        key_records=key_records,
        backup_records=backup_records,
        audit=audit,
        incident_level=IncidentLevel.LOCKDOWN,
    )

    result = await service.execute_crypto_shred(
        version_id='P-001',
        principal=ApiKeyPrincipal(key_id='super-key', role='super_admin', department='Security'),
        mfa_token='mfa:super-key',
        confirmation='DESTROY P-001',
        client_ip='127.0.0.1',
    )

    assert result['incident_effect'] == 'already_lockdown'
    incident_actions = [event for event in audit.admin_actions if event['action'] == 'incident_effect_applied']
    assert incident_actions
    assert incident_actions[-1]['resource_id'] == 'already_lockdown'
