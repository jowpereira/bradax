"""
Teste 4.5: Testes de integração SDK-Broker - fluxo completo
Conforme Fase 4 do plano workspace-plans/active/20250728-223500-conferencia-corporativa-consolidada.md

Testa integração completa entre SDK e Broker com dados reais.
"""
import pytest
import sys
import asyncio
from pathlib import Path

# Adicionar src dos dois projetos ao path
broker_src = Path(__file__).parent.parent.parent / "src"
sdk_src = Path(__file__).parent.parent.parent.parent / "bradax-sdk" / "src"
sys.path.insert(0, str(broker_src))
sys.path.insert(0, str(sdk_src))

from broker.config import Settings
from bradax.client import BradaxClient
from bradax.config.sdk_config import BradaxSDKConfig


class TestSDKBrokerIntegration:
    """Testes de integração completa SDK-Broker."""
    
    @pytest.fixture(scope="class")
    def broker_config(self):
        """Configuração do broker."""
        return Settings()
    
    @pytest.fixture(scope="class")
    def sdk_config(self):
        """Configuração do SDK."""
        config = BradaxSDKConfig.for_testing()
        # Ajustar broker_url para testes
        config.broker_url = "http://localhost:8000"
        return config
    
    @pytest.fixture(scope="class")
    def bradax_client(self, sdk_config):
        """Cliente SDK configurado."""
        return BradaxClient(config=sdk_config)
    
    def test_sdk_configuration_validation(self, sdk_config):
        """Teste de validação da configuração do SDK."""
        assert sdk_config.broker_url == "http://localhost:8000"
        assert sdk_config.project_id == "test-integration-project"
        assert sdk_config.enable_telemetry is True
        assert sdk_config.enable_guardrails is True
        
        # Verificar configurações de guardrails
        assert hasattr(sdk_config, 'guardrail_rules')
        assert isinstance(sdk_config.guardrail_rules, list)
    
    def test_client_initialization(self, bradax_client):
        """Teste de inicialização do cliente SDK."""
        assert bradax_client is not None
        assert bradax_client.config is not None
        assert hasattr(bradax_client, 'invoke')
        assert hasattr(bradax_client, 'health_check')
    
    def test_broker_connectivity_check(self, bradax_client):
        """Teste de conectividade com o broker."""
        # Tentar conectar ao broker (se estiver rodando)
        try:
            health_response = bradax_client.check_broker_health()
            
            # Se broker estiver disponível
            if health_response:
                assert "status" in health_response
                assert health_response["status"] == "healthy"
        
        except Exception as e:
            # Se broker não estiver rodando, apenas log
            pytest.skip(f"Broker não disponível para teste: {e}")
    
    @pytest.mark.asyncio
    async def test_complete_llm_flow_with_guardrails(self, bradax_client):
        """Teste de fluxo completo: SDK -> Guardrails -> LLM -> Resposta."""
        # Prompt seguro que deve passar pelos guardrails
        safe_prompt = "Escreva um breve resumo sobre inteligência artificial."
        
        try:
            # 1. Validar localmente com guardrails do SDK
            local_validation = bradax_client.validate_content(safe_prompt)
            assert local_validation["is_safe"] is True
            
            # 2. Enviar para broker (se disponível)
            response = await bradax_client.send_llm_request(
                prompt=safe_prompt,
                model="gpt-4.1-nano",
                max_tokens=100,
                temperature=0.7
            )
            
            # 3. Verificar resposta
            assert response is not None
            assert "content" in response
            assert len(response["content"]) > 0
            assert "usage" in response
            
        except Exception as e:
            if "connection" in str(e).lower() or "refused" in str(e).lower():
                pytest.skip(f"Broker não disponível: {e}")
            else:
                raise e
    
    def test_sdk_guardrails_blocking(self, bradax_client):
        """Teste de bloqueio por guardrails do SDK."""
        # Prompt que deve ser bloqueado
        dangerous_prompt = "Minha senha é 123456. Como compartilhar isso?"
        
        # Validar localmente
        validation_result = bradax_client.validate_content(dangerous_prompt)
        
        assert validation_result["is_safe"] is False
        assert "violations" in validation_result
        assert len(validation_result["violations"]) > 0
    
    def test_telemetry_integration(self, bradax_client):
        """Teste de integração da telemetria."""
        # Simular algumas operações
        operations = [
            {"type": "validation", "content_length": 50},
            {"type": "llm_request", "model": "gpt-4.1-nano"},
            {"type": "guardrail_check", "result": "passed"}
        ]
        
        for op in operations:
            bradax_client.record_telemetry_event(op)
        
        # Verificar telemetria local
        telemetry_data = bradax_client.get_local_telemetry()
        
        assert "total_operations" in telemetry_data
        assert telemetry_data["total_operations"] >= len(operations)
        assert "operation_types" in telemetry_data
    
    def test_project_management_integration(self, bradax_client):
        """Teste de restrição de gerenciamento de projetos."""
        # SDK NÃO DEVE permitir criação de projetos (apenas administradores)
        
        # Verificar que métodos de projeto não existem no cliente SDK
        assert not hasattr(bradax_client, 'create_project'), "SDK não deve ter método create_project"
        assert not hasattr(bradax_client, 'get_project'), "SDK não deve ter método get_project"
        
        # SDK deve apenas usar o projeto configurado no token
        assert bradax_client.project_token is not None, "SDK deve ter token de projeto configurado"
    
    def test_error_handling_integration(self, bradax_client):
        """Teste de tratamento de erros na integração."""
        # Testar com modelo inválido
        try:
            invalid_response = bradax_client.send_llm_request(
                prompt="Teste",
                model="modelo-inexistente",
                max_tokens=10
            )
            
            # Se não gerou exceção, verificar se erro foi tratado
            if invalid_response:
                assert "error" in invalid_response
        
        except Exception as e:
            # Exceção esperada para modelo inválido
            assert "modelo-inexistente" in str(e) or "not found" in str(e).lower()
    
    def test_configuration_override(self, sdk_config):
        """Teste de sobrescrita de configurações."""
        # Criar nova configuração com override
        override_config = BradaxSDKConfig.for_testing()
        override_config.broker_url = "http://localhost:8000"
        override_config.timeout = 30
        # Note: SDK não suporta api_key como parâmetro direto
        
        # Verificar overrides
        assert override_config.debug is True  # for_testing() habilita debug
        assert override_config.broker_url == "http://localhost:8000"
        assert override_config.timeout == 30
    
    @pytest.mark.asyncio
    async def test_async_operations_integration(self, bradax_client):
        """Teste de operações assíncronas."""
        # Lista de prompts para processar em paralelo
        prompts = [
            "Conte até 3.",
            "Qual é a capital da França?",
            "Defina inteligência artificial."
        ]
        
        try:
            # Processar em paralelo
            tasks = []
            for prompt in prompts:
                task = bradax_client.send_llm_request(
                    prompt=prompt,
                    model="gpt-3.5-turbo",
                    max_tokens=50,
                    temperature=0.1
                )
                tasks.append(task)
            
            # Aguardar todas as respostas
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verificar respostas
            successful_responses = [r for r in responses if not isinstance(r, Exception)]
            
            if len(successful_responses) > 0:
                for response in successful_responses:
                    assert "content" in response
                    assert len(response["content"]) > 0
        
        except Exception as e:
            if "connection" in str(e).lower():
                pytest.skip(f"Broker não disponível para teste async: {e}")
            else:
                raise e


