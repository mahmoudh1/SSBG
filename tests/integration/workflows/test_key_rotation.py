from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.core.enums import ClassificationLevel, IncidentLevel
from app.infrastructure.crypto.key_store_fs import KeyMaterial
from app.schemas.auth import ApiKeyPrincipal
from app.schemas.backups import BackupRequest
from app.schemas.restores import RestoreRequest
from app.services.backup_service import BackupService
from app.services.key_management_service import KeyManagementService, KeyRotationError
from app.services.restore_service import RestoreService


class InMemoryKeyVersionsRepository:
    def __init__(self) -> None:
        self.records: list[Any] = []

    async def get_active(self) -> Any | None:
        for record in reversed(self.records):
            if record.is_active:
                return record
        return None

    async def get_by_version_id(self, version_id: str) -> Any | None:
        for record in self.records:
            if record.version_id == version_id:
                return record
        return None

    async def list_versions(self) -> list[Any]:
        return list(reversed(self.records))

    async def create_version(self, record: Any) -> Any:
        if getattr(record, 'created_at', None) is None:
            record.created_at = datetime.now(UTC)
        self.records.append(record)
        return record

    async def set_active(
        self,
        to_version_id: str,
        rotated_from_version: str | None,
        reason: str | None,
        actor_key_id: str | None,
    ) -> Any | None:
        target = await self.get_by_version_id(to_version_id)
        if target is None:
            return None
        for record in self.records:
            record.is_active = False
        target.is_active = True
        target.rotated_from_version = rotated_from_version
        target.rotation_reason = reason
        target.created_by_key_id = actor_key_id
        target.activated_at = datetime.now(UTC)
        return target

    async def mark_destroyed(self, version_id: str) -> Any | None:
        record = await self.get_by_version_id(version_id)
        if record is None:
            return None
        record.is_destroyed = True
        record.is_active = False
        record.destroyed_at = datetime.now(UTC)
        return record


class FakeKeyStore:
    def __init__(self, material_by_version: dict[str, bytes], active_version: str) -> None:
        self._material = material_by_version
        self._active_version = active_version

    def get_key(self, version_id: str) -> KeyMaterial:
        if version_id not in self._material:
            raise RuntimeError('missing key')
        return KeyMaterial(version_id=version_id, key_bytes=self._material[version_id])

    def get_active_key(self) -> KeyMaterial:
        return self.get_key(self._active_version)


class FakeAuditService:
    def __init__(self) -> None:
        self.key_rotations: list[dict[str, object]] = []

    async def record_key_rotation(
        self,
        actor_key_id: str | None,
        from_version: str | None,
        to_version: str,
        client_ip: str | None,
    ) -> None:
        self.key_rotations.append(
            {
                'actor_key_id': actor_key_id,
                'from_version': from_version,
                'to_version': to_version,
                'client_ip': client_ip,
            },
        )

    async def record_policy_decision(self, **kwargs: object) -> None:
        _ = kwargs

    async def record_backup_event(self, **kwargs: object) -> None:
        _ = kwargs

    async def record_restore_event(self, **kwargs: object) -> None:
        _ = kwargs


class InMemoryBackupsRepository:
    def __init__(self) -> None:
        self.records: list[Any] = []

    async def create_metadata(self, record: Any) -> Any:
        self.records.append(record)
        return record

    async def get_by_backup_id(self, backup_id: str) -> Any | None:
        for record in self.records:
            if record.backup_id == backup_id:
                return record
        return None

    async def update_metadata(self, backup_id: str, **fields: object) -> Any | None:
        record = await self.get_by_backup_id(backup_id)
        if record is None:
            return None
        for key, value in fields.items():
            setattr(record, key, value)
        return record


class InMemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    async def put_object(self, bucket: str, object_name: str, data: bytes) -> None:
        self.objects[(bucket, object_name)] = data

    async def get_object(self, bucket: str, object_name: str) -> bytes | None:
        return self.objects.get((bucket, object_name))


class FakePolicyService:
    def evaluate_backup(
        self,
        principal: ApiKeyPrincipal | None,
        classification: ClassificationLevel,
    ) -> Any:
        _ = (principal, classification)
        return SimpleNamespace(
            allowed=True,
            reason='allowed',
            reason_category='allowed',
        )

    def evaluate_restore(self, principal: ApiKeyPrincipal | None, classification: object) -> Any:
        _ = (principal, classification)
        return SimpleNamespace(
            allowed=True,
            reason='allowed',
            reason_category='allowed',
        )


class FakeAuthService:
    async def validate_mfa_token(
        self,
        principal: ApiKeyPrincipal | None,
        mfa_token: str | None,
        client_ip: str | None,
    ) -> None:
        _ = client_ip
        if principal is None or mfa_token != f'mfa:{principal.key_id}':
            from app.services.auth_service import MfaFailure

            raise MfaFailure('MFA_INVALID', 'Invalid MFA token')


class FakeIncidentService:
    def get_current_level(self) -> IncidentLevel:
        return IncidentLevel.NORMAL


class FakeSettings:
    classification_required = True
    default_classification = 'PUBLIC'
    minio_bucket = 'unit-test'
    restore_access_token_ttl_seconds = 300


