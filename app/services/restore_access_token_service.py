from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable


@dataclass(frozen=True)
class RestoreAccessTokenRecord:
    token: str
    backup_id: str
    actor_key_id: str | None
    issued_at: datetime
    expires_at: datetime


class RestoreAccessTokenInvalid(Exception):
    def __init__(self, message: str = 'Invalid restore access token') -> None:
        super().__init__(message)
        self.message = message


class RestoreAccessTokenExpired(Exception):
    def __init__(self, message: str = 'Restore access token expired') -> None:
        super().__init__(message)
        self.message = message


class RestoreAccessTokenForbidden(Exception):
    def __init__(
        self,
        message: str = 'Restore access token is not valid for this principal',
    ) -> None:
        super().__init__(message)
        self.message = message


class RestoreAccessTokenService:
    def __init__(
        self,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._records: dict[str, RestoreAccessTokenRecord] = {}
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    def _purge_expired(self, now: datetime) -> None:
        expired = [token for token, record in self._records.items() if record.expires_at <= now]
        for token in expired:
            del self._records[token]

    def active_record_count(self) -> int:
        self._purge_expired(self._now_provider())
        return len(self._records)

    def issue_token(
        self,
        backup_id: str,
        actor_key_id: str | None,
        ttl_seconds: int,
    ) -> RestoreAccessTokenRecord:
        now = self._now_provider()
        self._purge_expired(now)
        if ttl_seconds <= 0:
            ttl_seconds = 1
        issued_at = now
        expires_at = issued_at + timedelta(seconds=ttl_seconds)
        token = secrets.token_urlsafe(24)
        record = RestoreAccessTokenRecord(
            token=token,
            backup_id=backup_id,
            actor_key_id=actor_key_id,
            issued_at=issued_at,
            expires_at=expires_at,
        )
        self._records[token] = record
        return record

    def validate_token(
        self,
        token: str,
        actor_key_id: str | None = None,
    ) -> RestoreAccessTokenRecord:
        record = self._records.get(token)
        if record is None:
            raise RestoreAccessTokenInvalid()
        now = self._now_provider()
        if record.expires_at <= now:
            del self._records[token]
            raise RestoreAccessTokenExpired()
        if record.actor_key_id is not None and actor_key_id != record.actor_key_id:
            raise RestoreAccessTokenForbidden()
        return record
