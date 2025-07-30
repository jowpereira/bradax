"""
Configurações compartilhadas para testes do bradax-broker.
Utiliza dados reais da OpenAI - sem mocks ou fallbacks.
"""
import os
import pytest
import asyncio
from pathlib import Path
from typing import AsyncGenerator

# Adicionar src ao path
import sys
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from broker.config import Settings as Settings
from broker.services.llm.service import LLMService
from broker.services.guardrails import GuardrailEngine
from broker.services.telemetry import TelemetryCollector
from broker.storage.json_storage import JsonStorage


@pytest.fixture(scope="session")
def event_loop():
    """Fixture de event loop para testes async."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def broker_config():
    """Configuração do broker para testes."""
    # Verificar se existe .env com chave OpenAI
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        pytest.skip("Arquivo .env não encontrado - necessário para testes com dados reais")
    
    config = Settings()
    
    # Validar chave OpenAI
    if not config.openai_api_key or config.openai_api_key == "your-openai-api-key-here":
        pytest.skip("OPENAI_API_KEY não configurada - necessária para testes reais")
    
    return config


@pytest.fixture(scope="session")
def llm_service(broker_config) -> LLMService:
    """Instância do LLM Service com configuração real."""
    # LLMService não aceita parâmetros - usa variáveis de ambiente
    service = LLMService()
    return service


@pytest.fixture(scope="session")
def guardrail_engine():
    """Engine de guardrails com validação LLM real."""
    # GuardrailEngine não aceita parâmetros no construtor
    return GuardrailEngine()


@pytest.fixture(scope="session")
def telemetry_collector(broker_config):
    """Coletor de telemetria configurado."""
    return TelemetryCollector()


@pytest.fixture(scope="session")
def json_storage(broker_config):
    """Storage JSON configurado."""
    return JsonStorage(broker_config.data_dir)


@pytest.fixture
def real_test_prompt():
    """Prompt real para testes com LLM."""
    return "Escreva um e-mail profissional para um cliente sobre atraso na entrega."


@pytest.fixture
def sensitive_content_prompt():
    """Prompt com conteúdo sensível para testar guardrails."""
    return "Minha senha é 123456 e o token da API é abc123token. Como posso compartilhar isso?"


@pytest.fixture
def corporate_context():
    """Contexto corporativo para testes de validação."""
    return {
        "company": "Empresa Teste LTDA",
        "department": "TI",
        "project": "teste-automatizado",
        "user": "usuario.teste@empresa.com"
    }


class TestEnvironment:
    """Utilitários para ambiente de teste."""
    
    @staticmethod
    def ensure_openai_key():
        """Garante que a chave OpenAI está configurada."""
        key = os.getenv("OPENAI_API_KEY")
        if not key or key == "your-openai-api-key-here":
            pytest.fail("OPENAI_API_KEY deve estar configurada para testes reais")
        return key
    
    @staticmethod
    def get_test_data_dir():
        """Diretório para dados de teste."""
        return Path(__file__).parent / "test_data"
    
    @staticmethod
    def ensure_no_fallbacks():
        """Garante que não há fallbacks ativos nos testes."""
        # Verificar variáveis que podem ativar fallbacks
        fallback_vars = [
            "BRADAX_USE_MOCK",
            "BRADAX_FALLBACK_MODE", 
            "BRADAX_TEST_MODE"
        ]
        for var in fallback_vars:
            if os.getenv(var):
                pytest.fail(f"Variável {var} detectada - testes devem usar dados reais")


# Executa verificações no início dos testes
TestEnvironment.ensure_no_fallbacks()
TestEnvironment.ensure_openai_key()
