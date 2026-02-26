from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class AuditService:
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
