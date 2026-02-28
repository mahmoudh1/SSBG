from __future__ import annotations

import asyncio
import json

from app.infrastructure.db.session import get_session_factory
from app.repositories.audit_repository import AuditRepository
from app.services.audit_service import AuditService


async def _run() -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        repository = AuditRepository(session)
        service = AuditService(repository)
        result = await service.validate_chain()
    print(json.dumps(result.model_dump(mode='json'), indent=2))
    return 0 if result.valid else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(_run()))
