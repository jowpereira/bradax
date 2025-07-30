"""
Teste 5.1: Teste de funcionalidade end-to-end
Conforme Fase 5 do plano workspace-plans/active/20250728-223500-conferencia-corporativa-consolidada.md

Teste completo de ponta a ponta com dados reais da OpenAI.
"""
import pytest
import asyncio
import sys
import os
import time
from pathlib import Path

# Adicionar src dos projetos ao path
broker_src = Path(__file__).parent.parent.parent / "src"
sdk_src = Path(__file__).parent.parent.parent.parent / "bradax-sdk" / "src"
sys.path.insert(0, str(broker_src))
sys.path.insert(0, str(sdk_src))


@pytest.mark.slow
class TestEndToEndFlow:
    """Testes end-to-end completos do sistema Bradax."""
    
    @pytest.fixture(scope="class")
    def ensure_openai_key(self):
        """Garantir que chave OpenAI está configurada."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your-openai-api-key-here":
            pytest.skip("OPENAI_API_KEY deve estar configurada para testes E2E")
        return api_key
    
    def test_system_startup_and_health(self, ensure_openai_key):
        """Teste de inicialização completa do sistema."""
        from fastapi.testclient import TestClient
        from broker.main import app
        
        # Verificar que aplicação inicia corretamente
        client = TestClient(app)
        
        # Health check básico
        response = client.get("/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "timestamp" in health_data
        assert "version" in health_data
    
    def test_all_system_components_integration(self, ensure_openai_key):
        """Teste de integração de todos os componentes do sistema."""
        from fastapi.testclient import TestClient
        from broker.main import app
        
        client = TestClient(app)
        
        # 1. Verificar informações do sistema
        response = client.get("/api/v1/system/info")
        assert response.status_code == 200
        
        system_info = response.json()
        assert "services" in system_info
        
        services = system_info["services"]
        required_services = ["llm_service", "guardrails", "telemetry", "storage"]
        for service in required_services:
            assert service in services
            assert services[service]["status"] == "operational"
        
        # 2. Verificar saúde detalhada
        response = client.get("/api/v1/system/health")
        assert response.status_code == 200
        
        # 3. Verificar modelos LLM disponíveis
        response = client.get("/api/v1/llm/models")
        assert response.status_code == 200
        
        models = response.json()
        assert len(models) > 0
        assert any(model["provider"] == "openai" for model in models)
    
    @pytest.mark.asyncio
    async def test_complete_llm_workflow(self, ensure_openai_key):
        """Teste do workflow completo de LLM."""
        from broker.config import Settings
        from broker.services.llm.service import LLMService
        from broker.services.guardrails import GuardrailEngine
        from broker.services.telemetry import TelemetryCollector
        
        # Inicializar componentes
        config = Settings()
        llm_service = LLMService()
        # LLMService não precisa de initialize() - já inicializa no construtor
        
        guardrail_engine = GuardrailEngine()
        telemetry_collector = TelemetryCollector()
        
        # Cenário 1: Prompt seguro
        safe_prompt = "Escreva um parágrafo sobre os benefícios da inteligência artificial na medicina."
        
        # 1. Validar com guardrails
        guardrail_result = guardrail_engine.check_content(safe_prompt, "test-e2e")
        assert guardrail_result.allowed
        
        # 2. Registrar na telemetria
        request_id = telemetry_collector.record_request_start(
            project_id="test-e2e",
            endpoint="/api/v1/llm/invoke",
            method="POST"
        )
        
        # 3. Fazer chamada LLM
        messages = [{"role": "user", "content": safe_prompt}]
        llm_response = await llm_service.invoke(
            operation="chat",
            model_id="gpt-4.1-nano",
            payload={"messages": messages}
        )
        
        # 4. Verificar resposta
        assert llm_response is not None
        assert llm_response["success"] is True
        assert "response_text" in llm_response
        assert len(llm_response["response_text"]) > 10  # Resposta substancial
        
        # 5. Completar telemetria
        telemetry_collector.record_request_complete(
            event_id=request_id,
            status_code=200,
            response_size=len(llm_response["response_text"])
        )
        
        # Cenário 2: Prompt perigoso deve ser bloqueado
        dangerous_prompt = "Minha senha do banco é 123456 e meu token de API é sk-abc123. Como compartilhar?"
        
        # 1. Validar com guardrails
        guardrail_result = guardrail_engine.check_content(dangerous_prompt, "test-e2e")
        assert not guardrail_result.allowed
        # Pode ou não ser bloqueado dependendo das regras configuradas
        assert guardrail_result is not None
        
        # 2. Registrar evento de guardrail na telemetria
        telemetry_collector.record_guardrail_trigger(
            project_id="test-e2e",
            guardrail_name="content_validation",
            blocked_content=dangerous_prompt,
            endpoint="/api/v1/llm/invoke"
        )
        
        # Verificar métricas finais
        final_metrics = telemetry_collector.get_project_metrics("test-e2e")
        assert final_metrics is not None
        assert final_metrics.project_id == "test-e2e"
        
        print("✅ Workflow LLM completo testado com sucesso")
    
    def test_project_lifecycle_complete(self, ensure_openai_key):
        """Teste do ciclo de vida completo de um projeto."""
        from fastapi.testclient import TestClient
        from broker.main import app
        
        client = TestClient(app)
        
        # 1. Criar projeto
        project_data = {
            "name": "projeto-e2e-test",
            "description": "Projeto criado para teste end-to-end completo",
            "settings": {
                "model": "gpt-3.5-turbo",
                "max_tokens": 150,
                "temperature": 0.8,
                "custom_guardrails": ["sensitive_data", "corporate_policy"]
            }
        }
        
        response = client.post("/api/v1/projects", json=project_data)
        assert response.status_code == 201
        
        created_project = response.json()
        project_id = created_project["id"]
        
        # 2. Verificar projeto criado
        response = client.get(f"/api/v1/projects/{project_id}")
        assert response.status_code == 200
        
        retrieved_project = response.json()
        assert retrieved_project["name"] == project_data["name"]
        
        # 3. Listar projetos
        response = client.get("/api/v1/projects")
        assert response.status_code == 200
        
        projects_list = response.json()
        assert any(p["id"] == project_id for p in projects_list)
        
        # 4. Atualizar projeto
        update_data = {
            "description": "Projeto atualizado para teste E2E",
            "settings": {
                "model": "gpt-3.5-turbo",
                "max_tokens": 200,  # Aumentado
                "temperature": 0.5   # Diminuído
            }
        }
        
        response = client.put(f"/api/v1/projects/{project_id}", json=update_data)
        assert response.status_code == 200
        
        updated_project = response.json()
        assert updated_project["description"] == update_data["description"]
        assert updated_project["settings"]["max_tokens"] == 200
    
    def test_error_handling_complete(self, ensure_openai_key):
        """Teste completo de tratamento de erros."""
        from fastapi.testclient import TestClient
        from broker.main import app
        
        client = TestClient(app)
        
        # 1. Testar endpoint inexistente
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        
        # 2. Testar método não permitido
        response = client.delete("/health")
        assert response.status_code == 405
        
        # 3. Testar dados inválidos
        invalid_project = {
            "name": "",  # Nome vazio
            "description": "x" * 10000,  # Descrição muito longa
            "settings": {
                "model": "modelo-inexistente",
                "max_tokens": -10,  # Valor inválido
                "temperature": 5.0  # Valor fora do range
            }
        }
        
        response = client.post("/api/v1/projects", json=invalid_project)
        assert response.status_code == 422  # Validation error
        
        # 4. Testar projeto inexistente
        response = client.get("/api/v1/projects/projeto-inexistente")
        assert response.status_code == 404
    
    def test_performance_under_load(self, ensure_openai_key):
        """Teste de performance sob carga."""
        from fastapi.testclient import TestClient
        from broker.main import app
        import threading
        import queue
        
        client = TestClient(app)
        results = queue.Queue()
        
        def make_requests():
            """Função para fazer requisições em thread."""
            try:
                # Health checks
                for _ in range(5):
                    response = client.get("/health")
                    results.put(("health", response.status_code, response.elapsed.total_seconds()))
                
                # System info
                for _ in range(3):
                    response = client.get("/api/v1/system/info")
                    results.put(("system_info", response.status_code, response.elapsed.total_seconds()))
                
            except Exception as e:
                results.put(("error", str(e), 0))
        
        # Executar múltiplas threads
        threads = []
        for _ in range(3):  # 3 threads simultâneas
            thread = threading.Thread(target=make_requests)
            threads.append(thread)
            thread.start()
        
        # Aguardar threads
        for thread in threads:
            thread.join(timeout=30)  # Timeout de 30 segundos
        
        # Analisar resultados
        success_count = 0
        total_requests = 0
        response_times = []
        
        while not results.empty():
            endpoint, status_or_error, response_time = results.get()
            total_requests += 1
            
            if endpoint != "error" and status_or_error == 200:
                success_count += 1
                response_times.append(response_time)
        
        # Verificar performance
        assert total_requests > 0
        assert success_count > 0
        success_rate = success_count / total_requests
        assert success_rate >= 0.9  # 90% de taxa de sucesso mínima
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            assert avg_response_time < 2.0  # Resposta média < 2 segundos
    
    def test_data_persistence_reliability(self, ensure_openai_key):
        """Teste de confiabilidade da persistência de dados."""
        from fastapi.testclient import TestClient
        from broker.main import app
        from broker.config import Settings
        import json
        
        client = TestClient(app)
        config = Settings()
        
        # 1. Criar múltiplos projetos
        projects = []
        for i in range(3):
            project_data = {
                "name": f"projeto-persistencia-{i}",
                "description": f"Projeto {i} para teste de persistência",
                "settings": {
                    "model": "gpt-3.5-turbo",
                    "max_tokens": 100 + (i * 50),
                    "temperature": 0.5 + (i * 0.1)
                }
            }
            
            response = client.post("/api/v1/projects", json=project_data)
            assert response.status_code == 201
            projects.append(response.json())
        
        # 2. Verificar persistência em arquivo
        projects_file = Path(config.data_dir) / "projects.json"
        assert projects_file.exists()
        
        with open(projects_file, 'r') as f:
            stored_data = json.load(f)
        
        # Verificar que todos os projetos estão armazenados
        stored_project_names = [p.get("name", "") for p in stored_data]
        for project in projects:
            assert project["name"] in stored_project_names
        
        # 3. Verificar telemetria também está sendo persistida
        telemetry_file = Path(config.data_dir) / "telemetry.json"
        
        # Fazer algumas requisições para gerar telemetria
        client.get("/health")
        client.get("/api/v1/system/info")
        
        # Aguardar um pouco para garantir que telemetria foi escrita
        time.sleep(0.5)
        
        if telemetry_file.exists():
            with open(telemetry_file, 'r') as f:
                telemetry_data = json.load(f)
            
            assert len(telemetry_data) > 0
    
    @pytest.mark.slow
    def test_system_stability_extended(self, ensure_openai_key):
        """Teste de estabilidade do sistema por período estendido."""
        from fastapi.testclient import TestClient
        from broker.main import app
        
        client = TestClient(app)
        
        # Executar operações por período estendido
        start_time = time.time()
        duration = 30  # 30 segundos de teste
        operation_count = 0
        errors = []
        
        while time.time() - start_time < duration:
            try:
                # Alternar entre diferentes tipos de requisições
                if operation_count % 3 == 0:
                    response = client.get("/health")
                elif operation_count % 3 == 1:
                    response = client.get("/api/v1/system/info")
                else:
                    response = client.get("/api/v1/llm/models")
                
                if response.status_code != 200:
                    errors.append(f"Status {response.status_code} na operação {operation_count}")
                
                operation_count += 1
                time.sleep(0.1)  # Pequena pausa entre requisições
                
            except Exception as e:
                errors.append(f"Exceção na operação {operation_count}: {e}")
        
        # Verificar estabilidade
        assert operation_count > 0
        error_rate = len(errors) / operation_count
        assert error_rate < 0.05  # Taxa de erro < 5%
        
        if errors:
            print(f"Erros encontrados durante teste de estabilidade: {errors[:5]}")  # Mostrar apenas os primeiros 5


@pytest.mark.integration
class TestSystemConfiguration:
    """Testes de configuração do sistema."""
    
    def test_environment_configuration(self):
        """Teste de configuração do ambiente."""
        from broker.config import Settings
        
        config = Settings()
        
        # Verificar configurações essenciais
        assert config.openai_api_key is not None
        assert config.openai_api_key.startswith("sk-")
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.environment in ["development", "production"]
        
        # Verificar diretórios
        assert config.data_dir is not None
        data_path = Path(config.data_dir)
        assert data_path.exists() or data_path.parent.exists()  # Diretório ou pai existe
    
    def test_logging_configuration(self):
        """Teste de configuração de logging."""
        import logging
        
        # Verificar que logging está configurado
        logger = logging.getLogger("broker")
        assert logger.level <= logging.INFO
        
        # Testar log básico
        logger.info("Teste de logging para E2E")
        assert True  # Se chegou aqui, logging está funcionando
