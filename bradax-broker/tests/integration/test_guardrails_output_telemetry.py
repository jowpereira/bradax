"""
Teste de Integração: Guardrails de Saída com Telemetria
========================================================

Valida que violações de guardrails de saída são detectadas, 
telemetria é capturada e respostas são sanitizadas adequadamente.

ESTRUTURA PROFISSIONAL: /tests/integration/
"""

import pytest
import json
import asyncio
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# Adicionar src ao path para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from broker.services.llm.service import LLMService, GuardrailViolationError
from broker.services.telemetry_raw import load_guardrail_violation


class TestGuardrailsOutputTelemetry:
    """Testes de guardrails de saída com telemetria completa"""

    @pytest.fixture
    def llm_service(self):
        """Fixture com LLMService configurado para testes"""
        service = LLMService()
        
        # Mock repositories
        service.project_repo = AsyncMock()
        service.telemetry_repo = AsyncMock() 
        service.guardrail_repo = AsyncMock()
        
        return service

    @pytest.fixture
    def mock_project_with_output_rules(self):
        """Fixture com projeto configurado com regras de saída"""
        project = MagicMock()
        project.config = {
            "guardrails": {
                "output_validation": {
                    "rules": [
                        {
                            "name": "block_sensitive_data",
                            "type": "keyword",
                            "action": "reject",
                            "keywords": ["senha", "password", "123456789"]
                        },
                        {
                            "name": "block_pii_output",
                            "type": "regex", 
                            "action": "reject",
                            "pattern": r"\d{3}\.\d{3}\.\d{3}-\d{2}"  # CPF pattern
                        },
                        {
                            "name": "block_inappropriate_content",
                            "type": "keyword",
                            "action": "reject",
                            "keywords": ["conteúdo inadequado", "informação proibida"]
                        }
                    ]
                }
            }
        }
        return project

    @pytest.mark.asyncio
    async def test_output_violation_password_detection_telemetry(self, llm_service, mock_project_with_output_rules):
        """Testa detecção de senha em resposta com telemetria completa"""
        
        # Setup
        request_id = str(uuid.uuid4())
        project_id = "test_project"
        output_with_password = "Sua senha temporária é: senha123. Use com cuidado."
        
        # Mock project repository
        llm_service.project_repo.get_by_id.return_value = mock_project_with_output_rules
        
        # Mock guardrail event logging
        llm_service._log_guardrail_event_async = AsyncMock()
        
        # Executar guardrails de saída
        result = await llm_service._apply_output_guardrails(
            project_id=project_id,
            output_text=output_with_password, 
            request_id=request_id
        )
        
        # Verificações
        # 1. Resposta foi sanitizada (não contém senha original)
        assert "senha123" not in result
        assert "não posso fornecer informações relacionadas a senhas" in result
        
        # 2. Verificar se violation foi salva
        violation_path = Path("data/raw/requests") / f"{request_id}.json"
        if violation_path.exists():
            violation_data = load_guardrail_violation(request_id)
            assert violation_data is not None
            assert violation_data["violation_type"] == "output_validation"
            assert violation_data["stage"] == "output"
            assert violation_data["rule_triggered"] == "block_sensitive_data"
            assert "senha" in violation_data["content_blocked"]
        
        # 3. Verificar se event async foi chamado
        llm_service._log_guardrail_event_async.assert_called_once()
        call_args = llm_service._log_guardrail_event_async.call_args[0]
        assert call_args[0] == project_id  # project_id
        assert call_args[1] == request_id  # request_id
        assert call_args[2] == "output_validation"  # event_type
        assert call_args[3] == "blocked"  # action

    @pytest.mark.asyncio
    async def test_output_violation_cpf_detection_telemetry(self, llm_service, mock_project_with_output_rules):
        """Testa detecção de CPF em resposta com telemetria"""
        
        # Setup
        request_id = str(uuid.uuid4())
        project_id = "test_project"
        output_with_cpf = "O CPF do usuário é 123.456.789-00. Verifique os dados."
        
        # Mock project repository
        llm_service.project_repo.get_by_id.return_value = mock_project_with_output_rules
        
        # Mock guardrail event logging
        llm_service._log_guardrail_event_async = AsyncMock()
        
        # Executar guardrails de saída
        result = await llm_service._apply_output_guardrails(
            project_id=project_id,
            output_text=output_with_cpf,
            request_id=request_id
        )
        
        # Verificações
        # 1. Resposta foi sanitizada (não contém CPF)
        assert "123.456.789-00" not in result
        assert "dados pessoais identificáveis" in result
        
        # 2. Event logging foi chamado
        llm_service._log_guardrail_event_async.assert_called_once()

    @pytest.mark.asyncio 
    async def test_output_no_violation_passthrough(self, llm_service, mock_project_with_output_rules):
        """Testa que resposta segura passa sem modificação"""
        
        # Setup
        request_id = str(uuid.uuid4())
        project_id = "test_project"
        safe_output = "Machine learning é uma área da inteligência artificial que permite sistemas aprenderem automaticamente."
        
        # Mock project repository
        llm_service.project_repo.get_by_id.return_value = mock_project_with_output_rules
        
        # Mock guardrail event logging
        llm_service._log_guardrail_event_async = AsyncMock()
        
        # Executar guardrails de saída
        result = await llm_service._apply_output_guardrails(
            project_id=project_id,
            output_text=safe_output,
            request_id=request_id
        )
        
        # Verificações
        # 1. Resposta não foi modificada
        assert result == safe_output
        
        # 2. Nenhum event logging foi chamado (sem violações)
        llm_service._log_guardrail_event_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_output_sanitization_metadata_preservation(self, llm_service, mock_project_with_output_rules):
        """Testa preservação de metadados durante sanitização"""
        
        # Setup
        request_id = str(uuid.uuid4())
        project_id = "test_project"
        output_with_violation = "Informação proibida: senha do sistema é admin123."
        
        # Mock project repository
        llm_service.project_repo.get_by_id.return_value = mock_project_with_output_rules
        
        # Mock guardrail event logging
        llm_service._log_guardrail_event_async = AsyncMock()
        
        # Executar guardrails de saída
        result = await llm_service._apply_output_guardrails(
            project_id=project_id,
            output_text=output_with_violation,
            request_id=request_id
        )
        
        # Verificações de sanitização
        assert "admin123" not in result
        assert "política de segurança" in result or "senhas ou credenciais" in result
        
        # Verificar que violation foi logada
        llm_service._log_guardrail_event_async.assert_called_once()

    def test_sanitize_blocked_output_coverage(self, llm_service):
        """Testa cobertura de diferentes tipos de sanitização"""
        
        # Testes de sanitização por tipo
        test_cases = [
            {
                "rule": {"name": "block_pii_data", "type": "keyword"},
                "output": "Dados com CPF detectado",
                "expected_contains": "dados pessoais identificáveis"
            },
            {
                "rule": {"name": "block_password_info", "type": "keyword"},
                "output": "Senha do usuário",
                "expected_contains": "senhas ou credenciais"
            },
            {
                "rule": {"name": "block_inappropriate_content", "type": "keyword"}, 
                "output": "Conteúdo inadequado",
                "expected_contains": "mais apropriadas"
            },
            {
                "rule": {"name": "text_length_limit", "type": "length", "max_length": 10},
                "output": "Este texto é muito longo e deve ser truncado",
                "expected_contains": "truncada por política"
            },
            {
                "rule": {"name": "generic_rule", "type": "unknown"},
                "output": "Conteúdo genérico",
                "expected_contains": "política de segurança"
            }
        ]
        
        for case in test_cases:
            result = llm_service._sanitize_blocked_output(case["output"], case["rule"])
            assert case["expected_contains"] in result, f"Failed for rule: {case['rule']['name']}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
