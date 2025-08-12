import pytest
from bradax.client import BradaxClient
from bradax.exceptions.bradax_exceptions import BradaxConfigurationError, BradaxAuthenticationError

class DummyResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data or {"success": True, "response_text": "ok", "usage": {}, "request_id": "r1"}
    def json(self):
        return self._json
    @property
    def text(self):
        return str(self._json)

class DummyClient:
    def __init__(self):
        self.last_url = None
        self.last_json = None
        self.last_headers = None
    def post(self, url, json=None, headers=None):
        self.last_url = url
        self.last_json = json
        self.last_headers = headers
        return DummyResponse()
    def get(self, url, timeout=None):
        return DummyResponse(json_data={"success": True, "data": {"project_id": "projeto-001"}})
    def close(self):
        pass

@pytest.fixture
def patched_client(monkeypatch):
    c = BradaxClient(project_token="token-real", broker_url="http://localhost:8000")
    monkeypatch.setattr(c, 'client', DummyClient())
    return c

def test_invoke_success(patched_client):
    result = patched_client.invoke("hello", model="gpt-x")
    assert result["content"] == "ok"
    assert patched_client.client.last_json["payload"]["messages"][0]["content"] == "hello"

import pytest_asyncio  # ensure plugin loaded

@pytest.mark.asyncio
@pytest.mark.parametrize("method_name", ["ainvoke"])  # future additions possible
async def test_ainvoke_blocked(patched_client, method_name):
    with pytest.raises(BradaxConfigurationError):
        await getattr(patched_client, method_name)("test")

def test_interceptor_direct_blocked():
    from bradax.telemetry_interceptor import initialize_global_telemetry, get_telemetry_interceptor
    initialize_global_telemetry("http://localhost:8000", "projeto-001")
    interceptor = get_telemetry_interceptor()
    with pytest.raises(BradaxConfigurationError):
        interceptor.chat_completion()
    with pytest.raises(BradaxConfigurationError):
        interceptor.completion()
    with pytest.raises(BradaxConfigurationError):
        interceptor.intercept_llm_request()

def test_missing_token_error(monkeypatch):
    monkeypatch.delenv("BRADAX_PROJECT_TOKEN", raising=False)
    with pytest.raises(BradaxConfigurationError):
        BradaxClient(project_token=None, broker_url="http://localhost:8000")

def test_placeholder_token_error(monkeypatch):
    with pytest.raises(BradaxAuthenticationError):
        BradaxClient(project_token="test-project-token", broker_url="http://localhost:8000")
