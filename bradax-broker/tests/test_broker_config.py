import importlib
from broker.constants import HubLLMConstants
from broker import config as cfg


def test_settings_defaults(monkeypatch):
    monkeypatch.setenv('BRADAX_ENV', 'development')
    importlib.reload(cfg)
    settings = cfg.Settings()
    assert settings.debug is True
    assert settings.environment.value == 'development'


def test_get_model_configuration():
    cfg_obj = cfg.get_model_configuration(HubLLMConstants.DEFAULT_MODEL)
    assert 'max_tokens' in cfg_obj


def test_environment_helpers(monkeypatch):
    monkeypatch.setenv('BRADAX_ENV', 'production')
    importlib.reload(cfg)
    assert cfg.is_production() is True
    assert cfg.is_development() is False
