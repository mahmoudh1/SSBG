from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import ClassificationLevel
from app.schemas.auth import ApiKeyPrincipal


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str
    required_permission: str
    role: str


@dataclass(frozen=True)
class BackupPolicyDecision:
    allowed: bool
    reason: str
    reason_category: str
    role: str
    classification: ClassificationLevel


@dataclass(frozen=True)
class RestorePolicyDecision:
    allowed: bool
    reason: str
    reason_category: str
    role: str
    classification: ClassificationLevel


class PolicyService:
    def __init__(
        self,
        role_permissions: dict[str, set[str]] | None = None,
        backup_classification_roles: dict[ClassificationLevel, set[str]] | None = None,
    ) -> None:
        self._role_permissions = role_permissions or {
            'operator': {'backups'},
            'admin': {'backups', 'restores', 'audit', 'admin'},
            'super_admin': {'backups', 'restores', 'audit', 'admin'},
        }
        self._backup_classification_roles = backup_classification_roles or {
            ClassificationLevel.PUBLIC: {'operator', 'admin', 'super_admin'},
            ClassificationLevel.INTERNAL: {'operator', 'admin', 'super_admin'},
            ClassificationLevel.CONFIDENTIAL: {'operator', 'admin', 'super_admin'},
            ClassificationLevel.SECRET: {'operator', 'admin', 'super_admin'},
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

    def evaluate_backup(
        self,
        principal: ApiKeyPrincipal | None,
        classification: ClassificationLevel,
    ) -> BackupPolicyDecision:
        if principal is None:
            return BackupPolicyDecision(
                allowed=False,
                reason='Missing principal',
                reason_category='missing_principal',
                role='unknown',
                classification=classification,
            )
        allowed_roles = self._backup_classification_roles.get(classification, set())
        if principal.role in allowed_roles:
            return BackupPolicyDecision(
                allowed=True,
                reason='Backup allowed',
                reason_category='allowed',
                role=principal.role,
                classification=classification,
            )
        return BackupPolicyDecision(
            allowed=False,
            reason='Role not permitted for classification',
            reason_category='role_restricted',
            role=principal.role,
            classification=classification,
        )

    def evaluate_restore(
        self,
        principal: ApiKeyPrincipal | None,
        classification: ClassificationLevel,
    ) -> RestorePolicyDecision:
        if principal is None:
            return RestorePolicyDecision(
                allowed=False,
                reason='Missing principal',
                reason_category='missing_principal',
                role='unknown',
                classification=classification,
            )
        # Restore remains more restrictive than backup; RBAC already gates `restores`.
        if principal.role in {'admin', 'super_admin'}:
            return RestorePolicyDecision(
                allowed=True,
                reason='Restore allowed',
                reason_category='allowed',
                role=principal.role,
                classification=classification,
            )
        return RestorePolicyDecision(
            allowed=False,
            reason='Role not permitted for restore',
            reason_category='role_restricted',
            role=principal.role,
            classification=classification,
        )
