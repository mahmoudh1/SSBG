from __future__ import annotations

from app.core.enums import ClassificationLevel
from app.schemas.auth import ApiKeyPrincipal
from app.services.policy_service import PolicyService


def test_backup_policy_allows_default_roles() -> None:
    service = PolicyService()
    principal = ApiKeyPrincipal(key_id='key-1', role='operator', department='IT')

    decision = service.evaluate_backup(principal, ClassificationLevel.SECRET)

    assert decision.allowed is True
    assert decision.reason_category == 'allowed'


def test_backup_policy_denies_restricted_role() -> None:
    service = PolicyService(
        backup_classification_roles={ClassificationLevel.SECRET: {'super_admin'}},
    )
    principal = ApiKeyPrincipal(key_id='key-1', role='operator', department='IT')

    decision = service.evaluate_backup(principal, ClassificationLevel.SECRET)

    assert decision.allowed is False
    assert decision.reason_category == 'role_restricted'


def test_backup_policy_denies_missing_principal() -> None:
    service = PolicyService()

    decision = service.evaluate_backup(None, ClassificationLevel.PUBLIC)

    assert decision.allowed is False
    assert decision.reason_category == 'missing_principal'
