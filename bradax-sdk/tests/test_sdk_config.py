import os
import pytest
import importlib.util
import sys
from types import ModuleType
from pathlib import Path

root = Path(__file__).resolve().parents[1] / 'src' / 'bradax'

# Create package placeholders with proper __path__ for relative imports
pkg = ModuleType('bradax')
pkg.__path__ = [str(root)]
sys.modules['bradax'] = pkg
cfg_pkg = ModuleType('bradax.config')
cfg_pkg.__path__ = [str(root / 'config')]
sys.modules['bradax.config'] = cfg_pkg

# Load dependencies
const_spec = importlib.util.spec_from_file_location('bradax.constants', root / 'constants.py')
constants = importlib.util.module_from_spec(const_spec)
sys.modules['bradax.constants'] = constants
const_spec.loader.exec_module(constants)

spec = importlib.util.spec_from_file_location('bradax.config.sdk_config', root / 'config' / 'sdk_config.py')
sdk_config = importlib.util.module_from_spec(spec)
sys.modules['bradax.config.sdk_config'] = sdk_config
spec.loader.exec_module(sdk_config)

BradaxSDKConfig = sdk_config.BradaxSDKConfig
ProjectConfig = sdk_config.ProjectConfig
create_sdk_config = sdk_config.create_sdk_config
create_project_config = sdk_config.create_project_config
SDKModelConstants = sdk_config.SDKModelConstants
BradaxEnvironment = sdk_config.BradaxEnvironment


def test_create_sdk_config_uses_env(monkeypatch):
    monkeypatch.setenv('BRADAX_ENV', 'testing')
    config = create_sdk_config()
    assert config.environment == BradaxEnvironment.TESTING
    assert config.hub_url


def test_project_config_validation_errors():
    with pytest.raises(ValueError):
        ProjectConfig(project_id='bad', api_key='also_bad')


def test_create_project_config_defaults():
    cfg = create_project_config(project_id='proj_test_123', api_key='bradax_x'*16)
    assert cfg.name.startswith('Project')
    assert cfg.default_model == SDKModelConstants.DEFAULT_MODEL
