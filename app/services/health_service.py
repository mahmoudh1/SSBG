from __future__ import annotations

from app.core.config import get_settings
from app.infrastructure.db.session import check_database_ready
from app.infrastructure.storage.minio_client import check_minio_ready


async def get_liveness_status() -> dict[str, object]:
    return {'status': 'ok'}


async def get_readiness_status() -> dict[str, object]:
    settings = get_settings()
    postgres_ready = await check_database_ready()
    minio_ready = await check_minio_ready(settings.minio_endpoint)

    dependencies = {
        'postgres': {'status': 'ok' if postgres_ready else 'unavailable'},
        'minio': {'status': 'ok' if minio_ready else 'unavailable'},
    }
    ready = postgres_ready and minio_ready
    return {
        'status': 'ready' if ready else 'not_ready',
        'dependencies': dependencies,
    }
