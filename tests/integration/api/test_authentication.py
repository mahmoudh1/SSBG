from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.dependencies import get_auth_service
from app.main import create_app
from app.schemas.auth import ApiKeyPrincipal
from app.services.auth_service import AuthFailure


def test_missing_api_key_returns_auth_error() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post(
        '/api/v1/backups',
        json={'classification': 'PUBLIC', 'source_system': 'system-a'},
    )

    assert response.status_code == 401
    assert response.json() == {
        'error': {'code': 'AUTH_INVALID_KEY', 'message': 'Missing API key'},
        'data': None,
        'meta': {'request_id': 'generated-placeholder-id'},
    }


def test_invalid_api_key_returns_auth_error() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            raise AuthFailure('AUTH_INVALID_KEY', 'Invalid API key')

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    client = TestClient(app)

    response = client.post(
        '/api/v1/backups',
        json={'classification': 'PUBLIC', 'source_system': 'system-a'},
        headers={'X-API-Key': 'invalid'},
    )

    assert response.status_code == 401
    assert response.json() == {
        'error': {'code': 'AUTH_INVALID_KEY', 'message': 'Invalid API key'},
        'data': None,
        'meta': {'request_id': 'generated-placeholder-id'},
    }


def test_valid_api_key_allows_request() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            return ApiKeyPrincipal(key_id='key-1', role='operator', department='IT')

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    client = TestClient(app)

    response = client.post(
        '/api/v1/backups',
        json={'classification': 'PUBLIC', 'source_system': 'system-a'},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 200
    assert response.json() == {
        'data': {
            'status': 'accepted',
            'classification': 'PUBLIC',
            'source_system': 'system-a',
        },
        'meta': {'request_id': 'generated-placeholder-id'},
    }


def test_auth_dependency_failure_denies_request_fail_secure() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            raise RuntimeError('db unavailable')

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    client = TestClient(app)

    response = client.post(
        '/api/v1/backups',
        json={'classification': 'PUBLIC', 'source_system': 'system-a'},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 401
    assert response.json() == {
        'error': {'code': 'AUTH_UNAVAILABLE', 'message': 'Authentication service unavailable'},
        'data': None,
        'meta': {'request_id': 'generated-placeholder-id'},
    }
