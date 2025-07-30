"""
Teste 4.1: Testes de endpoints - funcionalidade e validações
Conforme Fase 4 do plano workspace-plans/active/20250728-223500-conferencia-corporativa-consolidada.md

Testa funcionalidades básicas dos endpoints com dados reais da OpenAI.
"""
import pytest
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Adicionar src ao path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from broker.main import app


class TestEndpoints:
    """Testes dos endpoints principais do broker."""
    
    @pytest.fixture(scope="class")
    def client(self):
        """Cliente de teste para a aplicação."""
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Teste do endpoint de health check."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_system_info_endpoint(self, client):
        """Teste do endpoint de informações do sistema."""
        response = client.get("/api/v1/system/status")  # Rota real que existe
        assert response.status_code == 200
        
        data = response.json()
        # Ajustar campos para a resposta real do endpoint /status
        assert "data" in data
        assert "success" in data
        assert data["success"] == True
        
        # Verificar estrutura interna dos dados
        service_data = data["data"]
        assert "services" in service_data
        assert "timestamp" in service_data
    
    def test_system_health_endpoint(self, client):
        """Teste do endpoint de health do sistema."""
        response = client.get("/api/v1/system/health")
        assert response.status_code == 200
        
        data = response.json()
        # Ajustar para estrutura real: data.status em vez de status direto
        assert "data" in data
        assert "success" in data
        assert data["success"] == True
        
        # Verificar estrutura interna dos dados de health
        health_data = data["data"]
        assert "status" in health_data
        assert "components" in health_data
        assert "timestamp" in health_data
    
    def test_projects_list_endpoint(self, client):
        """Teste do endpoint de listagem de projetos."""
        response = client.get("/api/v1/projects/")  # Rota completa correta
        assert response.status_code == 200
        
        # A rota retorna diretamente a lista de projetos, não wrapped
        data = response.json()
        assert isinstance(data, list)  # Lista de projetos
        # Pode estar vazia inicialmente, mas deve retornar lista
    
    def test_llm_models_endpoint(self, client):
        """Teste do endpoint de modelos LLM disponíveis."""
        response = client.get("/api/v1/llm/models")
        assert response.status_code == 200
        
        data = response.json()
        # Ajustar para estrutura real da resposta
        assert "data" in data
        assert "success" in data
        assert data["success"] == True
        
        # Verificar estrutura dos modelos
        models_data = data["data"]
        assert "models" in models_data
        models = models_data["models"]
        assert isinstance(models, list)
        assert len(models) > 0
        
        # Verificar estrutura do modelo
        model = models[0]
        assert "model_id" in model
        assert "provider" in model
        assert "enabled" in model
    
    def test_openai_key_configured(self):
        """Verificar se a chave OpenAI está configurada."""
        openai_key = os.getenv("OPENAI_API_KEY")
        assert openai_key is not None, "OPENAI_API_KEY deve estar configurada no .env"
        assert openai_key != "your-openai-api-key-here", "OPENAI_API_KEY deve ser uma chave real"
        assert openai_key.startswith("sk-"), "OPENAI_API_KEY deve ter formato válido"
    
    def test_config_validation(self, client):
        """Teste de validação da configuração do sistema."""
        # Testar endpoint que valida configuração
        response = client.get("/api/v1/system/config")
        assert response.status_code == 200
        
        response_data = response.json()
        assert "data" in response_data
        assert "success" in response_data
        
        data = response_data["data"]
        assert "environment" in data
        assert "debug" in data
        
        # O sistema não retorna services_configured, mas tem features
        assert "features" in data
        features = data["features"]
        assert features["llm_service"] is True, "LLM service deve estar configurado"


class TestDataPersistence:
    """Testes de persistência de dados."""
    
    @pytest.fixture(scope="class")
    def client(self):
        """Cliente de teste para a aplicação."""
        return TestClient(app)
    
    def test_project_creation_and_retrieval(self, client):
        """Teste de criação e recuperação de projeto."""
        # Dados do projeto de teste
        project_data = {
            "name": "projeto-teste-automated",
            "description": "Projeto criado automaticamente para testes",
            "settings": {
                "model": "gpt-4.1-nano",
                "max_tokens": 1000,
                "temperature": 0.7
            }
        }
        
        # Criar projeto
        response = client.post("/api/v1/projects", json=project_data)
        assert response.status_code == 201
        
        created_project = response.json()
        assert "id" in created_project
        assert created_project["name"] == project_data["name"]
        
        project_id = created_project["id"]
        
        # Recuperar projeto
        response = client.get(f"/api/v1/projects/{project_id}")
        assert response.status_code == 200
        
        retrieved_project = response.json()
        assert retrieved_project["id"] == project_id
        assert retrieved_project["name"] == project_data["name"]
        assert retrieved_project["settings"]["model"] == project_data["settings"]["model"]
    
    def test_telemetry_recording(self, client):
        """Teste de gravação de telemetria."""
        # Fazer algumas requisições que devem gerar telemetria
        client.get("/health")
        client.get("/api/v1/system/info")
        client.get("/api/v1/llm/models")
        
        # Verificar se telemetria foi gravada
        response = client.get("/api/v1/system/telemetry")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_requests" in data
        assert "endpoints_accessed" in data
        assert "system_metrics" in data
        
        # Deve ter pelo menos as requisições que fizemos
        assert data["total_requests"] >= 3