@pytest.mark.asyncio
async def test_rotation_switches_active_key_for_new_backups_and_audits() -> None:
    key_store = FakeKeyStore({'P-001': b'k1', 'P-002': b'k2'}, active_version='P-001')
    key_repo = InMemoryKeyVersionsRepository()
    audit = FakeAuditService()
    key_management = KeyManagementService(
        repository=cast(Any, key_repo),
        key_store=key_store,  # type: ignore[arg-type]
        audit_service=cast(Any, audit),
    )
    backup_repo = InMemoryBackupsRepository()
    storage = InMemoryStorage()
    backup_service = BackupService(
        repository=cast(Any, backup_repo),
        settings=FakeSettings(),
        policy_service=cast(Any, FakePolicyService()),
        audit_service=cast(Any, audit),
        key_store=key_store,  # type: ignore[arg-type]
        storage=storage,  # type: ignore[arg-type]
        key_management_service=key_management,
    )
    principal = ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT')

    first = await backup_service.submit_backup(
        BackupRequest(
            classification=ClassificationLevel.PUBLIC,
            source_system='system-a',
            payload='first',
        ),
        principal,
        '127.0.0.1',
    )
    first_record = await backup_repo.get_by_backup_id(cast(str, first['backup_id']))
    assert first_record is not None and first_record.key_version == 'P-001'

    rotated = await key_management.rotate_active_version(
        to_version_id='P-002',
        actor_key_id='admin-key',
        reason='scheduled_rotation',
        client_ip='127.0.0.1',
    )
    assert rotated.version_id == 'P-002'
    assert rotated.is_active is True
    assert audit.key_rotations and audit.key_rotations[-1]['from_version'] == 'P-001'

    second = await backup_service.submit_backup(
        BackupRequest(
            classification=ClassificationLevel.PUBLIC,
            source_system='system-a',
            payload='second',
        ),
        principal,
        '127.0.0.1',
    )
    second_record = await backup_repo.get_by_backup_id(cast(str, second['backup_id']))
    assert second_record is not None and second_record.key_version == 'P-002'


@pytest.mark.asyncio
async def test_old_backups_bound_to_previous_non_destroyed_key_remain_restorable() -> None:
    key_store = FakeKeyStore({'P-001': b'k1', 'P-002': b'k2'}, active_version='P-001')
    key_repo = InMemoryKeyVersionsRepository()
    audit = FakeAuditService()
    key_management = KeyManagementService(
        repository=cast(Any, key_repo),
        key_store=key_store,  # type: ignore[arg-type]
        audit_service=cast(Any, audit),
    )
    backup_repo = InMemoryBackupsRepository()
    storage = InMemoryStorage()
    backup_service = BackupService(
        repository=cast(Any, backup_repo),
        settings=FakeSettings(),
        policy_service=cast(Any, FakePolicyService()),
        audit_service=cast(Any, audit),
        key_store=key_store,  # type: ignore[arg-type]
        storage=storage,  # type: ignore[arg-type]
        key_management_service=key_management,
    )
    principal = ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT')

    first = await backup_service.submit_backup(
        BackupRequest(
            classification=ClassificationLevel.CONFIDENTIAL,
            source_system='system-a',
            payload='legacy',
        ),
        principal,
        '127.0.0.1',
    )
    first_id = cast(str, first['backup_id'])
    await key_management.rotate_active_version(
        to_version_id='P-002',
        actor_key_id='admin-key',
        reason='scheduled_rotation',
        client_ip='127.0.0.1',
    )
    restore_service = RestoreService(  # type: ignore[arg-type]
        backups_repository=backup_repo,
        auth_service=FakeAuthService(),  # type: ignore[arg-type]
        policy_service=FakePolicyService(),  # type: ignore[arg-type]
        audit_service=audit,  # type: ignore[arg-type]
        incident_service=FakeIncidentService(),  # type: ignore[arg-type]
        settings=FakeSettings(),  # type: ignore[arg-type]
        key_store=key_store,  # type: ignore[arg-type]
        storage=storage,  # type: ignore[arg-type]
    )

    restored = await restore_service.load_restore_metadata(
        request=RestoreRequest(backup_id=first_id),
        principal=principal,
        client_ip='127.0.0.1',
        mfa_token='mfa:admin-key',
    )
    assert restored['status'] == 'restore_completed'
    assert restored['integrity_verified'] is True


@pytest.mark.asyncio
async def test_invalid_rotation_request_is_denied_fail_secure() -> None:
    key_store = FakeKeyStore({'P-001': b'k1'}, active_version='P-001')
    key_repo = InMemoryKeyVersionsRepository()
    audit = FakeAuditService()
    key_management = KeyManagementService(
        repository=cast(Any, key_repo),
        key_store=key_store,  # type: ignore[arg-type]
        audit_service=cast(Any, audit),
    )

    with pytest.raises(KeyRotationError) as exc_info:
        await key_management.rotate_active_version(
            to_version_id='P-999',
            actor_key_id='admin-key',
            reason='invalid',
            client_ip='127.0.0.1',
        )
    assert exc_info.value.reason_category == 'key_material_missing'
