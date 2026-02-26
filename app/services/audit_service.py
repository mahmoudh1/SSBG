from __future__ import annotations

import logging
from uuid import uuid4

from app.infrastructure.db.models.audit_log_entry import AuditLogEntryModel
from app.repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, repository: AuditRepository | None = None) -> None:
        self._repository = repository

    async def _persist_entry(
        self,
        action: str,
        resource: str,
        resource_id: str | None,
        actor_key_id: str | None,
        actor_role: str | None,
        status: str | None,
        reason: str | None,
    ) -> None:
        if self._repository is None:
            return
        record = AuditLogEntryModel(
            event_id=uuid4().hex,
            action=action,
            resource=resource,
            resource_id=resource_id,
            actor_key_id=actor_key_id,
            actor_role=actor_role,
            status=status,
            reason=reason,
        )
        await self._repository.create_entry(record)
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
        )
