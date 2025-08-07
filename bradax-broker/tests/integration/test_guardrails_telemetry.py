"""
Teste de Integração - Guardrails com Telemetria

Valida o funcionamento dos guardrails de entrada e saída
com telemetria raw completa conforme Phase 4-5.

Autor: Sistema de Telemetria Bradax
Data: 2025-07-31  
Fase: Phase 4 - Guardrails de Entrada
"""

import pytest
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

# Setup paths para imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from broker.services.telemetry_raw import save_guardrail_violation, load_raw_response


class TestGuardrailsWithTelemetry:
    """Testes de integração para guardrails com telemetria"""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup do ambiente de teste"""
        # Configurar ambiente
        os.environ['BRADAX_PROJECT_TOKEN'] = 'test-guardrails-token'
        
        # Garantir diretórios de telemetria
        self.data_dir = Path(__file__).parent.parent.parent / "data"  # bradax-broker/data/
        self.responses_dir = self.data_dir / "raw" / "responses"
        
        self.responses_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivos de teste para cleanup
        self.test_files = []
        
        yield
        
        # Cleanup
        for file_path in self.test_files:
            if os.path.exists(file_path):
                os.remove(file_path)
    
    def test_guardrail_violation_input_telemetry(self):
        """Testa salvamento de violação de guardrail de entrada"""
        # Arrange
        test_request_id = str(uuid.uuid4())
        blocked_content = "Este é um prompt que contém informações confidenciais de CPF: 123.456.789-00"
        rule_name = "pii_detection"
        
        # Act
        success = save_guardrail_violation(
            request_id=test_request_id,
            violation_type="input_validation",
            content_blocked=blocked_content,
            rule_triggered=rule_name,
            stage="input",
            project_id="test-project-guardrails",
            metadata={
                "rule_details": {
                    "name": rule_name,
                    "type": "pii_detection",
                    "action": "block"
                },
                "detected_pii": ["cpf"],
                "confidence": 0.95
            }
        )
        
        # Assert
        assert success is True
        
        # Verificar arquivo foi criado
        violation_file = self.responses_dir / f"{test_request_id}.json"
        self.test_files.append(str(violation_file))
        
        assert violation_file.exists()
        
        # Verificar conteúdo do arquivo
        with open(violation_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert saved_data["request_id"] == test_request_id
        assert saved_data["event_type"] == "guardrail_violation"
        assert saved_data["violation_type"] == "input_validation"
        assert saved_data["stage"] == "input"
        assert saved_data["rule_triggered"] == rule_name
        assert saved_data["status_code"] == 403
        assert "CPF" in saved_data["content_blocked"]  # Verificar que o CPF está no conteúdo
        assert saved_data["metadata"]["detected_pii"] == ["cpf"]
    
    def test_guardrail_violation_output_telemetry(self):
        """Testa salvamento de violação de guardrail de saída"""
        # Arrange
        test_request_id = str(uuid.uuid4())
        blocked_content = "Resposta com conteúdo inadequado que deveria ser bloqueado"
        rule_name = "content_filter"
        
        # Act
        success = save_guardrail_violation(
            request_id=test_request_id,
            violation_type="output_validation", 
            content_blocked=blocked_content,
            rule_triggered=rule_name,
            stage="output",
            project_id="test-project-output",
            metadata={
                "rule_details": {
                    "name": rule_name,
                    "type": "content_safety",
                    "action": "sanitize"
                },
                "content_category": "inappropriate",
                "severity": "medium"
            }
        )
        
        # Assert
        assert success is True
        
        # Verificar arquivo foi criado
        violation_file = self.responses_dir / f"{test_request_id}.json"
        self.test_files.append(str(violation_file))
        
        assert violation_file.exists()
        
        # Verificar conteúdo do arquivo
        with open(violation_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert saved_data["request_id"] == test_request_id
        assert saved_data["event_type"] == "guardrail_violation"
        assert saved_data["violation_type"] == "output_validation"
        assert saved_data["stage"] == "output"
        assert saved_data["rule_triggered"] == rule_name
        assert saved_data["metadata"]["content_category"] == "inappropriate"
    
    def test_guardrail_violation_large_content_truncation(self):
        """Testa truncamento de conteúdo grande em violações"""
        # Arrange
        test_request_id = str(uuid.uuid4())
        large_content = "Conteúdo muito grande para teste " * 100  # ~3300 chars
        rule_name = "size_limit"
        
        # Act
        success = save_guardrail_violation(
            request_id=test_request_id,
            violation_type="input_validation",
            content_blocked=large_content,
            rule_triggered=rule_name,
            stage="input",
            project_id="test-project-size",
            metadata={"original_size": len(large_content)}
        )
        
        # Assert
        assert success is True
        
        # Verificar arquivo foi criado
        violation_file = self.responses_dir / f"{test_request_id}.json"
        self.test_files.append(str(violation_file))
        
        # Verificar conteúdo do arquivo
        with open(violation_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        # Verificar truncamento para 500 caracteres
        assert len(saved_data["content_blocked"]) <= 500
        assert saved_data["metadata"]["original_size"] == len(large_content)
    
    def test_load_guardrail_violation_data(self):
        """Testa carregamento de dados de violação de guardrail"""
        # Arrange
        test_request_id = str(uuid.uuid4())
        
        # Salvar violação primeiro
        save_guardrail_violation(
            request_id=test_request_id,
            violation_type="input_validation",
            content_blocked="Teste de carregamento",
            rule_triggered="test_rule",
            stage="input",
            project_id="test-project-load"
        )
        
        violation_file = self.responses_dir / f"{test_request_id}.json"
        self.test_files.append(str(violation_file))
        
        # Act
        loaded_data = load_raw_response(test_request_id)
        
        # Assert
        assert loaded_data is not None
        assert loaded_data["request_id"] == test_request_id
        assert loaded_data["event_type"] == "guardrail_violation"
        assert loaded_data["rule_triggered"] == "test_rule"
        assert "timestamp" in loaded_data
    
    def test_guardrail_violation_different_stages(self):
        """Testa violações em diferentes estágios (input vs output)"""
        # Arrange
        input_request_id = str(uuid.uuid4())
        output_request_id = str(uuid.uuid4())
        
        # Act - Violação de entrada
        save_guardrail_violation(
            request_id=input_request_id,
            violation_type="input_validation",
            content_blocked="Input bloqueado",
            rule_triggered="input_rule",
            stage="input",
            project_id="test-project-stages"
        )
        
        # Act - Violação de saída
        save_guardrail_violation(
            request_id=output_request_id,
            violation_type="output_validation", 
            content_blocked="Output modificado",
            rule_triggered="output_rule",
            stage="output",
            project_id="test-project-stages"
        )
        
        # Adicionar arquivos para cleanup
        input_file = self.responses_dir / f"{input_request_id}.json"
        output_file = self.responses_dir / f"{output_request_id}.json"
        self.test_files.extend([str(input_file), str(output_file)])
        
        # Assert - Verificar diferenças entre estágios
        input_data = load_raw_response(input_request_id)
        output_data = load_raw_response(output_request_id)
        
        assert input_data["stage"] == "input"
        assert output_data["stage"] == "output"
        assert input_data["rule_triggered"] == "input_rule"
        assert output_data["rule_triggered"] == "output_rule"
    
    def test_guardrail_violation_metadata_preservation(self):
        """Testa preservação de metadados complexos"""
        # Arrange
        test_request_id = str(uuid.uuid4())
        complex_metadata = {
            "detection_details": {
                "patterns_matched": ["pattern1", "pattern2"],
                "confidence_scores": [0.95, 0.87],
                "model_version": "v1.2.3"
            },
            "user_context": {
                "user_id": "user123",
                "session_id": "session456",
                "request_count": 5
            },
            "timing": {
                "detection_time_ms": 45,
                "processing_started": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Act
        save_guardrail_violation(
            request_id=test_request_id,
            violation_type="input_validation",
            content_blocked="Conteúdo com metadados complexos",
            rule_triggered="complex_rule",
            stage="input",
            project_id="test-project-metadata",
            metadata=complex_metadata
        )
        
        # Adicionar arquivo para cleanup
        violation_file = self.responses_dir / f"{test_request_id}.json"
        self.test_files.append(str(violation_file))
        
        # Act - Carregar dados
        loaded_data = load_raw_response(test_request_id)
        
        # Assert - Verificar preservação de metadados
        assert loaded_data["metadata"]["detection_details"]["model_version"] == "v1.2.3"
        assert loaded_data["metadata"]["user_context"]["user_id"] == "user123"
        assert loaded_data["metadata"]["timing"]["detection_time_ms"] == 45
        assert len(loaded_data["metadata"]["detection_details"]["patterns_matched"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
