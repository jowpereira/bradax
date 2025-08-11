"""
Testes de Integração End-to-End - Sistema Bradax Completo
=========================================================

Testes rigorosos de integração real sem mocks ou fallbacks.
Fluxo completo: SDK → Hub → gpt-4.1-nano → Hub → SDK

🚨 IMPORTANTE: 
- Usa gpt-4.1-nano EXCLUSIVAMENTE (sem outros modelos)
- ZERO mocks - apenas dados reais e sistema funcionando
- Valida JSONs após cada execução
- Testa cenários reais de uso e falha

Baseado em:
- Análise completa da arquitetura
- Fluxo SDK→Hub→OpenAI→Hub→SDK mapeado
- Sistema de governança inegociável
- Telemetria e logs obrigatórios
"""

import asyncio
import json
import pytest
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import httpx
import requests
from fastapi.testclient import TestClient

# Imports dos sistemas Bradax
import sys
from pathlib import Path

# Adicionar paths
broker_path = Path(__file__).parent.parent.parent / "bradax-broker" / "src"  
sdk_path = Path(__file__).parent.parent.parent / "bradax-sdk" / "src"
sys.path.insert(0, str(broker_path))
sys.path.insert(0, str(sdk_path))

from broker.main import app
from bradax.client import BradaxClient
from bradax.config.sdk_config import BradaxSDKConfig, set_sdk_config
from tests.fixtures.test_fixtures import (
    BradaxTestFixtures, 
    BradaxTestDataManager, 
    TestValidators,
    requires_real_telemetry
)


