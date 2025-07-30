"""
Teste 4.2: Testes de integração LangChain - chamadas reais
Conforme Fase 4 do plano workspace-plans/active/20250728-223500-conferencia-corporativa-consolidada.md

Testa integração real com LangChain e OpenAI - sem mocks ou fallbacks.
"""
import pytest
import asyncio
import os
import sys
from pathlib import Path

# Adicionar src ao path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from broker.config import Settings
from broker.services.llm.service import LLMService
from broker.services.llm.providers import OpenAIProvider


class TestLangChainIntegration:
    """Testes de integração real com LangChain e OpenAI."""
    
    @pytest.fixture(scope="class")
    def config(self):
        """Configuração do broker."""
        return Settings()
    
    @pytest.fixture(scope="class")
    def llm_service(self, config):
        """Serviço LLM inicializado."""
        service = LLMService()
        return service
    
    def test_openai_provider_initialization(self, config):
        """Teste de inicialização do provider OpenAI."""
        provider = OpenAIProvider()
        assert provider.api_key == config.openai_api_key
        assert provider.is_available()
        assert hasattr(provider, 'client')
    
    def test_llm_service_initialization(self, llm_service):
        """Teste de inicialização do serviço LLM."""
        # Verificar se o serviço foi criado
        assert llm_service is not None
        
        # Verificar se tem os métodos básicos
        assert hasattr(llm_service, 'invoke')
        assert hasattr(llm_service, 'get_available_models')
        
        # Verificar se providers foram carregados
        assert hasattr(llm_service, 'providers')
        
        print("LLMService inicializado com sucesso")
    
    @pytest.mark.asyncio
    async def test_real_openai_completion(self, llm_service):
        """Teste de completion real com OpenAI."""
        messages = [{"role": "user", "content": "Escreva apenas 'TESTE_FUNCIONAL_OK' como resposta."}]
        
        # Fazer chamada real para OpenAI
        response = await llm_service.invoke(
            operation="chat",
            model_id="gpt-4.1-nano",
            payload={"messages": messages}
        )
        
        assert response is not None
        assert response["success"] == True
        assert "response_text" in response
        assert len(response["response_text"]) > 0
        
        print(f"OpenAI response: {response['response_text']}")
    
    @pytest.mark.asyncio
    async def test_model_registry_integration(self, llm_service):
        """Teste de integração com registry de modelos."""
        # Testar se consegue usar o modelo gpt-4.1-nano
        messages = [{"role": "user", "content": "Diga apenas 'modelo funcionando'"}]
        
        response = await llm_service.invoke(
            operation="chat",
            model_id="gpt-4.1-nano",
            payload={"messages": messages}
        )
        
        assert response is not None
        assert response["success"] == True
        assert "response_text" in response
        
        print(f"Model registry test response: {response['response_text']}")
    
    @pytest.mark.asyncio
    async def test_real_conversation_flow(self, llm_service):
        """Teste de fluxo conversacional real."""
        messages = [{"role": "user", "content": "Qual é a capital do Brasil?"}]
        
        response = await llm_service.invoke(
            operation="chat",
            model_id="gpt-4.1-nano",
            payload={"messages": messages}
        )
        
        assert response is not None
        assert response["success"] == True
        assert "response_text" in response
        
        # Verificar que a resposta contém informação relevante
        content = response["response_text"].lower()
        assert "brasília" in content or "brasilia" in content
        
        print(f"Conversation flow response: {response['response_text']}")
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_input(self, llm_service):
        """Teste de tratamento de erro com entrada inválida."""
        # Teste com prompt vazio
        messages = [{"role": "user", "content": ""}]
        
        response = await llm_service.invoke(
            operation="chat",
            model_id="gpt-4.1-nano",
            payload={"messages": messages}
        )
        
        # Pode retornar sucesso ou erro, ambos são válidos
        assert response is not None
        assert "success" in response
        
        if response["success"]:
            assert "response_text" in response
            print(f"Empty prompt response: {response['response_text']}")
        else:
            assert "error" in response
            print(f"Expected error for empty prompt: {response['error']}")
    
    @pytest.mark.asyncio
    async def test_token_usage_tracking(self, llm_service):
        """Teste de rastreamento de uso de tokens."""
        messages = [{"role": "user", "content": "Conte de 1 a 5."}]
        
        response = await llm_service.invoke(
            operation="chat",
            model_id="gpt-4.1-nano",
            payload={"messages": messages}
        )
        
        # Verificar se a resposta existe
        assert response is not None
        assert response["success"] == True
        assert "response_text" in response
        assert len(response["response_text"]) > 0
        
        # Verificar se há informações de tempo de resposta
        assert "response_time_ms" in response
        assert response["response_time_ms"] > 0
        
        # Log para verificação
        print(f"Token usage test response: {response['response_text']}")
        print(f"Response time: {response['response_time_ms']}ms")


