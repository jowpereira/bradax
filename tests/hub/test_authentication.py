"""
Testes do Hub - Validação de Autenticação e Tokens
==================================================

Testes rigorosos baseados na análise completa da arquitetura.
Sem mocks - apenas validações reais com dados controlados.

Baseado em:
- Middleware de autenticação analisado
- Project auth service 
- Storage com transações ACID
- Estrutura ProjectData real
"""

import asyncio
import json
import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any

import httpx
from fastapi.testclient import TestClient

# Imports do sistema Bradax
import sys
from pathlib import Path

# Adicionar o path do bradax-broker
broker_path = Path(__file__).parent.parent.parent / "bradax-broker" / "src"
sys.path.insert(0, str(broker_path))

from broker.main import app
from broker.storage.json_storage import JsonStorage
from tests.fixtures.test_fixtures import BradaxTestFixtures


class TestHubAuthentication:
    """Testes de autenticação do Hub - baseados na análise real"""
    
    @pytest.fixture
    def test_data_manager(self):
        """Setup de dados de teste em arquivos temporários"""
        temp_dir = Path(tempfile.mkdtemp(prefix="bradax_hub_auth_test_"))
        
        # Arquivos de configuração
        projects_file = temp_dir / "projects.json"
        llm_models_file = temp_dir / "llm_models.json"
        
        # Dados realistas baseados na análise
        projects_data = [BradaxTestFixtures.get_test_project_data()]
        llm_models_data = BradaxTestFixtures.get_llm_models_data()
        
        # Escrever arquivos
        with open(projects_file, 'w') as f:
            json.dump(projects_data, f, indent=2)
        with open(llm_models_file, 'w') as f:
            json.dump(llm_models_data, f, indent=2)
        
        yield {
            "temp_dir": temp_dir,
            "projects_file": projects_file,
            "llm_models_file": llm_models_file
        }
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def client(self, test_data_manager):
        """Cliente de teste configurado com dados reais"""
        # Configurar app com dados de teste
        app.dependency_overrides = {}  # Reset dependencies
        
        with TestClient(app) as client:
            yield client
    
    def test_valid_token_authentication(self, client):
        """
        Teste: Token válido deve ser aceito
        
        Cenário: Request com token presente em projects.json
        Esperado: HTTP 200 ou processamento normal (não 403)
        Validar: Token é encontrado e projeto está ativo
        """
        valid_token = BradaxTestFixtures.get_valid_project_token()
        
        # Request com telemetria completa
        request_data = {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Hello, test message"}],
            "max_tokens": 50
        }
        
        headers = {
            "Authorization": f"Bearer {valid_token}",
            "Content-Type": "application/json",
            "X-Bradax-Telemetry": json.dumps(
                BradaxTestFixtures.get_real_machine_telemetry()
            )
        }
        
        response = client.post("/llm/invoke", json=request_data, headers=headers)
        
        # Deve NÃO ser 403 (forbidden)
        assert response.status_code != 403, f"Token válido foi rejeitado: {response.text}"
        
        # Se retornou erro por outro motivo, verificar se não foi por autenticação
        if response.status_code != 200:
            error_detail = response.json().get("detail", "")
            assert "token" not in error_detail.lower(), f"Erro relacionado a token: {error_detail}"
            assert "unauthorized" not in error_detail.lower(), f"Erro de autorização: {error_detail}"
        
        print(f"✅ Token válido aceito: {response.status_code}")
    
    def test_invalid_token_rejection(self, client):
        """
        Teste: Token inválido deve ser rejeitado
        
        Cenário: Request com token não existente em projects.json
        Esperado: HTTP 403 Forbidden
        Validar: Mensagem de erro específica sobre token
        """
        invalid_token = BradaxTestFixtures.get_invalid_project_token()
        
        request_data = {
            "model": "gpt-4.1-nano", 
            "messages": [{"role": "user", "content": "This should be blocked"}],
            "max_tokens": 50
        }
        
        headers = {
            "Authorization": f"Bearer {invalid_token}",
            "Content-Type": "application/json",
            "X-Bradax-Telemetry": json.dumps(
                BradaxTestFixtures.get_real_machine_telemetry()
            )
        }
        
        response = client.post("/llm/invoke", json=request_data, headers=headers)
        
        # Deve ser exatamente 403
        assert response.status_code == 403, f"Token inválido não foi rejeitado corretamente: {response.status_code}"
        
        # Verificar mensagem de erro
        error_data = response.json()
        assert "detail" in error_data, "Response de erro deve ter campo 'detail'"
        
        error_message = error_data["detail"].lower()
        assert any(keyword in error_message for keyword in ["token", "unauthorized", "forbidden"]), \
            f"Mensagem de erro não indica problema de token: {error_data['detail']}"
        
        print(f"✅ Token inválido rejeitado corretamente: {error_data['detail']}")
    
    def test_missing_token_rejection(self, client):
        """
        Teste: Request sem token deve ser rejeitada
        
        Cenário: Request sem header Authorization
        Esperado: HTTP 403 ou 401 Unauthorized
        Validar: Sistema rejeita requests não autenticadas
        """
        request_data = {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "This should be blocked"}],
            "max_tokens": 50
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Bradax-Telemetry": json.dumps(
                BradaxTestFixtures.get_real_machine_telemetry()
            )
            # Authorization header ausente intencionalmente
        }
        
        response = client.post("/llm/invoke", json=request_data, headers=headers)
        
        # Deve ser 401 ou 403
        assert response.status_code in [401, 403], \
            f"Request sem token deveria ser rejeitada: {response.status_code}"
        
        print(f"✅ Request sem token rejeitada: {response.status_code}")
    
    def test_unauthorized_llm_model(self, client):
        """
        Teste: Request para LLM não permitido no projeto
        
        Cenário: Token válido mas modelo não está em allowed_llms
        Esperado: HTTP 403 Forbidden  
        Validar: Controle de acesso por modelo funciona
        """
        valid_token = BradaxTestFixtures.get_valid_project_token()
        
        # Tentar usar modelo não permitido (não está em allowed_llms)
        request_data = {
            "model": "gpt-4-turbo",  # NÃO está em allowed_llms do projeto teste
            "messages": [{"role": "user", "content": "This model is not allowed"}],
            "max_tokens": 50
        }
        
        headers = {
            "Authorization": f"Bearer {valid_token}",
            "Content-Type": "application/json",
            "X-Bradax-Telemetry": json.dumps(
                BradaxTestFixtures.get_real_machine_telemetry()
            )
        }
        
        response = client.post("/llm/invoke", json=request_data, headers=headers)
        
        # Deve ser 403 (forbidden model)
        assert response.status_code == 403, \
            f"Modelo não autorizado foi aceito: {response.status_code}"
        
        # Verificar se erro menciona modelo
        error_data = response.json()
        error_message = error_data.get("detail", "").lower()
        assert any(keyword in error_message for keyword in ["model", "allowed", "permission"]), \
            f"Erro não indica problema com modelo: {error_data.get('detail')}"
        
        print(f"✅ Modelo não autorizado bloqueado: {error_data.get('detail')}")
    
    def test_blocked_project_status(self, client):
        """
        Teste: Projeto com status 'blocked' deve ser rejeitado
        
        Cenário: Token válido mas projeto tem status != 'active'
        Esperado: HTTP 403 Forbidden
        Validar: Status do projeto é verificado
        """
        # Este teste requer dados adicionais - projeto bloqueado
        # Será implementado quando a fixture completa estiver pronta
        pytest.skip("Aguardando implementação completa das fixtures")


