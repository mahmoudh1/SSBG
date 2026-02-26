from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from hashlib import sha512
from types import SimpleNamespace
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_auth_service,
    get_restore_access_token_service,
    get_restore_service,
)
from app.core.enums import IncidentLevel
from app.infrastructure.crypto.aes_gcm import encrypt
from app.infrastructure.crypto.key_store_fs import KeyMaterial
from app.main import create_app
from app.schemas.auth import ApiKeyPrincipal
from app.schemas.restores import RestoreRequest
from app.services.restore_access_token_service import RestoreAccessTokenService
from app.services.restore_service import RestoreService


class FakeBackupsRepository:
    def __init__(self, metadata: object) -> None:
        self._metadata = metadata

    async def get_by_backup_id(self, backup_id: str) -> object | None:
        return self._metadata if getattr(self._metadata, 'backup_id', None) == backup_id else None


class FakeRestoreAuthService:
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


class FakeRequestAuthService:
    async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
        _ = (raw_key, client_ip)
        return ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT')


class FakeRequestAuthServiceAttacker:
    async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
        _ = (raw_key, client_ip)
        return ApiKeyPrincipal(key_id='attacker-key', role='admin', department='IT')


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

    async def record_restore_event(
        self,
        action: str,
        backup_id: str,
        actor_key_id: str | None,
        actor_role: str | None,
        status: str,
        reason: str | None,
    ) -> None:
        return None


class FakeIncidentService:
    def get_current_level(self) -> IncidentLevel:
        return IncidentLevel.NORMAL


class FakeKeyStore:
    def __init__(self, key_material: KeyMaterial) -> None:
        self._key_material = key_material

    def get_key(self, version_id: str) -> KeyMaterial:
        if version_id != self._key_material.version_id:
            raise RuntimeError('Missing key')
        return self._key_material


class FakeStorage:
    def __init__(self, blob: bytes) -> None:
        self._blob = blob

    async def get_object(self, bucket: str, object_name: str) -> bytes | None:
        _ = bucket
        return self._blob if object_name == 'backup-0001.bin' else None


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


class FakeSettings:
    minio_bucket = 'unit-test'

    def __init__(self, ttl_seconds: int) -> None:
        self.restore_access_token_ttl_seconds = ttl_seconds


def _metadata_and_crypto() -> tuple[SimpleNamespace, bytes, KeyMaterial]:
    plaintext = b'restore-payload'
    key_material = KeyMaterial(version_id='P-001', key_bytes=b'restore-key-material')
    encrypted = encrypt(plaintext, key_material.key_bytes)
    ciphertext_blob = encrypted.nonce + encrypted.tag + encrypted.ciphertext
    metadata = SimpleNamespace(
        backup_id='backup-0001',
        classification='CONFIDENTIAL',
        source_system='system-a',
        status='ACTIVE',
        key_version='P-001',
        storage_path='backup-0001.bin',
        nonce=encrypted.nonce.hex(),
        checksum_plaintext=sha512(plaintext).hexdigest(),
        checksum_ciphertext=sha512(ciphertext_blob).hexdigest(),
        created_at=None,
    )
    return metadata, ciphertext_blob, key_material


def _build_restore_service(
    ttl_seconds: int,
    token_service: RestoreAccessTokenService,
) -> RestoreService:
    metadata, ciphertext_blob, key_material = _metadata_and_crypto()
    return RestoreService(  # type: ignore[arg-type]
        FakeBackupsRepository(metadata),
        FakeRestoreAuthService(),  # type: ignore[arg-type]
        FakePolicyService(),  # type: ignore[arg-type]
        FakeAuditService(),  # type: ignore[arg-type]
        FakeIncidentService(),  # type: ignore[arg-type]
        cast(Any, FakeSettings(ttl_seconds)),
        FakeKeyStore(key_material),  # type: ignore[arg-type]
        FakeStorage(ciphertext_blob),  # type: ignore[arg-type]
        token_service,  # type: ignore[arg-type]
    )


def _override_restore_request_auth(app: FastAPI) -> None:
    app.dependency_overrides[get_auth_service] = lambda: FakeRequestAuthService()


