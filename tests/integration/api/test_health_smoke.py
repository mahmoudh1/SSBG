import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.api.routes import health as health_routes
from app.core.config import get_settings
from app.main import create_app
from app.services import health_service


def test_create_app_registers_api_v1_routes() -> None:
    app = create_app()
    paths = {route.path for route in app.routes if isinstance(route, APIRoute)}

    assert '/api/v1/health/live' in paths
    assert '/api/v1/health/ready' in paths
    assert '/api/v1/backups' in paths


def test_health_liveness_endpoint_returns_ok(client: TestClient) -> None:
    response = client.get('/api/v1/health/live')

    assert response.status_code == 200
    assert response.json() == {
        'data': {'status': 'ok'},
        'meta': {'request_id': 'generated-placeholder-id'},
    }


def test_health_readiness_reports_ready(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _db_ready() -> bool:
        return True

    async def _minio_ready(_: str) -> bool:
        return True

    monkeypatch.setattr(health_service, 'check_database_ready', _db_ready)
    monkeypatch.setattr(health_service, 'check_minio_ready', _minio_ready)

    response = client.get('/api/v1/health/ready')

    assert response.status_code == 200
    assert response.json() == {
        'data': {
            'status': 'ready',
            'dependencies': {
                'postgres': {'status': 'ok'},
                'minio': {'status': 'ok'},
            },
        },
        'meta': {'request_id': 'generated-placeholder-id'},
    }


def test_health_readiness_reports_not_ready(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _db_ready() -> bool:
        return False

    async def _minio_ready(_: str) -> bool:
        return True

    monkeypatch.setattr(health_service, 'check_database_ready', _db_ready)
    monkeypatch.setattr(health_service, 'check_minio_ready', _minio_ready)

    response = client.get('/api/v1/health/ready')

    assert response.status_code == 200
    assert response.json() == {
        'data': {
            'status': 'not_ready',
            'dependencies': {
                'postgres': {'status': 'unavailable'},
                'minio': {'status': 'ok'},
            },
        },
        'meta': {'request_id': 'generated-placeholder-id'},
    }


def test_health_readiness_reports_minio_not_ready(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _db_ready() -> bool:
        return True

    async def _minio_ready(_: str) -> bool:
        return False

    monkeypatch.setattr(health_service, 'check_database_ready', _db_ready)
    monkeypatch.setattr(health_service, 'check_minio_ready', _minio_ready)

    response = client.get('/api/v1/health/ready')

    assert response.status_code == 200
    assert response.json() == {
        'data': {
            'status': 'not_ready',
            'dependencies': {
                'postgres': {'status': 'ok'},
                'minio': {'status': 'unavailable'},
            },
        },
        'meta': {'request_id': 'generated-placeholder-id'},
    }


def test_health_unexpected_error_uses_shared_error_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _boom() -> dict[str, object]:
        raise RuntimeError('boom')

    monkeypatch.setattr(health_routes, 'get_readiness_status', _boom)
    monkeypatch.setenv('APP_DEBUG', 'false')
    get_settings.cache_clear()
    client = TestClient(create_app(), raise_server_exceptions=False)

    response = client.get('/api/v1/health/ready')

    assert response.status_code == 500
    assert response.json() == {
        'error': {'code': 'internal_server_error', 'message': 'Internal server error'},
        'data': None,
        'meta': None,
    }
    get_settings.cache_clear()
