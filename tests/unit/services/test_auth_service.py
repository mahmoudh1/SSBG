from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import cast

import pytest

from app.repositories.api_keys_repository import ApiKeysRepository
from app.schemas.auth import ApiKeyPrincipal
from app.services.audit_service import AuditService
from app.services.auth_service import AuthFailure, AuthService


class FakeRepository:
    def __init__(self, record: object | None) -> None:
        self.record = record
        self.updated = False

    async def get_by_hash(self, key_hash: str) -> object | None:
        return self.record

    async def update_last_used(self, api_key: object, ip_address: str | None) -> None:
        self.updated = True


class FakeAuditService:
    def __init__(self) -> None:
        self.failures: list[tuple[str, str, str | None]] = []
        self.successes: list[tuple[str, str | None]] = []

    async def record_auth_failure(
        self,
        key_prefix: str,
        reason: str,
        client_ip: str | None,
    ) -> None:
        self.failures.append((key_prefix, reason, client_ip))

    async def record_auth_success(self, key_id: str, client_ip: str | None) -> None:
        self.successes.append((key_id, client_ip))


@pytest.mark.asyncio
async def test_authenticate_missing_key_raises() -> None:
    repo = FakeRepository(record=None)
    audit = FakeAuditService()
    service = AuthService(
        cast(ApiKeysRepository, repo),
        cast(AuditService, audit),
    )

    with pytest.raises(AuthFailure) as excinfo:
        await service.authenticate('', '127.0.0.1')

    assert excinfo.value.code == 'AUTH_INVALID_KEY'
    assert audit.failures


@pytest.mark.asyncio
async def test_authenticate_revoked_key_raises() -> None:
    record = SimpleNamespace(
        key_id='key-1',
        key_prefix='abcd1234',
        is_active=False,
        expires_at=None,
        allowed_ips=None,
        role='operator',
        department='IT',
    )
    repo = FakeRepository(record=record)
    audit = FakeAuditService()
    service = AuthService(
        cast(ApiKeysRepository, repo),
        cast(AuditService, audit),
    )

    with pytest.raises(AuthFailure) as excinfo:
        await service.authenticate('raw-key', '127.0.0.1')

    assert excinfo.value.code == 'AUTH_INVALID_KEY'
    assert audit.failures


@pytest.mark.asyncio
async def test_authenticate_expired_key_raises() -> None:
    expired_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    record = SimpleNamespace(
        key_id='key-1',
        key_prefix='abcd1234',
        is_active=True,
        expires_at=expired_at,
        allowed_ips=None,
        role='operator',
        department='IT',
    )
    repo = FakeRepository(record=record)
    audit = FakeAuditService()
    service = AuthService(
        cast(ApiKeysRepository, repo),
        cast(AuditService, audit),
    )

    with pytest.raises(AuthFailure) as excinfo:
        await service.authenticate('raw-key', '127.0.0.1')

    assert excinfo.value.code == 'AUTH_INVALID_KEY'
    assert audit.failures


@pytest.mark.asyncio
async def test_authenticate_valid_key_returns_principal() -> None:
    record = SimpleNamespace(
        key_id='key-1',
        key_prefix='abcd1234',
        is_active=True,
        expires_at=None,
        allowed_ips=None,
        role='operator',
        department='IT',
    )
    repo = FakeRepository(record=record)
    audit = FakeAuditService()
    service = AuthService(
        cast(ApiKeysRepository, repo),
        cast(AuditService, audit),
    )

    principal = await service.authenticate('raw-key', '127.0.0.1')

    assert principal == ApiKeyPrincipal(key_id='key-1', role='operator', department='IT')
    assert repo.updated is True
    assert audit.successes


@pytest.mark.asyncio
async def test_authenticate_ip_not_allowed_raises() -> None:
    record = SimpleNamespace(
        key_id='key-1',
        key_prefix='abcd1234',
        is_active=True,
        expires_at=None,
        allowed_ips=['10.0.0.1'],
        role='operator',
        department='IT',
    )
    repo = FakeRepository(record=record)
    audit = FakeAuditService()
    service = AuthService(
        cast(ApiKeysRepository, repo),
        cast(AuditService, audit),
    )

    with pytest.raises(AuthFailure) as excinfo:
        await service.authenticate('raw-key', '127.0.0.1')

    assert excinfo.value.code == 'AUTH_INVALID_KEY'
    assert audit.failures
