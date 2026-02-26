from __future__ import annotations

from app.schemas.auth import ApiKeyPrincipal
from app.services.policy_service import PolicyService


def test_policy_service_allows_admin_permissions() -> None:
    service = PolicyService()
    principal = ApiKeyPrincipal(key_id='key-1', role='admin', department='IT')

    decision = service.authorize(principal, 'admin')

    assert decision.allowed is True


def test_policy_service_denies_operator_admin_access() -> None:
    service = PolicyService()
    principal = ApiKeyPrincipal(key_id='key-1', role='operator', department='IT')

    decision = service.authorize(principal, 'admin')

    assert decision.allowed is False