class TestHubTelemetryValidation:
    """Testes de validação de telemetria obrigatória"""
    
    @pytest.fixture
    def client(self):
        with TestClient(app) as client:
            yield client
    
    def test_missing_telemetry_rejection(self, client):
        """
        Teste: Request sem telemetria deve ser rejeitada
        
        Cenário: Request válida mas sem header X-Bradax-Telemetry
        Esperado: HTTP 400 Bad Request
        Validar: Telemetria é obrigatória em 100% das requests
        """
        valid_token = BradaxTestFixtures.get_valid_project_token()
        
        request_data = {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Test without telemetry"}],
            "max_tokens": 50
        }
        
        headers = {
            "Authorization": f"Bearer {valid_token}",
            "Content-Type": "application/json"
            # X-Bradax-Telemetry ausente intencionalmente
        }
        
        response = client.post("/llm/invoke", json=request_data, headers=headers)
        
        # Deve ser 400 (bad request por telemetria ausente)
        assert response.status_code == 400, \
            f"Request sem telemetria deveria retornar 400: {response.status_code}"
        
        # Verificar mensagem sobre telemetria
        error_data = response.json()
        error_message = error_data.get("detail", "").lower()
        assert "telemetry" in error_message or "telemetria" in error_message, \
            f"Erro deve mencionar telemetria: {error_data.get('detail')}"
        
        print(f"✅ Request sem telemetria rejeitada: {error_data.get('detail')}")
    
    def test_invalid_telemetry_format(self, client):
        """
        Teste: Telemetria com formato inválido deve ser rejeitada
        
        Cenário: Header presente mas com JSON inválido
        Esperado: HTTP 400 Bad Request
        Validar: Validação rigorosa do formato de telemetria
        """
        valid_token = BradaxTestFixtures.get_valid_project_token()
        
        request_data = {
            "model": "gpt-4.1-nano", 
            "messages": [{"role": "user", "content": "Test with invalid telemetry"}],
            "max_tokens": 50
        }
        
        headers = {
            "Authorization": f"Bearer {valid_token}",
            "Content-Type": "application/json",
            "X-Bradax-Telemetry": "invalid-json-format"  # JSON inválido
        }
        
        response = client.post("/llm/invoke", json=request_data, headers=headers)
        
        # Deve ser 400 (bad request por formato inválido)
        assert response.status_code == 400, \
            f"Telemetria inválida deveria retornar 400: {response.status_code}"
        
        print(f"✅ Telemetria inválida rejeitada: {response.status_code}")


# Executar testes se rodado diretamente
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
