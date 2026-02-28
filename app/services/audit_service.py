from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from hashlib import sha512
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.infrastructure.db.models.audit_log_entry import AuditLogEntryModel
from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditChainFailure, AuditChainValidationResult, AuditEntrySummary

logger = logging.getLogger(__name__)


class AuditWriteError(Exception):
    def __init__(self, message: str = 'Audit write failed') -> None:
        super().__init__(message)
        self.message = message


class AuditService:
    def __init__(self, repository: AuditRepository | None = None) -> None:
        self._repository = repository

    @staticmethod
    def _build_entry_hash(
        chain_index: int,
        prev_hash: str | None,
        created_at: datetime | None,
        event_id: str,
        action: str,
        resource: str,
        resource_id: str | None,
        actor_key_id: str | None,
        actor_role: str | None,
        status: str | None,
        reason: str | None,
    ) -> str:
        payload = {
            'chain_index': chain_index,
            'prev_hash': prev_hash,
            'created_at': (
                created_at.astimezone(UTC).isoformat()
                if created_at is not None
                else None
            ),
            'event_id': event_id,
            'action': action,
            'resource': resource,
            'resource_id': resource_id,
            'actor_key_id': actor_key_id,
            'actor_role': actor_role,
            'status': status,
            'reason': reason,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return sha512(canonical.encode()).hexdigest()

    async def _persist_entry(
        self,
        action: str,
        resource: str,
        resource_id: str | None,
        actor_key_id: str | None,
        actor_role: str | None,
        status: str | None,
        reason: str | None,
        fail_secure: bool = True,
    ) -> None:
        if self._repository is None:
            return
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                cursor = await self._repository.get_latest_chain_cursor()
                if cursor is None:
                    chain_index = 1
                    prev_hash = None
                else:
                    chain_index = cursor[0] + 1
                    prev_hash = cursor[1]
                created_at = datetime.now(UTC)
                event_id = uuid4().hex
                entry_hash = self._build_entry_hash(
                    chain_index=chain_index,
                    prev_hash=prev_hash,
                    created_at=created_at,
                    event_id=event_id,
                    action=action,
                    resource=resource,
                    resource_id=resource_id,
                    actor_key_id=actor_key_id,
                    actor_role=actor_role,
                    status=status,
                    reason=reason,
                )
                record = AuditLogEntryModel(
                    chain_index=chain_index,
                    prev_hash=prev_hash,
                    entry_hash=entry_hash,
                    created_at=created_at,
                    event_id=event_id,
                    action=action,
                    resource=resource,
                    resource_id=resource_id,
                    actor_key_id=actor_key_id,
                    actor_role=actor_role,
                    status=status,
                    reason=reason,
                )
                await self._repository.create_entry(record)
                return
            except IntegrityError as exc:
                if attempt < max_attempts - 1:
                    continue
                if fail_secure:
                    raise AuditWriteError() from exc
                logger.exception('Audit write conflict; suppressed in best-effort mode')
                return
            except Exception as exc:
                if fail_secure:
                    raise AuditWriteError() from exc
                logger.exception('Audit write failure; suppressed in best-effort mode')
                return
    async def record_auth_failure(
        self,
        key_prefix: str,
        reason: str,
        client_ip: str | None,
    ) -> None:
        logger.warning(
            'Auth failure',
            extra={'key_prefix': key_prefix, 'reason': reason, 'client_ip': client_ip},
        )
        await self._persist_entry(
            action='auth_failure',
            resource='api_key',
            resource_id=key_prefix or None,
            actor_key_id=None,
            actor_role=None,
            status='denied',
            reason=reason,
            fail_secure=False,
        )

    async def record_auth_success(
        self,
        key_id: str,
        client_ip: str | None,
    ) -> None:
        logger.info('Auth success', extra={'key_id': key_id, 'client_ip': client_ip})
        await self._persist_entry(
            action='auth_success',
            resource='api_key',
            resource_id=key_id,
            actor_key_id=key_id,
            actor_role=None,
            status='success',
            reason=None,
            fail_secure=False,
        )

    async def record_mfa_outcome(
        self,
        key_id: str | None,
        outcome: str,
        reason: str | None,
        client_ip: str | None,
    ) -> None:
        logger.info(
            'MFA outcome',
            extra={
                'key_id': key_id,
                'outcome': outcome,
                'reason': reason,
                'client_ip': client_ip,
            },
        )
        await self._persist_entry(
            action='mfa_outcome',
            resource='restore',
            resource_id=None,
            actor_key_id=key_id,
            actor_role=None,
            status=outcome,
            reason=reason,
            fail_secure=False,
        )

    async def record_authorization_denied(
        self,
        key_id: str | None,
        role: str,
        permission: str,
        reason: str,
        client_ip: str | None,
    ) -> None:
        logger.warning(
            'Authorization denied',
            extra={
                'key_id': key_id,
                'role': role,
                'permission': permission,
                'reason': reason,
                'client_ip': client_ip,
            },
        )
        await self._persist_entry(
            action='authorization_denied',
            resource=permission,
            resource_id=None,
            actor_key_id=key_id,
            actor_role=role,
            status='denied',
            reason=reason,
            fail_secure=True,
        )

    async def record_admin_action(
        self,
        actor_key_id: str | None,
        action: str,
        resource: str,
        resource_id: str | None,
        client_ip: str | None,
    ) -> None:
        logger.info(
            'Admin action',
            extra={
                'actor_key_id': actor_key_id,
                'action': action,
                'resource': resource,
                'resource_id': resource_id,
                'client_ip': client_ip,
            },
        )
        await self._persist_entry(
            action=action,
            resource=resource,
            resource_id=resource_id,
            actor_key_id=actor_key_id,
            actor_role=None,
            status='success',
            reason=None,
            fail_secure=True,
        )

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
        logger.info(
            'Policy decision',
            extra={
                'key_id': key_id,
                'operation': operation,
                'allowed': allowed,
                'reason': reason,
                'reason_category': reason_category,
                'classification': classification,
                'client_ip': client_ip,
            },
        )
        await self._persist_entry(
            action='policy_decision',
            resource=operation,
            resource_id=classification,
            actor_key_id=key_id,
            actor_role=None,
            status='allowed' if allowed else 'denied',
            reason=reason_category,
            fail_secure=True,
        )

    async def record_backup_event(
        self,
        action: str,
        backup_id: str,
        actor_key_id: str | None,
        actor_role: str | None,
        status: str,
        reason: str | None,
    ) -> None:
        logger.info(
            'Backup event',
            extra={
                'action': action,
                'backup_id': backup_id,
                'actor_key_id': actor_key_id,
                'actor_role': actor_role,
                'status': status,
                'reason': reason,
            },
        )
        await self._persist_entry(
            action=action,
            resource='backup',
            resource_id=backup_id,
            actor_key_id=actor_key_id,
            actor_role=actor_role,
            status=status,
            reason=reason,
            fail_secure=True,
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
        logger.info(
            'Restore event',
            extra={
                'action': action,
                'backup_id': backup_id,
                'actor_key_id': actor_key_id,
                'actor_role': actor_role,
                'status': status,
                'reason': reason,
            },
        )
        await self._persist_entry(
            action=action,
            resource='restore',
            resource_id=backup_id,
            actor_key_id=actor_key_id,
            actor_role=actor_role,
            status=status,
            reason=reason,
            fail_secure=True,
        )

    async def validate_chain(self) -> AuditChainValidationResult:
        if self._repository is None:
            return AuditChainValidationResult(valid=True, checked_entries=0, failure=None)
        offset = 0
        limit = 1000
        expected_chain_index = 1
        expected_prev_hash: str | None = None

        while True:
            entries = await self._repository.list_entries(offset=offset, limit=limit)
            if not entries:
                break
            for entry in entries:
                if entry.chain_index != expected_chain_index:
                    return AuditChainValidationResult(
                        valid=False,
                        checked_entries=expected_chain_index - 1,
                        failure=AuditChainFailure(
                            chain_index=entry.chain_index,
                            event_id=entry.event_id,
                            reason='chain_index_out_of_sequence',
                        ),
                    )
                if entry.prev_hash != expected_prev_hash:
                    return AuditChainValidationResult(
                        valid=False,
                        checked_entries=expected_chain_index - 1,
                        failure=AuditChainFailure(
                            chain_index=entry.chain_index,
                            event_id=entry.event_id,
                            reason='prev_hash_mismatch',
                        ),
                    )

                computed_hash = self._build_entry_hash(
                    chain_index=entry.chain_index,
                    prev_hash=entry.prev_hash,
                    created_at=entry.created_at,
                    event_id=entry.event_id,
                    action=entry.action,
                    resource=entry.resource,
                    resource_id=entry.resource_id,
                    actor_key_id=entry.actor_key_id,
                    actor_role=entry.actor_role,
                    status=entry.status,
                    reason=entry.reason,
                )
                if computed_hash != entry.entry_hash:
                    return AuditChainValidationResult(
                        valid=False,
                        checked_entries=expected_chain_index - 1,
                        failure=AuditChainFailure(
                            chain_index=entry.chain_index,
                            event_id=entry.event_id,
                            reason='entry_hash_mismatch',
                        ),
                    )

                expected_prev_hash = entry.entry_hash
                expected_chain_index += 1
            offset += len(entries)

        return AuditChainValidationResult(
            valid=True,
            checked_entries=expected_chain_index - 1,
            failure=None,
        )

    async def list_audit_entries(
        self,
        offset: int = 0,
        limit: int = 100,
        action: str | None = None,
        resource: str | None = None,
        status: str | None = None,
    ) -> list[AuditEntrySummary]:
        if self._repository is None:
            return []
        records = await self._repository.list_entries(
            offset=offset,
            limit=limit,
            action=action,
            resource=resource,
            status=status,
        )
        return [
            AuditEntrySummary(
                chain_index=record.chain_index,
                event_id=record.event_id,
                action=record.action,
                resource=record.resource,
                resource_id=record.resource_id,
                actor_key_id=record.actor_key_id,
                actor_role=record.actor_role,
                status=record.status,
                reason=record.reason,
                created_at=record.created_at,
            )
            for record in records
        ]