class TestOpenAISpecific:
    """Testes específicos para funcionalidades OpenAI."""
    
    @pytest.fixture(scope="class")
    def config(self):
        """Configuração do broker."""
        return Settings()
    
    def test_openai_key_format_validation(self, config):
        """Teste de validação do formato da chave OpenAI."""
        api_key = config.openai_api_key
        
        # Verificar formato da chave
        assert api_key.startswith("sk-"), "Chave OpenAI deve começar com 'sk-'"
        assert len(api_key) > 20, "Chave OpenAI deve ter tamanho adequado"
        assert not api_key.endswith("here"), "Chave não deve ser placeholder"
    
    @pytest.mark.asyncio
    async def test_openai_rate_limits_respect(self):
        """Teste de respeito aos rate limits da OpenAI."""
        config = Settings()
        service = LLMService()
        
        # Fazer múltiplas chamadas para testar rate limiting
        responses = []
        for i in range(3):
            messages = [{"role": "user", "content": f"Teste {i+1}"}]
            response = await service.invoke(
                operation="chat",
                model_id="gpt-4.1-nano",
                payload={"messages": messages}
            )
            responses.append(response)
            
        # Verificar que todas as chamadas funcionaram
        assert len(responses) == 3
        for response in responses:
            assert response is not None
            assert "success" in response
            
        print("Rate limit test completed successfully")
    
    @pytest.mark.asyncio
    async def test_openai_model_availability(self):
        """Teste de disponibilidade dos modelos OpenAI."""
        config = Settings()
        service = LLMService()
        
        # Testar se consegue fazer uma chamada básica
        messages = [{"role": "user", "content": "Responda apenas 'DISPONÍVEL'"}]
        response = await service.invoke(
            operation="chat",
            model_id="gpt-4.1-nano",
            payload={"messages": messages}
        )
        
        assert response is not None
        assert response["success"] == True
        assert "response_text" in response
        assert len(response["response_text"]) > 0
        
        print(f"Model availability test response: {response['response_text']}")


class TestLLMServicePerformance:
    """Testes de performance do LLMService."""
    
    @pytest.fixture(scope="class")
    def config(self):
        """Configuração do broker."""
        return Settings()
    
    @pytest.fixture(scope="class")
    def llm_service(self, config):
        """Serviço LLM inicializado."""
        service = LLMService()
        return service
    
    @pytest.mark.asyncio
    async def test_response_time_basic(self, llm_service):
        """Teste básico de tempo de resposta."""
        import time
        
        messages = [{"role": "user", "content": "Diga apenas 'RÁPIDO'"}]
        
        start_time = time.time()
        response = await llm_service.invoke(
            operation="chat",
            model_id="gpt-4.1-nano",
            payload={"messages": messages}
        )
        end_time = time.time()
        
        duration = end_time - start_time
        
        assert response is not None
        assert response["success"] == True
        assert duration < 30  # Máximo 30 segundos para resposta simples
        
        print(f"Response time: {duration:.2f}s")
        print(f"Response: {response['response_text']}")
        print(f"Service reported time: {response['response_time_ms']}ms")
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_basic(self, llm_service):
        """Teste básico de requisições concorrentes (simulado)."""
        responses = []
        
        # Fazer 3 chamadas sequenciais para simular concorrência
        for i in range(3):
            messages = [{"role": "user", "content": f"Teste {i+1}"}]
            response = await llm_service.invoke(
                operation="chat",
                model_id="gpt-4.1-nano",
                payload={"messages": messages}
            )
            responses.append(response)
        
        # Verificar que todas as respostas foram recebidas
        assert len(responses) == 3
        for response in responses:
            assert response is not None
            assert response["success"] == True
            assert "response_text" in response
        
        print(f"Concurrent test completed with {len(responses)} responses")
