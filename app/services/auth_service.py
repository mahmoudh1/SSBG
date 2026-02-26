from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha512

from app.repositories.api_keys_repository import ApiKeysRepository
from app.schemas.auth import ApiKeyPrincipal
from app.services.audit_service import AuditService


class AuthFailure(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class AuthService:
    def __init__(self, repository: ApiKeysRepository, audit_service: AuditService) -> None:
        self._repository = repository
        self._audit_service = audit_service

    async def authenticate(
        self,
        raw_key: str,
        client_ip: str | None,
    ) -> ApiKeyPrincipal:
        key_prefix = raw_key[:8] if raw_key else ''
        if not raw_key:
            await self._audit_service.record_auth_failure(
                key_prefix=key_prefix,
                reason='missing_key',
                client_ip=client_ip,
            )
            raise AuthFailure('AUTH_INVALID_KEY', 'Missing API key')

        key_hash = sha512(raw_key.encode()).hexdigest()
        record = await self._repository.get_by_hash(key_hash)
        if record is None:
            await self._audit_service.record_auth_failure(
                key_prefix=key_prefix,
                reason='key_not_found',
                client_ip=client_ip,
            )
            raise AuthFailure('AUTH_INVALID_KEY', 'Invalid API key')

        if not record.is_active:
            await self._audit_service.record_auth_failure(
                key_prefix=record.key_prefix,
                reason='revoked',
                client_ip=client_ip,
            )
            raise AuthFailure('AUTH_INVALID_KEY', 'Revoked API key')

        now = datetime.now(timezone.utc)
        if record.expires_at is not None and record.expires_at <= now:
            await self._audit_service.record_auth_failure(
                key_prefix=record.key_prefix,
                reason='expired',
                client_ip=client_ip,
            )
            raise AuthFailure('AUTH_INVALID_KEY', 'Expired API key')

        if record.allowed_ips:
            if client_ip is None or client_ip not in record.allowed_ips:
                await self._audit_service.record_auth_failure(
                    key_prefix=record.key_prefix,
                    reason='ip_not_allowed',
                    client_ip=client_ip,
                )
                raise AuthFailure('AUTH_INVALID_KEY', 'API key not allowed from this IP')

        await self._repository.update_last_used(record, client_ip)
        await self._audit_service.record_auth_success(record.key_id, client_ip)

        return ApiKeyPrincipal(
            key_id=record.key_id,
            role=record.role,
            department=record.department,
        )