def test_successful_restore_includes_token_expiration_and_token_can_be_used() -> None:
    clock = MutableClock(datetime(2026, 2, 26, 12, 0, 0, tzinfo=UTC))
    token_service = RestoreAccessTokenService(now_provider=clock)
    restore_service = _build_restore_service(ttl_seconds=300, token_service=token_service)
    app = create_app()
    _override_restore_request_auth(app)
    app.dependency_overrides[get_restore_service] = lambda: restore_service
    app.dependency_overrides[get_restore_access_token_service] = lambda: token_service
    client = TestClient(app)

    restore_response = client.post(
        '/api/v1/restores',
        json={'backup_id': 'backup-0001'},
        headers={'X-API-Key': 'valid', 'X-MFA-Token': 'mfa:admin-key'},
    )

    assert restore_response.status_code == 200
    restore_payload = restore_response.json()
    token = restore_payload['data']['restore_token']
    assert restore_payload['data']['status'] == 'restore_completed'
    assert restore_payload['data']['restore_token_ttl_seconds'] == 300
    assert restore_payload['data']['restore_token_expires_at'] == '2026-02-26T12:05:00+00:00'

    access_response = client.get(
        f'/api/v1/restores/access/{token}',
        headers={'X-API-Key': 'valid'},
    )
    assert access_response.status_code == 200
    access_payload = access_response.json()
    assert access_payload['data']['status'] == 'restore_access_granted'
    assert access_payload['data']['backup_id'] == 'backup-0001'
    assert access_payload['data']['expires_at'] == '2026-02-26T12:05:00+00:00'


def test_expired_restore_access_token_is_denied() -> None:
    clock = MutableClock(datetime(2026, 2, 26, 12, 0, 0, tzinfo=UTC))
    token_service = RestoreAccessTokenService(now_provider=clock)
    record = token_service.issue_token('backup-0001', 'admin-key', ttl_seconds=60)
    app = create_app()
    _override_restore_request_auth(app)
    app.dependency_overrides[get_restore_access_token_service] = lambda: token_service
    client = TestClient(app)

    clock.now = clock.now + timedelta(seconds=61)
    response = client.get(
        f'/api/v1/restores/access/{record.token}',
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload['error']['code'] == 'RESTORE_TOKEN_EXPIRED'


def test_restore_access_token_cannot_be_used_by_different_principal() -> None:
    clock = MutableClock(datetime(2026, 2, 26, 12, 0, 0, tzinfo=UTC))
    token_service = RestoreAccessTokenService(now_provider=clock)
    record = token_service.issue_token('backup-0001', 'admin-key', ttl_seconds=300)
    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: FakeRequestAuthServiceAttacker()
    app.dependency_overrides[get_restore_access_token_service] = lambda: token_service
    client = TestClient(app)

    response = client.get(
        f'/api/v1/restores/access/{record.token}',
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload['error']['code'] == 'RESTORE_TOKEN_FORBIDDEN'


def test_expired_records_are_purged_on_new_token_issue() -> None:
    clock = MutableClock(datetime(2026, 2, 26, 12, 0, 0, tzinfo=UTC))
    token_service = RestoreAccessTokenService(now_provider=clock)
    token_service.issue_token('backup-0001', 'admin-key', ttl_seconds=1)

    clock.now = clock.now + timedelta(seconds=2)
    token_service.issue_token('backup-0002', 'admin-key', ttl_seconds=60)

    assert token_service.active_record_count() == 1


def test_ttl_configuration_change_affects_newly_issued_restore_tokens() -> None:
    clock = MutableClock(datetime(2026, 2, 26, 13, 0, 0, tzinfo=UTC))
    token_service = RestoreAccessTokenService(now_provider=clock)
    principal = ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT')

    short_ttl_service = _build_restore_service(ttl_seconds=60, token_service=token_service)
    issued_short = cast(
        dict[str, object],
        asyncio.run(
            short_ttl_service.load_restore_metadata(
                request=RestoreRequest(backup_id='backup-0001'),
                principal=principal,
                client_ip='127.0.0.1',
                mfa_token='mfa:admin-key',
            ),
        ),
    )

    clock.now = datetime(2026, 2, 26, 13, 10, 0, tzinfo=UTC)
    long_ttl_service = _build_restore_service(ttl_seconds=600, token_service=token_service)
    issued_long = cast(
        dict[str, object],
        asyncio.run(
            long_ttl_service.load_restore_metadata(
                request=RestoreRequest(backup_id='backup-0001'),
                principal=principal,
                client_ip='127.0.0.1',
                mfa_token='mfa:admin-key',
            ),
        ),
    )

    assert issued_short['restore_token_ttl_seconds'] == 60
    assert issued_short['restore_token_expires_at'] == '2026-02-26T13:01:00+00:00'
    assert issued_long['restore_token_ttl_seconds'] == 600
    assert issued_long['restore_token_expires_at'] == '2026-02-26T13:20:00+00:00'