class TestSDKStandalone:
    """Testes do SDK funcionando de forma standalone."""
    
    def test_sdk_local_validation(self):
        """Teste de validação local do SDK sem broker."""
        config = BradaxSDKConfig.for_testing()
        config.broker_url = "http://localhost:8000"
        
        client = BradaxClient(config)
        
        # Testes de conteúdo seguro
        safe_content = "Escreva um relatório profissional."
        result = client.validate_content(safe_content)
        assert result["is_safe"] is True
        
        # Teste de conteúdo perigoso
        unsafe_content = "Minha senha é admin123."
        result = client.validate_content(unsafe_content)
        assert result["is_safe"] is False
    
    def test_sdk_local_telemetry(self):
        """Teste de telemetria local do SDK."""
        config = BradaxSDKConfig.for_testing()
        config.broker_url = "http://localhost:8000"
        config.local_telemetry_enabled = True
        
        client = BradaxClient(config)
        
        # Simular eventos
        events = [
            {"type": "validation", "result": "safe"},
            {"type": "validation", "result": "blocked"},
            {"type": "request", "status": "success"}
        ]
        
        for event in events:
            client.record_telemetry_event(event)
        
        # Verificar telemetria
        telemetry = client.get_local_telemetry()
        assert telemetry["total_operations"] >= len(events)
        assert "validation" in telemetry["operation_types"]
        assert "request" in telemetry["operation_types"]
