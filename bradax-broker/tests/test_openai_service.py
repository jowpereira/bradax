import types
import sys
import pytest


class DummyResponse:
    def __init__(self):
        self.choices = [types.SimpleNamespace(message=types.SimpleNamespace(content='ok'), finish_reason='stop')]
        self.usage = types.SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2)


class DummyChat:
    async def create(self, **kwargs):
        return DummyResponse()


class DummyAsyncOpenAI:
    def __init__(self, *args, **kwargs):
        self.chat = types.SimpleNamespace(completions=DummyChat())


sys.modules['openai'] = types.SimpleNamespace(AsyncOpenAI=DummyAsyncOpenAI)
from broker.services import openai_service


def patch_client(monkeypatch):
    monkeypatch.setattr(openai_service, 'AsyncOpenAI', DummyAsyncOpenAI)


@pytest.mark.asyncio
async def test_invoke_llm(monkeypatch):
    patch_client(monkeypatch)
    service = openai_service.OpenAIService(api_key='key')
    result = await service.invoke_llm('gpt-4o-mini', [{'role': 'user', 'content': 'hi'}])
    assert result['model'] == 'gpt-4o-mini'
    assert result['usage']['total_tokens'] == 2


@pytest.mark.asyncio
async def test_validate_api_key(monkeypatch):
    patch_client(monkeypatch)
    service = openai_service.OpenAIService(api_key='key')
    valid = await service.validate_api_key()
    assert valid is True
