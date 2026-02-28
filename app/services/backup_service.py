from __future__ import annotations

from hashlib import sha512
from typing import Any, Protocol
from uuid import uuid4

from app.core.enums import BackupStatus, ClassificationLevel
from app.infrastructure.crypto.aes_gcm import encrypt
from app.infrastructure.crypto.key_store_fs import KeyMaterial
from app.infrastructure.db.models.backup_metadata import BackupMetadataModel
from app.infrastructure.storage.minio_client import ObjectStorageError
from app.schemas.auth import ApiKeyPrincipal
from app.schemas.backups import BackupRequest


class BackupValidationError(Exception):
    def __init__(self, message: str, details: list[dict[str, object]]) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class BackupPolicyDenied(Exception):
    def __init__(self, message: str, reason_category: str) -> None:
        super().__init__(message)
        self.message = message
        self.reason_category = reason_category


class BackupProcessingError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class KeyStore(Protocol):
    def get_active_key(self) -> KeyMaterial:
        ...


class ObjectStorage(Protocol):
    async def put_object(self, bucket: str, object_name: str, data: bytes) -> None:
        ...


class BackupRepositoryLike(Protocol):
    async def create_metadata(self, record: BackupMetadataModel) -> Any:
        ...

    async def update_metadata(self, backup_id: str, **fields: object) -> Any | None:
        ...


class BackupPolicyServiceLike(Protocol):
    def evaluate_backup(
        self,
        principal: ApiKeyPrincipal | None,
        classification: ClassificationLevel,
    ) -> Any:
        ...


class BackupAuditServiceLike(Protocol):
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
        ...

    async def record_backup_event(
        self,
        action: str,
        backup_id: str,
        actor_key_id: str | None,
        actor_role: str | None,
        status: str,
        reason: str | None,
    ) -> None:
        ...


class BackupSettingsLike(Protocol):
    classification_required: bool
    default_classification: str
    minio_bucket: str