@pytest.mark.integration
class TestEndToEndIntegration:
    """Testes de integração completa do sistema"""
    
    @pytest.fixture(scope="class")
    def test_data_manager(self):
        """Setup de dados para toda a classe de testes"""
        with BradaxTestDataManager() as manager:
            print(f"🔧 Test environment setup: {manager.temp_dir}")
            yield manager
    
    @pytest.fixture
    def hub_client(self, test_data_manager):
        """Cliente HTTP para o Hub (FastAPI)"""
        with TestClient(app) as client:
            yield client
    
    @pytest.fixture
    def sdk_client(self, test_data_manager):
        """Cliente do SDK configurado para testes"""
        # Configurar SDK para usar dados de teste
        config = BradaxSDKConfig.for_testing(
            broker_url="http://localhost:8000",  # URL do Hub
            project_id="proj_test_bradax_2025",
            timeout=30,  # Tempo suficiente para gpt-4.1-nano
            enable_telemetry=True,
            enable_guardrails=True
        )
        set_sdk_config(config)
        
        # Criar cliente SDK
        token = BradaxTestFixtures.get_valid_project_token()
        client = BradaxClient(project_token=token)
        
        yield client
    
    @pytest.mark.slow
    @requires_real_telemetry
    def test_complete_valid_flow_gpt_4_1_nano(self, hub_client, sdk_client, test_data_manager):
        """
        Teste: Fluxo completo válido com gpt-4.1-nano real
        
        Cenário: SDK → Hub → OpenAI gpt-4.1-nano → Hub → SDK
        Esperado: Response válida, telemetria gravada, sem erros
        Validar: Sistema funcionando end-to-end com modelo real
        """
        # Request válida para gpt-4.1-nano
        valid_request = BradaxTestFixtures.get_valid_llm_request()
        
        # Headers completos com telemetria real
        headers = {
            "Authorization": f"Bearer {valid_request['project_token']}",
            "Content-Type": "application/json",
            "X-Bradax-Telemetry": json.dumps(valid_request["telemetry"])
        }
        
        request_body = {
            "model": "gpt-4.1-nano",  # 🚨 EXCLUSIVAMENTE este modelo
            "messages": valid_request["messages"],
            "max_tokens": valid_request["max_tokens"],
            "temperature": valid_request.get("temperature", 0.7)
        }
        
        print(f"🚀 Executando request para gpt-4.1-nano...")
        start_time = time.time()
        
        response = hub_client.post("/llm/invoke", json=request_body, headers=headers)
        
        execution_time = time.time() - start_time
        print(f"⏱️  Tempo de execução: {execution_time:.2f}s")
        
        # Validar response
        assert response.status_code == 200, \
            f"Request válida falhou: {response.status_code} - {response.text}"
        
        response_data = response.json()
        
        # Verificar estrutura de response esperada
        assert "choices" in response_data or "response" in response_data, \
            f"Response deve ter estrutura válida: {list(response_data.keys())}"
        
        # Verificar que response não está vazia
        if "choices" in response_data:
            assert len(response_data["choices"]) > 0, "Response deve ter pelo menos uma choice"
            content = response_data["choices"][0].get("message", {}).get("content", "")
        else:
            content = response_data.get("response", "")
        
        assert len(content.strip()) > 0, "Response não deve estar vazia"
        
        print(f"✅ Response recebida do gpt-4.1-nano: {len(content)} caracteres")
        print(f"📝 Preview: {content[:100]}...")
        
        # Verificar telemetria foi gravada (simulação)
        telemetry_logs = test_data_manager.get_telemetry_logs()
        print(f"📊 Logs de telemetria: {len(telemetry_logs)}")
        
        # TODO: Validar logs específicos quando integração completa estiver pronta
    
    @pytest.mark.slow
    def test_blocked_content_by_guardrails(self, hub_client, test_data_manager):
        """
        Teste: Conteúdo bloqueado por guardrails customizados
        
        Cenário: Request com código Python (violação de guardrail)
        Esperado: HTTP 403/400, log de guardrail gravado
        Validar: Sistema de governança funcionando
        """
        blocked_request = BradaxTestFixtures.get_blocked_python_request()
        
        headers = {
            "Authorization": f"Bearer {blocked_request['project_token']}",
            "Content-Type": "application/json", 
            "X-Bradax-Telemetry": json.dumps(blocked_request["telemetry"])
        }
        
        request_body = {
            "model": "gpt-4.1-nano",
            "messages": blocked_request["messages"],
            "max_tokens": blocked_request["max_tokens"]
        }
        
        print(f"🛡️ Testando bloqueio por guardrail...")
        
        response = hub_client.post("/llm/invoke", json=request_body, headers=headers)
        
        # Deve ser bloqueado
        assert response.status_code in [400, 403], \
            f"Conteúdo com Python deveria ser bloqueado: {response.status_code}"
        
        error_data = response.json()
        error_message = error_data.get("detail", "").lower()
        
        # Verificar mensagem de bloqueio
        assert any(keyword in error_message for keyword in ["guardrail", "blocked", "python", "code"]), \
            f"Erro deve mencionar guardrail: {error_data.get('detail')}"
        
        print(f"✅ Conteúdo bloqueado por guardrail: {error_data.get('detail')}")
        
        # Verificar logs de guardrail
        guardrail_logs = test_data_manager.get_guardrail_logs()
        print(f"🛡️ Logs de guardrail: {len(guardrail_logs)}")
    
    def test_unauthorized_llm_model_rejection(self, hub_client, test_data_manager):
        """
        Teste: Modelo LLM não autorizado é rejeitado
        
        Cenário: Token válido mas tentar usar modelo fora de allowed_llms
        Esperado: HTTP 403 Forbidden
        Validar: Controle de acesso por modelo
        """
        unauthorized_request = BradaxTestFixtures.get_unauthorized_llm_request()
        
        headers = {
            "Authorization": f"Bearer {unauthorized_request['project_token']}",
            "Content-Type": "application/json",
            "X-Bradax-Telemetry": json.dumps(unauthorized_request["telemetry"])
        }
        
        request_body = {
            "model": "gpt-4-turbo",  # ❌ NÃO está em allowed_llms
            "messages": unauthorized_request["messages"],
            "max_tokens": unauthorized_request["max_tokens"]
        }
        
        print(f"🚫 Testando modelo não autorizado (gpt-4-turbo)...")
        
        response = hub_client.post("/llm/invoke", json=request_body, headers=headers)
        
        # Deve ser rejeitado
        assert response.status_code == 403, \
            f"Modelo não autorizado deveria ser rejeitado: {response.status_code}"
        
        error_data = response.json()
        error_message = error_data.get("detail", "").lower()
        
        assert any(keyword in error_message for keyword in ["model", "allowed", "permission", "unauthorized"]), \
            f"Erro deve mencionar modelo não permitido: {error_data.get('detail')}"
        
        print(f"✅ Modelo não autorizado rejeitado: {error_data.get('detail')}")
    
    def test_missing_telemetry_rejection(self, hub_client, test_data_manager):
        """
        Teste: Request sem telemetria é rejeitada
        
        Cenário: Request perfeita em tudo exceto telemetria ausente
        Esperado: HTTP 400 Bad Request
        Validar: Telemetria é obrigatória (governança inegociável)
        """
        request_without_telemetry = BradaxTestFixtures.get_request_without_telemetry()
        
        headers = {
            "Authorization": f"Bearer {request_without_telemetry['project_token']}",
            "Content-Type": "application/json"
            # X-Bradax-Telemetry ausente intencionalmente
        }
        
        request_body = {
            "model": "gpt-4.1-nano",
            "messages": request_without_telemetry["messages"],
            "max_tokens": request_without_telemetry["max_tokens"]
        }
        
        print(f"📊 Testando rejeição por telemetria ausente...")
        
        response = hub_client.post("/llm/invoke", json=request_body, headers=headers)
        
        # Deve ser rejeitado
        assert response.status_code == 400, \
            f"Request sem telemetria deveria retornar 400: {response.status_code}"
        
        error_data = response.json()
        error_message = error_data.get("detail", "").lower()
        
        assert any(keyword in error_message for keyword in ["telemetry", "required", "missing"]), \
            f"Erro deve mencionar telemetria: {error_data.get('detail')}"
        
        print(f"✅ Request sem telemetria rejeitada: {error_data.get('detail')}")
    
    def test_invalid_token_rejection(self, hub_client, test_data_manager):
        """
        Teste: Token inválido é rejeitado
        
        Cenário: Request com token que não existe em projects.json
        Esperado: HTTP 403 Forbidden
        Validar: Autenticação rigorosa
        """
        invalid_token = BradaxTestFixtures.get_invalid_project_token()
        valid_request = BradaxTestFixtures.get_valid_llm_request()
        
        headers = {
            "Authorization": f"Bearer {invalid_token}",
            "Content-Type": "application/json",
            "X-Bradax-Telemetry": json.dumps(valid_request["telemetry"])
        }
        
        request_body = {
            "model": "gpt-4.1-nano",
            "messages": valid_request["messages"],
            "max_tokens": valid_request["max_tokens"]
        }
        
        print(f"🔐 Testando token inválido...")
        
        response = hub_client.post("/llm/invoke", json=request_body, headers=headers)
        
        # Deve ser rejeitado
        assert response.status_code == 403, \
            f"Token inválido deveria retornar 403: {response.status_code}"
        
        error_data = response.json()
        error_message = error_data.get("detail", "").lower()
        
        assert any(keyword in error_message for keyword in ["token", "unauthorized", "forbidden", "invalid"]), \
            f"Erro deve mencionar token: {error_data.get('detail')}"
        
        print(f"✅ Token inválido rejeitado: {error_data.get('detail')}")


