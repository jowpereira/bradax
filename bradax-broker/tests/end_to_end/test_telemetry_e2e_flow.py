"""
Teste End-to-End - SDK to Broker Telemetry Flow

Valida o fluxo completo de telemetria entre SDK e Broker:
- SDK intercepta requests antes do envio
- Broker salva responses após LLM
- Correlação correta via request_id
- Integridade dos dados em ambos os lados

Autor: Sistema de Telemetria Bradax  
Data: 2025-07-31
Fase: Phase 3 - Instrumentação Full-Stack (Saída)
"""

import pytest
import json
import os
import uuid
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

# Setup paths para imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "bradax-sdk" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestSDKBrokerTelemetryFlow:
    """Testes end-to-end para fluxo SDK → Broker"""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup do ambiente de teste"""
        # Configurar ambiente
        os.environ['BRADAX_PROJECT_TOKEN'] = 'test-e2e-token'
        
        # Garantir diretórios de telemetria
        self.data_dir = Path(__file__).parent.parent.parent.parent.parent / "data"
        self.requests_dir = self.data_dir / "raw" / "requests"  
        self.responses_dir = self.data_dir / "raw" / "responses"
        
        self.requests_dir.mkdir(parents=True, exist_ok=True)
        self.responses_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivos de teste para cleanup
        self.test_files = []
        
        yield
        
        # Cleanup
        for file_path in self.test_files:
            if os.path.exists(file_path):
                os.remove(file_path)
    
    def test_sdk_telemetry_interceptor_initialization(self):
        """Testa se o interceptor é inicializado corretamente no SDK"""
        # Arrange & Act
        try:
            from bradax.client import BradaxClient
            from bradax.telemetry_interceptor import TelemetryInterceptor
            
            client = BradaxClient(broker_url="http://localhost:8000")
            
            # Assert
            assert hasattr(client, 'telemetry_interceptor')
            assert isinstance(client.telemetry_interceptor, TelemetryInterceptor)
            
        except ImportError as e:
            pytest.skip(f"SDK imports não disponíveis: {e}")
    
    def test_telemetry_interceptor_capture_request(self):
        """Testa captura de request pelo interceptor do SDK"""
        # Arrange
        try:
            from bradax.telemetry_interceptor import TelemetryInterceptor
            
            interceptor = TelemetryInterceptor()
            
            test_input = "Test prompt for E2E validation"
            test_config = {"model": "gpt-4", "temperature": 0.7}
            test_payload = {
                "operation": "chat",
                "model": "gpt-4", 
                "payload": {
                    "messages": [{"role": "user", "content": test_input}],
                    "temperature": 0.7
                }
            }
            test_kwargs = {"max_tokens": 1000}
            
            # Act
            request_data = interceptor.intercept_request(
                input_data=test_input,
                config=test_config,
                payload=test_payload,
                kwargs=test_kwargs
            )
            
            # Assert
            assert "request_id" in request_data
            assert "timestamp" in request_data
            assert request_data["input_data"] == test_input
            assert request_data["config"]["model"] == "gpt-4"
            assert request_data["payload"]["operation"] == "chat"
            
            # Verificar se arquivo foi salvo
            request_file = self.requests_dir / f"{request_data['request_id']}.json"
            self.test_files.append(str(request_file))
            
            assert request_file.exists()
            
            # Verificar conteúdo do arquivo
            with open(request_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                
            assert saved_data["request_id"] == request_data["request_id"]
            assert saved_data["input_data"] == test_input
            
        except ImportError as e:
            pytest.skip(f"SDK imports não disponíveis: {e}")
    
    def test_broker_telemetry_save_response(self):
        """Testa salvamento de response pelo broker"""
        # Arrange
        try:
            from broker.services.telemetry_raw import save_raw_response
            
            test_request_id = str(uuid.uuid4())
            response_data = {
                "request_id": test_request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "provider": "openai",
                "model": "gpt-4",
                "response_text": "Test response from E2E validation",
                "processing_time_ms": 250,
                "input_tokens": 10,
                "output_tokens": 15,
                "success": True,
                "metadata": {
                    "guardrails_applied_pre": 0,
                    "project_id": "test-e2e-project",
                    "test_mode": True
                }
            }
            
            # Act
            file_path = save_raw_response(test_request_id, response_data)
            self.test_files.append(file_path)
            
            # Assert
            assert os.path.exists(file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                
            assert saved_data["request_id"] == test_request_id
            assert saved_data["response_text"] == "Test response from E2E validation"
            assert saved_data["success"] is True
            assert saved_data["processing_time_ms"] == 250
            
        except ImportError as e:
            pytest.skip(f"Broker imports não disponíveis: {e}")
    
    def test_full_request_response_correlation_flow(self):
        """Testa correlação completa request-response via UUID compartilhado"""
        # Arrange
        try:
            from bradax.telemetry_interceptor import TelemetryInterceptor
            from broker.services.telemetry_raw import save_raw_response, load_raw_request, load_raw_response
            
            interceptor = TelemetryInterceptor()
            
            # Simular request do SDK
            test_input = "Full flow correlation test"
            test_config = {"model": "gpt-4"}
            test_payload = {
                "operation": "chat",
                "model": "gpt-4",
                "payload": {"messages": [{"role": "user", "content": test_input}]}
            }
            
            # Act - Parte 1: Interceptar request (SDK)
            request_data = interceptor.intercept_request(
                input_data=test_input,
                config=test_config, 
                payload=test_payload,
                kwargs={}
            )
            
            request_id = request_data["request_id"]
            
            # Act - Parte 2: Simular response do broker
            response_data = {
                "request_id": request_id,  # Usar mesmo UUID
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "provider": "openai",
                "model": "gpt-4",
                "response_text": "Full flow correlation response",
                "processing_time_ms": 180,
                "success": True,
                "metadata": {
                    "correlation_test": True,
                    "request_correlation": True
                }
            }
            
            response_file = save_raw_response(request_id, response_data)
            
            # Adicionar arquivos para cleanup
            request_file = self.requests_dir / f"{request_id}.json"
            self.test_files.extend([str(request_file), response_file])
            
            # Act - Parte 3: Carregar ambos os dados
            loaded_request = load_raw_request(request_id)
            loaded_response = load_raw_response(request_id)
            
            # Assert - Correlação perfeita
            assert loaded_request["request_id"] == loaded_response["request_id"]
            assert loaded_request["input_data"] == test_input
            assert loaded_response["response_text"] == "Full flow correlation response"
            
            # Assert - Timestamps devem ser cronológicos
            request_time = datetime.fromisoformat(loaded_request["timestamp"].replace('Z', '+00:00'))
            response_time = datetime.fromisoformat(loaded_response["timestamp"].replace('Z', '+00:00'))
            assert request_time <= response_time
            
            # Assert - Metadados de correlação
            assert loaded_response["metadata"]["correlation_test"] is True
            
        except ImportError as e:
            pytest.skip(f"Imports não disponíveis: {e}")
    
    @pytest.mark.asyncio
    async def test_async_telemetry_flow(self):
        """Testa fluxo de telemetria assíncrono"""
        # Arrange
        try:
            from bradax.telemetry_interceptor import TelemetryInterceptor
            
            interceptor = TelemetryInterceptor()
            
            test_input = "Async telemetry test"
            test_config = {"model": "gpt-4"}
            test_payload = {
                "operation": "chat",
                "model": "gpt-4",
                "payload": {"messages": [{"role": "user", "content": test_input}]}
            }
            
            # Act
            request_data = interceptor.intercept_request(
                input_data=test_input,
                config=test_config,
                payload=test_payload,
                kwargs={},
                is_async=True  # Marcar como async
            )
            
            # Assert
            assert request_data["metadata"]["is_async"] is True
            assert "request_id" in request_data
            
            # Verificar arquivo foi salvo
            request_file = self.requests_dir / f"{request_data['request_id']}.json"
            self.test_files.append(str(request_file))
            
            assert request_file.exists()
            
        except ImportError as e:
            pytest.skip(f"SDK imports não disponíveis: {e}")
    
    def test_telemetry_error_handling(self):
        """Testa tratamento de erros na telemetria"""
        # Arrange
        try:
            from broker.services.telemetry_raw import save_raw_response
            
            test_request_id = str(uuid.uuid4())
            
            # Simular erro de processamento
            error_response_data = {
                "request_id": test_request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "provider": "error",
                "model": "gpt-4",
                "error": "Test connection timeout",
                "processing_time_ms": 5000,
                "success": False,
                "metadata": {
                    "error_type": "ConnectionError",
                    "test_error": True
                }
            }
            
            # Act
            file_path = save_raw_response(test_request_id, error_response_data)
            self.test_files.append(file_path)
            
            # Assert
            assert os.path.exists(file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                
            assert saved_data["success"] is False
            assert saved_data["error"] == "Test connection timeout"
            assert saved_data["metadata"]["error_type"] == "ConnectionError"
            
        except ImportError as e:
            pytest.skip(f"Broker imports não disponíveis: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
