from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from functools import lru_cache

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.infrastructure.crypto.key_store_fs import FileSystemKeyStore
from app.infrastructure.db.session import get_db_session
from app.infrastructure.storage.minio_client import InMemoryObjectStorage
from app.repositories.api_keys_repository import ApiKeysRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.backups_repository import BackupsRepository
from app.repositories.policies_repository import PoliciesRepository
from app.schemas.auth import ApiKeyPrincipal
from app.services.audit_service import AuditService
from app.services.auth_service import AuthFailure, AuthService
from app.services.backup_service import BackupService
from app.services.policy_service import PolicyService

logger = logging.getLogger(__name__)


def get_app_settings() -> Settings:
    return get_settings()


def get_request_id(request: Request) -> str:
    return request.headers.get('x-request-id', 'generated-placeholder-id')


def _auth_error_payload(code: str, message: str, request_id: str) -> dict[str, object]:
    return {
        'error': {'code': code, 'message': message},
        'data': None,
        'meta': {'request_id': request_id},
    }


def get_api_keys_repository(db: AsyncSession = Depends(get_db_session)) -> ApiKeysRepository:
    return ApiKeysRepository(db)


def get_policies_repository(db: AsyncSession = Depends(get_db_session)) -> PoliciesRepository:
    return PoliciesRepository(db)


def get_backups_repository(db: AsyncSession = Depends(get_db_session)) -> BackupsRepository:
    return BackupsRepository(db)


def get_audit_repository(db: AsyncSession = Depends(get_db_session)) -> AuditRepository:
    return AuditRepository(db)


def get_audit_service(
    repository: AuditRepository = Depends(get_audit_repository),
) -> AuditService:
    return AuditService(repository)


def get_key_store(settings: Settings = Depends(get_app_settings)) -> FileSystemKeyStore:
    return FileSystemKeyStore(key_store_path=settings.key_store_path)


@lru_cache(maxsize=1)
def get_storage_client() -> InMemoryObjectStorage:
    return InMemoryObjectStorage()


def get_auth_service(
    repository: ApiKeysRepository = Depends(get_api_keys_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> AuthService:
    return AuthService(repository, audit_service)


def get_policy_service() -> PolicyService:
    return PolicyService()


def get_backup_service(
    repository: BackupsRepository = Depends(get_backups_repository),
    settings: Settings = Depends(get_app_settings),
    policy_service: PolicyService = Depends(get_policy_service),
    audit_service: AuditService = Depends(get_audit_service),
    key_store: FileSystemKeyStore = Depends(get_key_store),
    storage: InMemoryObjectStorage = Depends(get_storage_client),
) -> BackupService:
    return BackupService(repository, settings, policy_service, audit_service, key_store, storage)


async def require_api_key(
    request: Request,
    request_id: str = Depends(get_request_id),
    settings: Settings = Depends(get_app_settings),
    auth_service: AuthService = Depends(get_auth_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> ApiKeyPrincipal:
    api_key = request.headers.get(settings.api_key_header)
    try:
        client_ip = request.client.host if request.client else None
        principal = await auth_service.authenticate(api_key or '', client_ip)
    except AuthFailure as exc:
        raise HTTPException(
            status_code=401,
            detail=_auth_error_payload(code=exc.code, message=exc.message, request_id=request_id),
        ) from exc
    except Exception as exc:
        logger.exception('Authentication dependency failure', exc_info=exc)
        try:
            await audit_service.record_auth_failure(
                key_prefix=(api_key or '')[:8],
                reason='auth_dependency_failure',
                client_ip=request.client.host if request.client else None,
            )
        except Exception:
            logger.exception('Failed to record auth dependency failure audit event')
        raise HTTPException(
            status_code=401,
            detail=_auth_error_payload(
                code='AUTH_UNAVAILABLE',
                message='Authentication service unavailable',
                request_id=request_id,
            ),
        ) from exc
    request.state.principal = principal
    return principal


def require_permission(permission: str) -> Callable[..., Awaitable[ApiKeyPrincipal]]:
    async def _require_permission(
        request: Request,
        request_id: str = Depends(get_request_id),
        principal: ApiKeyPrincipal = Depends(require_api_key),
        policy_service: PolicyService = Depends(get_policy_service),
        audit_service: AuditService = Depends(get_audit_service),
    ) -> ApiKeyPrincipal:
        decision = policy_service.authorize(principal, permission)
        if not decision.allowed:
            client_ip = request.client.host if request.client else None
            await audit_service.record_authorization_denied(
                key_id=principal.key_id if principal else None,
                role=decision.role,
                permission=decision.required_permission,
                reason=decision.reason,
                client_ip=client_ip,
            )
            raise HTTPException(
                status_code=403,
                detail=_auth_error_payload(
                    code='POLICY_DENIED',
                    message='Not authorized for this operation',
                    request_id=request_id,
                ),
            )
        return principal

    return _require_permission
