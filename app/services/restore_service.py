from __future__ import annotations

from hashlib import sha512
from typing import Any, Protocol

from app.core.enums import ClassificationLevel, IncidentLevel
from app.infrastructure.crypto.aes_gcm import decrypt
from app.infrastructure.storage.minio_client import ObjectStorageError
from app.schemas.auth import ApiKeyPrincipal
from app.schemas.restores import RestoreMetadataSummary, RestoreRequest
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.incident_service import IncidentService
from app.services.policy_service import PolicyService


class RestoreMetadataNotFound(Exception):
    def __init__(self, backup_id: str) -> None:
        super().__init__(f'Backup metadata not found for {backup_id}')
        self.backup_id = backup_id


class RestorePolicyDenied(Exception):
    def __init__(self, message: str, reason_category: str) -> None:
        super().__init__(message)
        self.message = message
        self.reason_category = reason_category


class RestoreIncidentRestricted(Exception):
    def __init__(self, message: str, reason_category: str) -> None:
        super().__init__(message)
        self.message = message
        self.reason_category = reason_category


class RestoreIntegrityFailed(Exception):
    def __init__(self, message: str = 'Restore integrity verification failed') -> None:
        super().__init__(message)
        self.message = message


class RestoreExecutionUnavailable(Exception):
    def __init__(self, message: str = 'Restore service unavailable') -> None:
        super().__init__(message)
        self.message = message


class BackupsRepositoryLike(Protocol):
    async def get_by_backup_id(self, backup_id: str) -> Any | None:
        ...


class KeyStoreLike(Protocol):
    def get_key(self, version_id: str) -> Any:
        ...


class ObjectStorageLike(Protocol):
    async def get_object(self, bucket: str, object_name: str) -> bytes | None:
        ...


class RestoreSettingsLike(Protocol):
    minio_bucket: str
    restore_access_token_ttl_seconds: int


class RestoreAccessTokenServiceLike(Protocol):
    def issue_token(
        self,
        backup_id: str,
        actor_key_id: str | None,
        ttl_seconds: int,
    ) -> Any:
        ...


