from __future__ import annotations

from dataclasses import dataclass

from app.schemas.auth import ApiKeyPrincipal


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str
    required_permission: str
    role: str


class PolicyService:
    def __init__(self, role_permissions: dict[str, set[str]] | None = None) -> None:
        self._role_permissions = role_permissions or {
            'operator': {'backups'},
            'admin': {'backups', 'restores', 'audit', 'admin'},
            'super_admin': {'backups', 'restores', 'audit', 'admin'},
        }

    def authorize(
        self,
        principal: ApiKeyPrincipal | None,
        permission: str,
    ) -> AuthorizationDecision:
        if principal is None:
            return AuthorizationDecision(
                allowed=False,
                reason='missing_principal',
                required_permission=permission,
                role='unknown',
            )

        role = principal.role
        allowed_permissions = self._role_permissions.get(role, set())
        if permission in allowed_permissions:
            return AuthorizationDecision(
                allowed=True,
                reason='allowed',
                required_permission=permission,
                role=role,
            )

        return AuthorizationDecision(
            allowed=False,
            reason='permission_denied',
            required_permission=permission,
            role=role,
        )
