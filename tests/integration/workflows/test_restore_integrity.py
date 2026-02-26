from __future__ import annotations

from hashlib import sha512
from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.core.enums import IncidentLevel
from app.infrastructure.crypto.aes_gcm import encrypt
from app.infrastructure.crypto.key_store_fs import KeyMaterial
from app.infrastructure.storage.minio_client import ObjectStorageError
from app.schemas.auth import ApiKeyPrincipal
from app.schemas.restores import RestoreRequest
from app.services.restore_service import (
    RestoreExecutionUnavailable,
    RestoreIntegrityFailed,
    RestoreService,
)


class FakeBackupsRepository:
    def __init__(self, metadata: object) -> None:
        self._metadata = metadata

    async def get_by_backup_id(self, backup_id: str) -> object | None:
        return self._metadata if getattr(self._metadata, 'backup_id', None) == backup_id else None


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


class FakePolicyService:
    def evaluate_restore(self, principal: ApiKeyPrincipal | None, classification: object) -> Any:
        _ = classification
        return SimpleNamespace(
            allowed=True,
            reason='Restore allowed',
            reason_category='allowed',
            role=principal.role if principal else 'unknown',
        )


class FakeAuditService:
    def __init__(self) -> None:
        self.policy_events: list[dict[str, object]] = []
        self.restore_events: list[dict[str, object]] = []

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
        self.policy_events.append(
            {
                'key_id': key_id,
                'operation': operation,
                'allowed': allowed,
                'reason': reason,
                'reason_category': reason_category,
                'classification': classification,
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


class FakeIncidentService:
    def get_current_level(self) -> IncidentLevel:
        return IncidentLevel.NORMAL


class FakeKeyStore:
    def __init__(self, key_material: KeyMaterial) -> None:
        self._key_material = key_material

    def get_key(self, version_id: str) -> KeyMaterial:
        if version_id != self._key_material.version_id:
            raise RuntimeError('Missing key version')
        return self._key_material


class FakeStorage:
    def __init__(self, blob: bytes) -> None:
        self._blob = blob

    async def get_object(self, bucket: str, object_name: str) -> bytes | None:
        _ = bucket
        return self._blob if object_name == 'backup-0001.bin' else None


class FailingStorage:
    async def get_object(self, bucket: str, object_name: str) -> bytes | None:
        _ = (bucket, object_name)
        raise ObjectStorageError('Storage unavailable')


class FakeSettings:
    minio_bucket = 'unit-test'


def _build_metadata(ciphertext_blob: bytes, plaintext: bytes) -> SimpleNamespace:
    nonce = ciphertext_blob[:12]
    return SimpleNamespace(
        backup_id='backup-0001',
        classification='CONFIDENTIAL',
        source_system='system-a',
        status='ACTIVE',
        key_version='P-001',
        storage_path='backup-0001.bin',
        nonce=nonce.hex(),
        checksum_plaintext=sha512(plaintext).hexdigest(),
        checksum_ciphertext=sha512(ciphertext_blob).hexdigest(),
        created_at=None,
    )


def _build_service(
    metadata: object,
    storage: object,
    key_store: object,
    audit: FakeAuditService,
) -> RestoreService:
    return RestoreService(  # type: ignore[arg-type]
        FakeBackupsRepository(metadata),
        FakeAuthService(),  # type: ignore[arg-type]
        FakePolicyService(),  # type: ignore[arg-type]
        audit,  # type: ignore[arg-type]
        FakeIncidentService(),  # type: ignore[arg-type]
        cast(Any, FakeSettings()),
        key_store,  # type: ignore[arg-type]
        storage,  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_restore_decrypts_and_verifies_integrity_before_success() -> None:
    plaintext = b'secret restore payload'
    key_material = KeyMaterial(version_id='P-001', key_bytes=b'restore-key-material')
    encrypted = encrypt(plaintext, key_material.key_bytes)
    ciphertext_blob = encrypted.nonce + encrypted.tag + encrypted.ciphertext
    metadata = _build_metadata(ciphertext_blob, plaintext)
    audit = FakeAuditService()
    service = _build_service(
        metadata=metadata,
        storage=FakeStorage(ciphertext_blob),
        key_store=FakeKeyStore(key_material),
        audit=audit,
    )

    result = await service.load_restore_metadata(
        RestoreRequest(backup_id='backup-0001'),
        ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT'),
        '127.0.0.1',
        'mfa:admin-key',
    )

    assert result['status'] == 'restore_completed'
    assert result['integrity_verified'] is True
    assert result['restored_size'] == len(plaintext)
    assert result['next_step'] == 'restore_access_token'
    assert 'restore_token' not in result
    assert audit.restore_events[-1]['action'] == 'restore_completed'


@pytest.mark.asyncio
async def test_restore_tamper_detection_fails_and_audits_no_success() -> None:
    plaintext = b'secret restore payload'
    key_material = KeyMaterial(version_id='P-001', key_bytes=b'restore-key-material')
    encrypted = encrypt(plaintext, key_material.key_bytes)
    ciphertext_blob = encrypted.nonce + encrypted.tag + encrypted.ciphertext
    tampered_blob = bytearray(ciphertext_blob)
    tampered_blob[-1] ^= 0x01
    metadata = _build_metadata(ciphertext_blob, plaintext)
    audit = FakeAuditService()
    service = _build_service(
        metadata=metadata,
        storage=FakeStorage(bytes(tampered_blob)),
        key_store=FakeKeyStore(key_material),
        audit=audit,
    )

    with pytest.raises(RestoreIntegrityFailed):
        await service.load_restore_metadata(
            RestoreRequest(backup_id='backup-0001'),
            ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT'),
            '127.0.0.1',
            'mfa:admin-key',
        )

    assert audit.restore_events[-1]['action'] == 'restore_failed'
    assert audit.restore_events[-1]['reason'] == 'integrity_failed'
    assert all(event['action'] != 'restore_completed' for event in audit.restore_events)


@pytest.mark.asyncio
async def test_restore_storage_failure_is_fail_secure_and_audited() -> None:
    plaintext = b'secret restore payload'
    key_material = KeyMaterial(version_id='P-001', key_bytes=b'restore-key-material')
    encrypted = encrypt(plaintext, key_material.key_bytes)
    ciphertext_blob = encrypted.nonce + encrypted.tag + encrypted.ciphertext
    metadata = _build_metadata(ciphertext_blob, plaintext)
    audit = FakeAuditService()
    service = _build_service(
        metadata=metadata,
        storage=FailingStorage(),
        key_store=FakeKeyStore(key_material),
        audit=audit,
    )

    with pytest.raises(RestoreExecutionUnavailable):
        await service.load_restore_metadata(
            RestoreRequest(backup_id='backup-0001'),
            ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT'),
            '127.0.0.1',
            'mfa:admin-key',
        )

    assert audit.restore_events[-1]['action'] == 'restore_failed'
    assert audit.restore_events[-1]['reason'] == 'restore_unavailable'


@pytest.mark.asyncio
async def test_restore_invalid_metadata_classification_is_fail_secure() -> None:
    plaintext = b'secret restore payload'
    key_material = KeyMaterial(version_id='P-001', key_bytes=b'restore-key-material')
    encrypted = encrypt(plaintext, key_material.key_bytes)
    ciphertext_blob = encrypted.nonce + encrypted.tag + encrypted.ciphertext
    metadata = _build_metadata(ciphertext_blob, plaintext)
    metadata.classification = 'NOT_A_VALID_CLASSIFICATION'
    audit = FakeAuditService()
    service = _build_service(
        metadata=metadata,
        storage=FakeStorage(ciphertext_blob),
        key_store=FakeKeyStore(key_material),
        audit=audit,
    )

    with pytest.raises(RestoreExecutionUnavailable):
        await service.load_restore_metadata(
            RestoreRequest(backup_id='backup-0001'),
            ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT'),
            '127.0.0.1',
            'mfa:admin-key',
        )

    assert audit.restore_events[-1]['action'] == 'restore_failed'
    assert audit.restore_events[-1]['reason'] == 'invalid_metadata_classification'
