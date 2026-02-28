from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from app.core.enums import IncidentLevel
from app.infrastructure.crypto.key_store_fs import KeyMaterial
from app.infrastructure.db.models.key_version import KeyVersionModel
from app.schemas.auth import ApiKeyPrincipal
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService, MfaFailure
from app.services.incident_service import InvalidIncidentTransition


class KeyRotationError(Exception):
    def __init__(self, message: str, reason_category: str) -> None:
        super().__init__(message)
        self.message = message
        self.reason_category = reason_category


class CryptoShredError(Exception):
    def __init__(self, message: str, reason_category: str) -> None:
        super().__init__(message)
        self.message = message
        self.reason_category = reason_category


class KeyVersionNotFoundError(Exception):
    def __init__(self, version_id: str) -> None:
        super().__init__(f'Key version {version_id} not found')
        self.version_id = version_id


@dataclass(frozen=True)
class KeyVersionSnapshot:
    version_id: str
    is_active: bool
    is_destroyed: bool
    rotated_from_version: str | None
    created_by_key_id: str | None
    rotation_reason: str | None
    created_at: datetime | None
    activated_at: datetime | None
    destroyed_at: datetime | None


class KeyStoreLike(Protocol):
    def get_key(self, version_id: str) -> KeyMaterial:
        ...

    def get_active_key(self) -> KeyMaterial:
        ...


class KeyVersionsRepositoryLike(Protocol):
    async def get_active(self) -> KeyVersionModel | None:
        ...

    async def get_by_version_id(self, version_id: str) -> KeyVersionModel | None:
        ...

    async def list_versions(self) -> list[KeyVersionModel]:
        ...

    async def create_version(self, record: KeyVersionModel) -> KeyVersionModel:
        ...

    async def set_active(
        self,
        to_version_id: str,
        rotated_from_version: str | None,
        reason: str | None,
        actor_key_id: str | None,
    ) -> KeyVersionModel | None:
        ...

    async def mark_destroyed(
        self,
        version_id: str,
        *,
        destroyed_at: datetime | None = None,
        commit: bool = True,
    ) -> KeyVersionModel | None:
        ...

    @property
    def session(self) -> object:
        ...


class BackupsRepositoryLike(Protocol):
    async def mark_irreversible_by_key_version(
        self,
        key_version: str,
        reason: str,
        *,
        shredded_at: datetime | None = None,
        commit: bool = True,
    ) -> int:
        ...

    async def summarize_by_key_version(self, key_version: str) -> dict[str, object]:
        ...

    @property
    def session(self) -> object:
        ...


class IncidentServiceLike(Protocol):
    async def get_current_level(self) -> IncidentLevel:
        ...

    async def transition_to(
        self,
        new_level: IncidentLevel,
        changed_by_key_id: str | None,
        reason: str | None,
    ) -> object:
        ...


