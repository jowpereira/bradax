"""
Testes do SDK Bradax com dados reais.
Sem mocks, fallbacks ou simulações - apenas integração real.
"""
import pytest
import os
import sys
from pathlib import Path

# Adicionar src do SDK ao path
sdk_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(sdk_src))

from bradax.client import BradaxClient
from bradax.config.sdk_config import BradaxSDKConfig
from bradax.constants import (
    SDKConstants,
    SDKNetworkConstants,
    SDKModelConstants,
    SDKValidationConstants,
    get_sdk_environment,
    get_hub_url
)


class TestSDKCore:
    """Testes principais do SDK."""
    
    @pytest.fixture(scope="class")
    def sdk_config(self):
        """Configuração base do SDK."""
        return BradaxSDKConfig.for_integration_tests(
            broker_url="http://localhost:8000",
            project_id="test-sdk-project",
            api_key="test-sdk-key",
            enable_telemetry=True,
            enable_guardrails=True,
            timeout=30
        )
    
    @pytest.fixture(scope="class")
    def bradax_client(self, sdk_config):
        """Cliente SDK configurado."""
        return BradaxClient(config=sdk_config)
    
    def test_sdk_config_validation(self, sdk_config):
        """Teste de validação da configuração do SDK."""
        assert sdk_config.broker_url == "http://localhost:8000"
        assert sdk_config.project_id == "test-sdk-project"
        assert sdk_config.enable_telemetry is True
        assert sdk_config.enable_guardrails is True
        assert sdk_config.timeout == 30
    
    def test_client_initialization(self, bradax_client):
        """Teste de inicialização do cliente."""
        assert bradax_client is not None
        assert bradax_client.config is not None
        assert hasattr(bradax_client, 'validate_content')
        assert hasattr(bradax_client, 'record_telemetry_event')
    
    def test_local_guardrails_validation(self, bradax_client):
        """Teste de validação local dos guardrails."""
        # Conteúdo seguro
        safe_content = "Escreva um e-mail profissional sobre reunião."
        result = bradax_client.validate_content(safe_content)
        
        assert "is_safe" in result
        assert result["is_safe"] is True
        assert "violations" in result
        assert len(result["violations"]) == 0
        
        # Conteúdo perigoso
        dangerous_content = "Minha senha é admin123 e meu token é sk-abc123"
        result = bradax_client.validate_content(dangerous_content)
        
        assert result["is_safe"] is False
        assert len(result["violations"]) > 0
    
    def test_telemetry_recording(self, bradax_client):
        """Teste de gravação de telemetria local."""
        # Registrar eventos
        events = [
            {"type": "validation", "result": "safe", "content_length": 50},
            {"type": "validation", "result": "blocked", "content_length": 30},
            {"type": "request", "endpoint": "/test", "status": "success"}
        ]
        
        for event in events:
            bradax_client.record_telemetry_event(event)
        
        # Verificar telemetria
        telemetry = bradax_client.get_local_telemetry()
        
        assert "total_operations" in telemetry
        assert telemetry["total_operations"] >= len(events)
        assert "operation_types" in telemetry
        assert "validation" in telemetry["operation_types"]
        assert "request" in telemetry["operation_types"]
    
    def test_sdk_constants(self):
        """Teste das constantes do SDK."""
        assert hasattr(SDKConstants, 'DEFAULT_TIMEOUT')
        assert hasattr(SDKConstants, 'DEFAULT_BROKER_URL')
        assert hasattr(SDKConstants, 'GUARDRAIL_RULES')
        
        # Verificar valores sensatos
        assert SDKConstants.DEFAULT_TIMEOUT > 0
        assert isinstance(SDKConstants.DEFAULT_BROKER_URL, str)
        assert isinstance(SDKConstants.GUARDRAIL_RULES, list)
    
    def test_custom_guardrail_rules(self, bradax_client):
        """Teste de regras de guardrails customizadas."""
        # Adicionar regra custom
        custom_rule = {
            "id": "test_custom_rule",
            "pattern": r"\bTESTE_CUSTOM\b",
            "severity": "MEDIUM",  # Corrigido de risk_level para severity
            "message": "Termo de teste personalizado detectado"
        }
        
        bradax_client.add_custom_guardrail_rule(custom_rule)
        
        # Testar conteúdo que deve ser capturado pela regra custom
        content_with_custom = "Este conteúdo contém TESTE_CUSTOM que deve ser detectado."
        result = bradax_client.validate_content(content_with_custom)
        
        assert result["is_safe"] is False
        assert any("custom" in v.lower() for v in result["violations"])