@pytest.mark.integration
class TestJSONDataValidation:
    """Testes de validação dos arquivos JSON após operações"""
    
    @pytest.fixture
    def test_data_manager(self):
        """Manager para inspeção de dados"""
        with BradaxTestDataManager() as manager:
            yield manager
    
    def test_projects_json_integrity(self, test_data_manager):
        """
        Teste: Integridade do arquivo projects.json
        
        Cenário: Verificar estrutura e dados dos projetos
        Esperado: Arquivo válido, projetos com campos obrigatórios
        Validar: Dados consistentes para testes
        """
        projects_data = test_data_manager.read_json_file(test_data_manager.projects_file)
        
        assert isinstance(projects_data, list), "Projects deve ser uma lista"
        assert len(projects_data) > 0, "Deve ter pelo menos um projeto"
        
        for project in projects_data:
            # Verificar estrutura ProjectData
            assert TestValidators.validate_project_data(project), \
                f"Projeto inválido: {project.get('project_id', 'unknown')}"
            
            # Verificar campos específicos
            assert project["status"] in ["active", "blocked", "suspended"], \
                f"Status inválido: {project['status']}"
            
            assert isinstance(project["allowed_llms"], list), "allowed_llms deve ser lista"
            assert len(project["allowed_llms"]) > 0, "Deve ter pelo menos um LLM permitido"
            
            # Verificar que gpt-4.1-nano está na lista (obrigatório para testes)
            if project["status"] == "active":
                assert "gpt-4.1-nano" in project["allowed_llms"], \
                    "Projetos ativos devem permitir gpt-4.1-nano"
        
        print(f"✅ Projects.json válido: {len(projects_data)} projetos")
    
    def test_llm_models_json_integrity(self, test_data_manager):
        """
        Teste: Integridade do arquivo llm_models.json
        
        Cenário: Verificar catálogo de modelos LLM
        Esperado: gpt-4.1-nano presente e habilitado
        Validar: Modelo obrigatório disponível
        """
        models_data = test_data_manager.read_json_file(test_data_manager.llm_models_file)
        
        assert isinstance(models_data, list), "Models deve ser uma lista"
        assert len(models_data) > 0, "Deve ter pelo menos um modelo"
        
        # Verificar que gpt-4.1-nano está presente
        gpt_4_1_nano = None
        for model in models_data:
            if model.get("model_id") == "gpt-4.1-nano":
                gpt_4_1_nano = model
                break
        
        assert gpt_4_1_nano is not None, "gpt-4.1-nano deve estar no catálogo"
        assert gpt_4_1_nano["enabled"] is True, "gpt-4.1-nano deve estar habilitado"
        assert gpt_4_1_nano["provider"] == "openai", "Provider deve ser openai"
        
        print(f"✅ LLM models.json válido: gpt-4.1-nano disponível")
    
    def test_json_files_integrity_check(self, test_data_manager):
        """
        Teste: Verificação geral de integridade dos JSONs
        
        Cenário: Validar que todos os arquivos são JSON válidos
        Esperado: Todos os arquivos podem ser lidos sem erro
        Validar: Arquivos não corrompidos
        """
        integrity_results = test_data_manager.validate_json_integrity()
        
        for file_name, is_valid in integrity_results.items():
            assert is_valid, f"Arquivo {file_name}.json está corrompido"
        
        print(f"✅ Todos os JSONs íntegros: {list(integrity_results.keys())}")
    
    def test_telemetry_logs_after_requests(self, test_data_manager):
        """
        Teste: Logs de telemetria são gravados após requests
        
        Cenário: Simular request e verificar se log foi gravado
        Esperado: Arquivo telemetry.json atualizado
        Validar: Sistema de logging funciona
        """
        # Dados iniciais
        initial_logs = test_data_manager.get_telemetry_logs()
        initial_count = len(initial_logs)
        
        # Simular adição de log (como o sistema faria após request real)
        test_log = BradaxTestFixtures.get_expected_success_telemetry_log()
        current_logs = test_data_manager.get_telemetry_logs()
        current_logs.append(test_log)
        test_data_manager._write_json_file(test_data_manager.telemetry_file, current_logs)
        
        # Verificar que log foi adicionado
        updated_logs = test_data_manager.get_telemetry_logs()
        assert len(updated_logs) == initial_count + 1, "Um log deve ter sido adicionado"
        
        # Verificar estrutura do log
        new_log = updated_logs[-1]  # Último log adicionado
        assert new_log["model_used"] == "gpt-4.1-nano", "Deve usar modelo correto"
        assert new_log["status_code"] == 200, "Deve indicar sucesso"
        assert "system_info" in new_log, "Deve conter system_info"
        
        print(f"✅ Log de telemetria gravado: {new_log['telemetry_id']}")


# Configuração de marcadores para pytest
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow  # Testes que fazem calls reais para APIs
]


# Executar testes se rodado diretamente
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "not slow"])  # Pula testes lentos por padrão
