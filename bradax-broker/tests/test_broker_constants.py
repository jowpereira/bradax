import importlib
from broker.constants import (
    get_hub_environment, BradaxEnvironment,
    get_cors_origins, get_default_budget,
    validate_model, get_model_limits,
    HubNetworkConstants, HubBudgetConstants, HubLLMConstants
)


def test_get_hub_environment_default(monkeypatch):
    monkeypatch.delenv('BRADAX_ENV', raising=False)
    assert get_hub_environment() == BradaxEnvironment.DEVELOPMENT


def test_get_hub_environment_override(monkeypatch):
    monkeypatch.setenv('BRADAX_ENV', 'production')
    assert get_hub_environment() == BradaxEnvironment.PRODUCTION


def test_get_cors_origins(monkeypatch):
    monkeypatch.setenv('BRADAX_ENV', 'production')
    importlib.reload(importlib.import_module('broker.constants'))
    from broker.constants import get_cors_origins as fresh_get_cors
    assert fresh_get_cors() == HubNetworkConstants.CORS_ORIGINS_PROD


def test_get_default_budget(monkeypatch):
    monkeypatch.setenv('BRADAX_ENV', 'staging')
    importlib.reload(importlib.import_module('broker.constants'))
    from broker.constants import get_default_budget as fresh_budget
    assert fresh_budget() == HubBudgetConstants.DEFAULT_BUDGET_STAGING


def test_validate_model_and_limits():
    assert validate_model(HubLLMConstants.DEFAULT_MODEL)
    limits = get_model_limits('unknown')
    assert 'max_tokens' in limits