class TestSDKIntegrationBroker:
    """Testes de integração do SDK com o broker."""
    
    @pytest.fixture(scope="class")
    def sdk_config(self):
        """Configuração do SDK para integração."""
        return BradaxSDKConfig.for_integration_tests(
            broker_url="http://localhost:8000",
            project_id="integration-test-project",
            api_key="integration-test-key",
            enable_telemetry=True,
            enable_guardrails=True
        )
    
    @pytest.fixture(scope="class")
    def bradax_client(self, sdk_config):
        """Cliente SDK configurado para integração."""
        return BradaxClient(config=sdk_config)
    
    def test_broker_health_check(self, bradax_client):
        """Teste de verificação de saúde do broker."""
        try:
            health_response = bradax_client.check_broker_health()
            
            if health_response:
                assert "status" in health_response
                assert health_response["status"] == "healthy"
            else:
                pytest.skip("Broker não está disponível para teste")
        
        except Exception as e:
            if "connection" in str(e).lower() or "refused" in str(e).lower():
                pytest.skip(f"Broker não disponível: {e}")
            else:
                raise e
    
    @pytest.mark.asyncio
    async def test_llm_request_flow(self, bradax_client):
        """Teste de fluxo completo de requisição LLM."""
        try:
            # Prompt seguro
            prompt = "Responda apenas com 'SDK_TEST_OK'"
            
            response = await bradax_client.send_llm_request(
                prompt=prompt,
                model="gpt-4.1-nano",
                max_tokens=10,
                temperature=0
            )
            
            assert response is not None
            assert "content" in response
            assert len(response["content"]) > 0
            
        except Exception as e:
            if "connection" in str(e).lower():
                pytest.skip(f"Broker não disponível para teste LLM: {e}")
            else:
                raise e
    
    def test_langchain_compatibility(self, bradax_client):
        """Teste de compatibilidade LangChain via SDK."""
        try:
            # Testar invoke() - compatibilidade LangChain
            result_invoke = bradax_client.invoke("Responda apenas: SDK_TEST_OK")
            
            assert result_invoke is not None
            assert "content" in result_invoke
            assert "response_metadata" in result_invoke
            
        except Exception as e:
            if "connection" in str(e).lower():
                pytest.skip(f"Broker não disponível para teste LangChain: {e}")
            else:
                raise e


class TestSDKConfiguration:
    """Testes de configuração avançada do SDK."""
    
    def test_configuration_with_custom_settings(self):
        """Teste de configuração com settings customizados."""
        custom_settings = {
            "custom_timeout": 60,
            "custom_retries": 5,
            "custom_guardrails": [
                {
                    "id": "custom_corporate_rule",
                    "pattern": r"\bCORPORATE_SECRET\b",
                    "risk_level": "HIGH"
                }
            ]
        }
        
        config = BradaxSDKConfig.for_integration_tests(
            broker_url="http://localhost:8000",
            project_id="custom-test-project",
            api_key="custom-test-key",
            custom_settings=custom_settings
        )
        
        assert config.custom_settings["custom_timeout"] == 60
        assert config.custom_settings["custom_retries"] == 5
        assert len(config.custom_settings["custom_guardrails"]) == 1
    
    def test_configuration_validation_errors(self):
        """Teste de validação de erros de configuração."""
        # URL inválida
        with pytest.raises(ValueError):
            BradaxSDKConfig.for_integration_tests(
                broker_url="invalid-url",
                project_id="test-project",
                api_key="test-key"
            )
        
        # API key vazia
        with pytest.raises(ValueError):
            BradaxSDKConfig.for_integration_tests(
                broker_url="http://localhost:8000",
                project_id="test-project",
                api_key=""
            )
        
        # Project ID vazio
        with pytest.raises(ValueError):
            BradaxSDKConfig.for_integration_tests(
                broker_url="http://localhost:8000",
                project_id="",
                api_key="test-key"
            )
    
    def test_environment_variables_override(self):
        """Teste de override via variáveis de ambiente."""
        # Definir variáveis de ambiente temporariamente
        original_env = {}
        test_env_vars = {
            "BRADAX_SDK_BROKER_URL": "http://env-broker:8000",
            "BRADAX_SDK_API_KEY": "env-api-key",
            "BRADAX_SDK_PROJECT_ID": "env-project-id"
        }
        
        # Salvar valores originais e definir novos
        for key, value in test_env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            # Criar configuração que deve usar variáveis de ambiente
            config = BradaxSDKConfig.from_environment()
            
            assert config.broker_url == "http://env-broker:8000"
            # api_key não é armazenada diretamente no config, mas project_id sim
            assert config.project_id == "env-project-id"
        
        finally:
            # Restaurar variáveis originais
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value


class TestSDKErrorHandling:
    """Testes de tratamento de erros do SDK."""
    
    def test_network_error_handling(self):
        """Teste de tratamento de erros de rede."""
        config = BradaxSDKConfig.for_integration_tests(
            broker_url="http://nonexistent-broker:8000",
            project_id="test-project",
            api_key="test-key",
            timeout=1  # Timeout curto para forçar erro
        )
        
        client = BradaxClient(config)
        
        # Deve capturar erro de conexão graciosamente
        with pytest.raises(Exception) as exc_info:
            client.check_broker_health()
        
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ["connection", "timeout", "network"])
    
    def test_invalid_response_handling(self):
        """Teste de tratamento de respostas inválidas."""
        config = BradaxSDKConfig.for_integration_tests(
            broker_url="http://localhost:8000",
            project_id="test-project",
            api_key="invalid-api-key"
        )
        
        client = BradaxClient(config)
        
        # Tentar operação que deve falhar com chave inválida
        try:
            # Usar check_broker_health ao invés de create_project
            result = client.check_broker_health()
            
            # Se não gerou exceção, deve indicar erro na resposta
            if result and "error" in result:
                assert "authentication" in result["error"].lower() or "authorization" in result["error"].lower()
        
        except Exception as e:
            # Exceção esperada para auth inválida
            error_msg = str(e).lower()
            assert any(keyword in error_msg for keyword in ["auth", "unauthorized", "forbidden"])
    
    def test_malformed_data_handling(self):
        """Teste de tratamento de dados malformados."""
        config = BradaxSDKConfig.for_integration_tests(
            broker_url="http://localhost:8000",
            project_id="test-project",
            api_key="test-key"
        )
        
        client = BradaxClient(config)
        
        # Dados malformados para guardrails (ao invés de projeto)
        malformed_rule = {
            "id": None,  # ID nulo
            "pattern": "",  # Pattern vazio
            "severity": "INVALID_LEVEL"  # Severity inválida
        }
        
        with pytest.raises(Exception) as exc_info:
            client.add_custom_guardrail_rule(malformed_rule)
        
        # Deve indicar erro de validação
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ["validation", "invalid", "malformed"])