class BackupService:
    def __init__(
        self,
        repository: BackupRepositoryLike,
        settings: BackupSettingsLike,
        policy_service: BackupPolicyServiceLike,
        audit_service: BackupAuditServiceLike,
        key_store: KeyStore,
        storage: ObjectStorage,
        key_management_service: object | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._policy_service = policy_service
        self._audit_service = audit_service
        self._key_store = key_store
        self._storage = storage
        self._key_management_service = key_management_service

    async def _mark_failed(
        self,
        backup_id: str,
        principal: ApiKeyPrincipal | None,
        reason: str,
    ) -> None:
        await self._repository.update_metadata(
            backup_id,
            status=BackupStatus.FAILED.value,
        )
        await self._audit_service.record_backup_event(
            action='backup_processing_failed',
            backup_id=backup_id,
            actor_key_id=principal.key_id if principal else None,
            actor_role=principal.role if principal else None,
            status=BackupStatus.FAILED.value,
            reason=reason,
        )

    def _normalize_classification(self, request: BackupRequest) -> ClassificationLevel:
        if request.classification is None:
            if self._settings.classification_required:
                raise BackupValidationError(
                    message='Request validation failed',
                    details=[
                        {
                            'loc': ['body', 'classification'],
                            'msg': 'Field required',
                            'type': 'missing',
                        },
                    ],
                )
            default_value = self._settings.default_classification
            try:
                return ClassificationLevel(default_value)
            except ValueError as exc:
                raise BackupValidationError(
                    message='Invalid default classification configuration',
                    details=[
                        {
                            'loc': ['config', 'default_classification'],
                            'msg': f'Invalid classification: {default_value}',
                            'type': 'value_error',
                        },
                    ],
                ) from exc
        return request.classification

    async def submit_backup(
        self,
        request: BackupRequest,
        principal: ApiKeyPrincipal | None,
        client_ip: str | None,
    ) -> dict[str, object]:
        classification = self._normalize_classification(request)
        backup_id = uuid4().hex
        decision = self._policy_service.evaluate_backup(principal, classification)
        await self._audit_service.record_policy_decision(
            key_id=principal.key_id if principal else None,
            operation='backup_submit',
            allowed=decision.allowed,
            reason=decision.reason,
            reason_category=decision.reason_category,
            classification=classification.value,
            client_ip=client_ip,
        )
        if not decision.allowed:
            await self._audit_service.record_backup_event(
                action='backup_processing_denied',
                backup_id=backup_id,
                actor_key_id=principal.key_id if principal else None,
                actor_role=principal.role if principal else None,
                status='DENIED',
                reason=decision.reason_category,
            )
            raise BackupPolicyDenied(decision.reason, decision.reason_category)
        plaintext = (request.payload or '').encode()
        checksum_plaintext = sha512(plaintext).hexdigest()
        record = BackupMetadataModel(
            backup_id=backup_id,
            key_version=None,
            classification=classification.value,
            source_system=request.source_system,
            description=request.description,
            status=BackupStatus.PROCESSING.value,
            checksum_plaintext=checksum_plaintext,
            original_size=len(plaintext),
            created_by=principal.key_id if principal else None,
        )
        await self._repository.create_metadata(record)
        await self._audit_service.record_backup_event(
            action='backup_processing_started',
            backup_id=backup_id,
            actor_key_id=principal.key_id if principal else None,
            actor_role=principal.role if principal else None,
            status=BackupStatus.PROCESSING.value,
            reason=None,
        )
        try:
            if self._key_management_service is not None and hasattr(
                self._key_management_service,
                'get_active_key_material',
            ):
                key_material = await self._key_management_service.get_active_key_material()
            else:
                key_material = self._key_store.get_active_key()
        except Exception as exc:
            await self._mark_failed(backup_id, principal, 'key_unavailable')
            raise BackupProcessingError('UPLOAD_FAILED', 'Backup encryption failed') from exc
        await self._repository.update_metadata(
            backup_id,
            key_version=key_material.version_id,
        )
        try:
            encryption = encrypt(plaintext, key_material.key_bytes)
        except Exception as exc:
            await self._mark_failed(backup_id, principal, 'encryption_failed')
            raise BackupProcessingError('UPLOAD_FAILED', 'Backup encryption failed') from exc
        object_name = f'{backup_id}.bin'
        ciphertext_blob = encryption.nonce + encryption.tag + encryption.ciphertext
        try:
            await self._storage.put_object(
                self._settings.minio_bucket,
                object_name,
                ciphertext_blob,
            )
        except ObjectStorageError as exc:
            await self._mark_failed(backup_id, principal, 'storage_failed')
            raise BackupProcessingError('UPLOAD_FAILED', exc.message) from exc
        except Exception as exc:
            await self._mark_failed(backup_id, principal, 'storage_failed')
            raise BackupProcessingError('UPLOAD_FAILED', 'Backup upload failed') from exc
        checksum_ciphertext = sha512(ciphertext_blob).hexdigest()
        updated_record = await self._repository.update_metadata(
            backup_id,
            status=BackupStatus.ACTIVE.value,
            storage_path=object_name,
            checksum_ciphertext=checksum_ciphertext,
            nonce=encryption.nonce.hex(),
            encrypted_size=len(ciphertext_blob),
            key_version=key_material.version_id,
        )
        await self._audit_service.record_backup_event(
            action='backup_processing_succeeded',
            backup_id=backup_id,
            actor_key_id=principal.key_id if principal else None,
            actor_role=principal.role if principal else None,
            status=BackupStatus.ACTIVE.value,
            reason=None,
        )
        return {
            'status': 'accepted',
            'backup_id': updated_record.backup_id if updated_record else backup_id,
            'classification': (
                updated_record.classification if updated_record else classification.value
            ),
            'source_system': (
                updated_record.source_system if updated_record else request.source_system
            ),
        }
