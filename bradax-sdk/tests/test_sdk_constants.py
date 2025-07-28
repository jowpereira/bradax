import importlib.util
import sys
from types import ModuleType
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / 'src' / 'bradax' / 'constants.py'

sys.modules.setdefault('bradax', ModuleType('bradax'))

spec = importlib.util.spec_from_file_location('bradax.constants', module_path)
constants = importlib.util.module_from_spec(spec)
sys.modules['bradax.constants'] = constants
spec.loader.exec_module(constants)

get_sdk_environment = constants.get_sdk_environment
BradaxEnvironment = constants.BradaxEnvironment
get_hub_url = constants.get_hub_url
validate_project_id = constants.validate_project_id
validate_api_key = constants.validate_api_key
SDKNetworkConstants = constants.SDKNetworkConstants
SDKSecurityConstants = constants.SDKSecurityConstants
SDKValidationConstants = constants.SDKValidationConstants


def test_get_sdk_environment_default(monkeypatch):
    monkeypatch.delenv('BRADAX_ENV', raising=False)
    assert get_sdk_environment() == BradaxEnvironment.DEVELOPMENT


def test_get_sdk_environment_override(monkeypatch):
    monkeypatch.setenv('BRADAX_ENV', 'staging')
    assert get_sdk_environment() == BradaxEnvironment.STAGING


def test_get_hub_url_for_env(monkeypatch):
    monkeypatch.setenv('BRADAX_ENV', 'production')
    importlib.reload(constants)
    assert get_hub_url() == SDKNetworkConstants.PRODUCTION_HUB_URL


def test_validate_project_id():
    valid = f"{SDKValidationConstants.PROJECT_ID_PREFIX}abc12345"
    assert validate_project_id(valid)
    assert not validate_project_id('invalid')


def test_validate_api_key():
    valid = f"{SDKSecurityConstants.API_KEY_PREFIX}" + 'a'*32
    assert validate_api_key(valid)
    assert not validate_api_key('bad')
