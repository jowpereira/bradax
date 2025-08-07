"""
Testes de Integração - Telemetria Raw Flow

Valida o fluxo completo de telemetria raw:
- Interceptação no SDK
- Salvamento de requests/responses
- Correlação por UUID
- Integridade dos dados

Autor: Sistema de Telemetria Bradax
Data: 2025-07-31
"""

import pytest
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Setup paths para imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from broker.services.telemetry_raw import save_raw_request, save_raw_response, load_raw_request, load_raw_response
from broker.constants import HubStorageConstants


class TestTelemetryRawFlow:
    """Testes de integração para telemetria raw"""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup do ambiente de teste"""
        # Garantir que os diretórios existem
        os.makedirs(HubStorageConstants.RAW_REQUESTS_DIR, exist_ok=True)
        os.makedirs(HubStorageConstants.RAW_RESPONSES_DIR, exist_ok=True)
        
        # Gerar ID único para o teste
        self.test_request_id = str(uuid.uuid4())
        self.test_files = []
        
        yield
        
        # Cleanup: remover arquivos de teste
        for file_path in self.test_files:
            if os.path.exists(file_path):
                os.remove(file_path)
    
    def test_save_and_load_raw_request(self):
        """Testa salvamento e carregamento de request raw"""
        # Arrange
        request_data = {
            "request_id": self.test_request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_data": "Test prompt for telemetry",
            "config": {"model": "gpt-4", "temperature": 0.7},
            "payload": {
                "operation": "chat",
                "model": "gpt-4",
                "payload": {
                    "messages": [{"role": "user", "content": "test"}],
                    "temperature": 0.7
                }
            },
            "metadata": {
                "sdk_version": "1.0.0",
                "is_async": False
            }
        }
        
        # Act
        file_path = save_raw_request(self.test_request_id, request_data)
        self.test_files.append(file_path)
        
        loaded_data = load_raw_request(self.test_request_id)
        
        # Assert
        assert loaded_data is not None
        assert loaded_data["request_id"] == self.test_request_id
        assert loaded_data["input_data"] == "Test prompt for telemetry"
        assert loaded_data["config"]["model"] == "gpt-4"
        assert "timestamp" in loaded_data
        
    def test_save_and_load_raw_response(self):
        """Testa salvamento e carregamento de response raw"""
        # Arrange
        response_data = {
            "request_id": self.test_request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": "openai",
            "model": "gpt-4",
            "response_text": "Test response for telemetry validation",
            "processing_time_ms": 150,
            "input_tokens": 5,
            "output_tokens": 8,
            "success": True,
            "metadata": {
                "guardrails_applied_pre": 0,
                "project_id": "test-project",
                "test_mode": True
            }
        }
        
        # Act
        file_path = save_raw_response(self.test_request_id, response_data)
        self.test_files.append(file_path)
        
        loaded_data = load_raw_response(self.test_request_id)
        
        # Assert
        assert loaded_data is not None
        assert loaded_data["request_id"] == self.test_request_id
        assert loaded_data["response_text"] == "Test response for telemetry validation"
        assert loaded_data["success"] is True
        assert loaded_data["processing_time_ms"] == 150
        
    def test_request_response_correlation(self):
        """Testa correlação entre request e response via UUID"""
        # Arrange
        request_data = {
            "request_id": self.test_request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_data": "Correlation test prompt",
            "config": {"model": "gpt-4"}
        }
        
        response_data = {
            "request_id": self.test_request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": "openai",
            "response_text": "Correlation test response",
            "success": True
        }
        
        # Act
        request_file = save_raw_request(self.test_request_id, request_data)
        response_file = save_raw_response(self.test_request_id, response_data)
        
        self.test_files.extend([request_file, response_file])
        
        loaded_request = load_raw_request(self.test_request_id)
        loaded_response = load_raw_response(self.test_request_id)
        
        # Assert
        assert loaded_request["request_id"] == loaded_response["request_id"]
        assert loaded_request["input_data"] == "Correlation test prompt"
        assert loaded_response["response_text"] == "Correlation test response"
        
    def test_file_integrity_and_format(self):
        """Testa integridade e formato dos arquivos JSON"""
        # Arrange
        test_data = {
            "request_id": self.test_request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "test_unicode": "Teste com acentuação: ção, ñ, ü",
            "test_numbers": {"int": 42, "float": 3.14159},
            "test_nested": {
                "level1": {
                    "level2": ["item1", "item2", "item3"]
                }
            }
        }
        
        # Act
        file_path = save_raw_request(self.test_request_id, test_data)
        self.test_files.append(file_path)
        
        # Verificar se o arquivo foi criado
        assert os.path.exists(file_path)
        
        # Verificar se é JSON válido
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
            parsed_data = json.loads(raw_content)
        
        loaded_data = load_raw_request(self.test_request_id)
        
        # Assert
        assert loaded_data["test_unicode"] == "Teste com acentuação: ção, ñ, ü"
        assert loaded_data["test_numbers"]["int"] == 42
        assert loaded_data["test_numbers"]["float"] == 3.14159
        assert loaded_data["test_nested"]["level1"]["level2"] == ["item1", "item2", "item3"]
        
    def test_error_handling_invalid_uuid(self):
        """Testa tratamento de erro para UUID inválido"""
        # Act & Assert
        with pytest.raises((FileNotFoundError, ValueError)):
            load_raw_request("invalid-uuid-format")
            
        with pytest.raises((FileNotFoundError, ValueError)):
            load_raw_response("invalid-uuid-format")
            
    def test_performance_large_payload(self):
        """Testa performance com payload grande"""
        # Arrange
        large_text = "Large payload test " * 1000  # ~19KB
        large_data = {
            "request_id": self.test_request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "large_payload": large_text,
            "metadata": {
                "size_test": True,
                "estimated_size_kb": len(large_text) / 1024
            }
        }
        
        # Act
        import time
        start_time = time.time()
        
        file_path = save_raw_request(self.test_request_id, large_data)
        save_time = time.time() - start_time
        
        start_time = time.time()
        loaded_data = load_raw_request(self.test_request_id)
        load_time = time.time() - start_time
        
        self.test_files.append(file_path)
        
        # Assert
        assert loaded_data["large_payload"] == large_text
        assert save_time < 1.0  # Deve salvar em menos de 1 segundo
        assert load_time < 1.0  # Deve carregar em menos de 1 segundo
        
        
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