class KeyManagementService:
    def __init__(
        self,
        repository: KeyVersionsRepositoryLike,
        key_store: KeyStoreLike,
        audit_service: AuditService,
        backups_repository: BackupsRepositoryLike | None = None,
        incident_service: IncidentServiceLike | None = None,
        auth_service: AuthService | None = None,
    ) -> None:
        self._repository = repository
        self._key_store = key_store
        self._audit_service = audit_service
        self._backups_repository = backups_repository
        self._incident_service = incident_service
        self._auth_service = auth_service

    @staticmethod
    def _to_snapshot(record: KeyVersionModel) -> KeyVersionSnapshot:
        return KeyVersionSnapshot(
            version_id=record.version_id,
            is_active=record.is_active,
            is_destroyed=record.is_destroyed,
            rotated_from_version=record.rotated_from_version,
            created_by_key_id=record.created_by_key_id,
            rotation_reason=record.rotation_reason,
            created_at=record.created_at,
            activated_at=record.activated_at,
            destroyed_at=record.destroyed_at,
        )

    async def _ensure_active_seed(self) -> KeyVersionModel:
        active = await self._repository.get_active()
        if active is not None:
            return active
        key_material = self._key_store.get_active_key()
        seeded = await self._repository.get_by_version_id(key_material.version_id)
        if seeded is None:
            seeded = await self._repository.create_version(
                KeyVersionModel(
                    version_id=key_material.version_id,
                    is_active=False,
                    is_destroyed=False,
                ),
            )
        activated = await self._repository.set_active(
            to_version_id=seeded.version_id,
            rotated_from_version=None,
            reason='initial_seed',
            actor_key_id=None,
        )
        if activated is None:
            raise KeyRotationError('Failed to seed active key version', 'seed_failed')
        return activated

    async def get_active_key_material(self) -> KeyMaterial:
        active = await self._ensure_active_seed()
        if active.is_destroyed:
            raise KeyRotationError('Active key version is destroyed', 'destroyed_active_key')
        try:
            return self._key_store.get_key(active.version_id)
        except Exception as exc:
            raise KeyRotationError(
                'Active key material unavailable',
                'key_material_missing',
            ) from exc

    async def rotate_active_version(
        self,
        to_version_id: str,
        actor_key_id: str | None,
        reason: str | None,
        client_ip: str | None,
    ) -> KeyVersionSnapshot:
        current = await self._ensure_active_seed()
        if current.version_id == to_version_id:
            raise KeyRotationError('Target key version already active', 'no_state_change')
        try:
            self._key_store.get_key(to_version_id)
        except Exception as exc:
            raise KeyRotationError('Target key material not found', 'key_material_missing') from exc
        target = await self._repository.get_by_version_id(to_version_id)
        if target is None:
            target = await self._repository.create_version(
                KeyVersionModel(
                    version_id=to_version_id,
                    is_active=False,
                    is_destroyed=False,
                ),
            )
        if target.is_destroyed:
            raise KeyRotationError('Target key version destroyed', 'target_destroyed')
        updated = await self._repository.set_active(
            to_version_id=to_version_id,
            rotated_from_version=current.version_id,
            reason=reason,
            actor_key_id=actor_key_id,
        )
        if updated is None:
            raise KeyRotationError('Failed to activate target key version', 'activation_failed')
        await self._audit_service.record_key_rotation(
            actor_key_id=actor_key_id,
            from_version=current.version_id,
            to_version=to_version_id,
            client_ip=client_ip,
        )
        return self._to_snapshot(updated)

    async def list_versions(self) -> list[KeyVersionSnapshot]:
        records = await self._repository.list_versions()
        return [self._to_snapshot(record) for record in records]

    async def get_version(self, version_id: str) -> KeyVersionSnapshot:
        record = await self._repository.get_by_version_id(version_id)
        if record is None:
            raise KeyVersionNotFoundError(version_id)
        return self._to_snapshot(record)

    async def get_crypto_shred_outcome(self, version_id: str) -> dict[str, object]:
        version = await self._repository.get_by_version_id(version_id)
        if version is None:
            raise KeyVersionNotFoundError(version_id)
        summary = (
            await self._backups_repository.summarize_by_key_version(version_id)
            if self._backups_repository is not None
            else {
                'total_backups': 0,
                'irreversible_backups': 0,
                'active_backups': 0,
                'processing_backups': 0,
                'failed_backups': 0,
                'last_shredded_at': None,
                'irreversible_reason': None,
            }
        )
        return {
            'version_id': version_id,
            'key_destroyed': version.is_destroyed,
            'destroyed_at': version.destroyed_at,
            'total_backups': summary['total_backups'],
            'irreversible_backups': summary['irreversible_backups'],
            'active_backups': summary['active_backups'],
            'processing_backups': summary['processing_backups'],
            'failed_backups': summary['failed_backups'],
            'last_shredded_at': summary['last_shredded_at'],
            'irreversible_reason': summary['irreversible_reason'],
        }

    async def execute_crypto_shred(
        self,
        version_id: str,
        principal: ApiKeyPrincipal | None,
        mfa_token: str | None,
        confirmation: str,
        client_ip: str | None,
    ) -> dict[str, object]:
        if principal is None or principal.role != 'super_admin':
            await self._audit_service.record_admin_action(
                actor_key_id=principal.key_id if principal else None,
                action='crypto_shred_denied',
                resource='key_version',
                resource_id=version_id,
                client_ip=client_ip,
            )
            raise CryptoShredError('Privileged role required', 'insufficient_role')
        expected_confirmation = f'DESTROY {version_id}'
        if confirmation != expected_confirmation:
            await self._audit_service.record_admin_action(
                actor_key_id=principal.key_id,
                action='crypto_shred_denied',
                resource='key_version',
                resource_id=version_id,
                client_ip=client_ip,
            )
            raise CryptoShredError('Explicit confirmation mismatch', 'missing_confirmation')
        if self._auth_service is None:
            raise CryptoShredError('Auth service unavailable', 'auth_unavailable')
        try:
            await self._auth_service.validate_mfa_token(principal, mfa_token, client_ip)
        except MfaFailure as exc:
            await self._audit_service.record_admin_action(
                actor_key_id=principal.key_id,
                action='crypto_shred_denied',
                resource='key_version',
                resource_id=version_id,
                client_ip=client_ip,
            )
            raise CryptoShredError(exc.message, exc.code.lower()) from exc
        await self._audit_service.record_admin_action(
            actor_key_id=principal.key_id,
            action='crypto_shred_started',
            resource='key_version',
            resource_id=version_id,
            client_ip=client_ip,
        )
        affected_backups = 0
        timestamp = datetime.now(timezone.utc)
        repository_session = getattr(self._repository, 'session', None)
        backups_session = getattr(self._backups_repository, 'session', None)
        supports_atomic_transition = (
            self._backups_repository is not None
            and repository_session is not None
            and repository_session is backups_session
            and hasattr(repository_session, 'begin')
        )
        try:
            if supports_atomic_transition:
                async with repository_session.begin():
                    target = await self._repository.get_by_version_id(version_id)
                    if target is None:
                        raise CryptoShredError('Key version not found', 'key_not_found')
                    if target.is_destroyed:
                        raise CryptoShredError('Key version already destroyed', 'already_destroyed')
                    destroyed = await self._repository.mark_destroyed(
                        version_id,
                        destroyed_at=timestamp,
                        commit=False,
                    )
                    if destroyed is None:
                        raise CryptoShredError('Failed to mark key destroyed', 'destroy_failed')
                    affected_backups = await self._backups_repository.mark_irreversible_by_key_version(
                        version_id,
                        'crypto_shredded',
                        shredded_at=timestamp,
                        commit=False,
                    )
            else:
                target = await self._repository.get_by_version_id(version_id)
                if target is None:
                    raise CryptoShredError('Key version not found', 'key_not_found')
                if target.is_destroyed:
                    raise CryptoShredError('Key version already destroyed', 'already_destroyed')
                destroyed = await self._repository.mark_destroyed(version_id)
                if destroyed is None:
                    raise CryptoShredError('Failed to mark key destroyed', 'destroy_failed')
                if self._backups_repository is not None:
                    affected_backups = await self._backups_repository.mark_irreversible_by_key_version(
                        version_id,
                        'crypto_shredded',
                        shredded_at=timestamp,
                    )
        except CryptoShredError as exc:
            if exc.reason_category in {'key_not_found', 'already_destroyed'}:
                await self._audit_service.record_admin_action(
                    actor_key_id=principal.key_id,
                    action='crypto_shred_denied',
                    resource='key_version',
                    resource_id=version_id,
                    client_ip=client_ip,
                )
            raise
        incident_effect = 'unchanged'
        if self._incident_service is not None:
            try:
                current_level = await self._incident_service.get_current_level()
                if current_level != IncidentLevel.LOCKDOWN:
                    await self._incident_service.transition_to(
                        new_level=IncidentLevel.LOCKDOWN,
                        changed_by_key_id=principal.key_id,
                        reason='crypto_shred_executed',
                    )
                    incident_effect = 'escalated_to_lockdown'
                else:
                    incident_effect = 'already_lockdown'
            except InvalidIncidentTransition:
                incident_effect = 'transition_denied'
            await self._audit_service.record_admin_action(
                actor_key_id=principal.key_id,
                action='incident_effect_applied',
                resource='incident',
                resource_id=incident_effect,
                client_ip=client_ip,
            )
        await self._audit_service.record_admin_action(
            actor_key_id=principal.key_id,
            action='crypto_shred_completed',
            resource='key_version',
            resource_id=version_id,
            client_ip=client_ip,
        )
        return {
            'version_id': version_id,
            'destroyed': True,
            'affected_backups': affected_backups,
            'incident_effect': incident_effect,
        }