class RestoreService:
    def __init__(
        self,
        backups_repository: BackupsRepositoryLike,
        auth_service: AuthService,
        policy_service: PolicyService,
        audit_service: AuditService,
        incident_service: IncidentService,
        settings: RestoreSettingsLike | None = None,
        key_store: KeyStoreLike | None = None,
        storage: ObjectStorageLike | None = None,
        restore_access_token_service: RestoreAccessTokenServiceLike | None = None,
    ) -> None:
        self._backups_repository = backups_repository
        self._auth_service = auth_service
        self._policy_service = policy_service
        self._audit_service = audit_service
        self._incident_service = incident_service
        self._settings = settings
        self._key_store = key_store
        self._storage = storage
        self._restore_access_token_service = restore_access_token_service

    async def _record_restore_failure(
        self,
        metadata: Any,
        principal: ApiKeyPrincipal | None,
        reason: str,
    ) -> None:
        await self._audit_service.record_restore_event(
            action='restore_failed',
            backup_id=metadata.backup_id,
            actor_key_id=principal.key_id if principal else None,
            actor_role=principal.role if principal else None,
            status='FAILED',
            reason=reason,
        )

    def _require_restore_field(self, metadata: Any, field_name: str) -> str:
        value = getattr(metadata, field_name, None)
        if not isinstance(value, str) or not value:
            raise RestoreExecutionUnavailable()
        return value

    async def _restore_and_verify(self, metadata: Any) -> bytes:
        if self._settings is None or self._key_store is None or self._storage is None:
            raise RestoreExecutionUnavailable()
        storage_path = self._require_restore_field(metadata, 'storage_path')
        key_version = self._require_restore_field(metadata, 'key_version')
        nonce_hex = self._require_restore_field(metadata, 'nonce')
        checksum_plaintext = self._require_restore_field(metadata, 'checksum_plaintext')

        try:
            ciphertext_blob = await self._storage.get_object(
                self._settings.minio_bucket,
                storage_path,
            )
        except ObjectStorageError as exc:
            raise RestoreExecutionUnavailable() from exc
        except Exception as exc:
            raise RestoreExecutionUnavailable() from exc
        if ciphertext_blob is None or len(ciphertext_blob) < 28:
            raise RestoreIntegrityFailed()

        checksum_ciphertext = getattr(metadata, 'checksum_ciphertext', None)
        if isinstance(checksum_ciphertext, str) and checksum_ciphertext:
            if sha512(ciphertext_blob).hexdigest() != checksum_ciphertext:
                raise RestoreIntegrityFailed()

        nonce = ciphertext_blob[:12]
        tag = ciphertext_blob[12:28]
        ciphertext = ciphertext_blob[28:]
        try:
            nonce_from_metadata = bytes.fromhex(nonce_hex)
        except ValueError as exc:
            raise RestoreIntegrityFailed() from exc
        if nonce != nonce_from_metadata:
            raise RestoreIntegrityFailed()

        try:
            if hasattr(self._key_store, 'get_key'):
                key_material = self._key_store.get_key(key_version)
            else:
                key_material = self._key_store.get_active_key()  # type: ignore[attr-defined]
        except Exception as exc:
            raise RestoreExecutionUnavailable() from exc

        try:
            plaintext = decrypt(ciphertext, key_material.key_bytes, nonce, tag)
        except Exception as exc:
            raise RestoreIntegrityFailed() from exc
        if sha512(plaintext).hexdigest() != checksum_plaintext:
            raise RestoreIntegrityFailed()
        return plaintext

    async def load_restore_metadata(
        self,
        request: RestoreRequest,
        principal: ApiKeyPrincipal | None,
        client_ip: str | None,
        mfa_token: str | None,
    ) -> dict[str, object]:
        await self._auth_service.validate_mfa_token(principal, mfa_token, client_ip)

        metadata = await self._backups_repository.get_by_backup_id(request.backup_id)
        if metadata is None:
            raise RestoreMetadataNotFound(request.backup_id)

        try:
            classification = ClassificationLevel(metadata.classification)
        except ValueError as exc:
            await self._record_restore_failure(
                metadata,
                principal,
                'invalid_metadata_classification',
            )
            raise RestoreExecutionUnavailable('Restore metadata is invalid') from exc
        decision = self._policy_service.evaluate_restore(principal, classification)
        await self._audit_service.record_policy_decision(
            key_id=principal.key_id if principal else None,
            operation='restore_authorize',
            allowed=decision.allowed,
            reason=decision.reason,
            reason_category=decision.reason_category,
            classification=metadata.classification,
            client_ip=client_ip,
        )
        if not decision.allowed:
            raise RestorePolicyDenied(decision.reason, decision.reason_category)

        backup = RestoreMetadataSummary(
            backup_id=metadata.backup_id,
            classification=metadata.classification,
            source_system=metadata.source_system,
            status=metadata.status,
            key_version=metadata.key_version,
            created_at=getattr(metadata, 'created_at', None),
        )

        incident_level = self._incident_service.get_current_level()
        if incident_level == IncidentLevel.QUARANTINE:
            await self._audit_service.record_restore_event(
                action='restore_restricted_pending_manual_review',
                backup_id=metadata.backup_id,
                actor_key_id=principal.key_id if principal else None,
                actor_role=principal.role if principal else None,
                status='PENDING_MANUAL_REVIEW',
                reason='incident_quarantine',
            )
            return {
                'status': 'pending_manual_review',
                'backup': backup.model_dump(mode='json'),
                'restriction_reason': 'incident_quarantine',
                'next_step': 'manual_review',
            }
        if incident_level == IncidentLevel.LOCKDOWN:
            await self._audit_service.record_restore_event(
                action='restore_restricted_blocked',
                backup_id=metadata.backup_id,
                actor_key_id=principal.key_id if principal else None,
                actor_role=principal.role if principal else None,
                status='BLOCKED',
                reason='incident_lockdown',
            )
            raise RestoreIncidentRestricted(
                'Restore blocked by active incident level',
                'incident_lockdown',
            )

        # Backward-compatible fallback for tests that construct RestoreService without
        # storage/crypto adapters; production DI provides these adapters.
        if self._settings is None or self._key_store is None or self._storage is None:
            return {
                'status': 'metadata_loaded',
                'backup': backup.model_dump(mode='json'),
                'next_step': 'mfa_policy_authorization',
            }

        try:
            plaintext = await self._restore_and_verify(metadata)
        except RestoreIntegrityFailed:
            await self._record_restore_failure(metadata, principal, 'integrity_failed')
            raise
        except RestoreExecutionUnavailable:
            await self._record_restore_failure(metadata, principal, 'restore_unavailable')
            raise

        await self._audit_service.record_restore_event(
            action='restore_completed',
            backup_id=metadata.backup_id,
            actor_key_id=principal.key_id if principal else None,
            actor_role=principal.role if principal else None,
            status='COMPLETED',
            reason=None,
        )
        response: dict[str, object] = {
            'status': 'restore_completed',
            'backup': backup.model_dump(mode='json'),
            'integrity_verified': True,
            'restored_size': len(plaintext),
            'next_step': 'restore_access_token',
        }
        if self._restore_access_token_service is not None and self._settings is not None:
            token_record = self._restore_access_token_service.issue_token(
                backup_id=metadata.backup_id,
                actor_key_id=principal.key_id if principal else None,
                ttl_seconds=self._settings.restore_access_token_ttl_seconds,
            )
            response['restore_token'] = token_record.token
            response['restore_token_expires_at'] = token_record.expires_at.isoformat()
            response['restore_token_ttl_seconds'] = (
                self._settings.restore_access_token_ttl_seconds
            )
        return response
