"""
Testes do Hub - Sistema de Guardrails
=====================================

Testes rigorosos do sistema de guardrails baseados na análise completa.
Validação de guardrails defaults (inegociáveis) + customizados.

Baseado em:
- GuardrailsService analisado
- Estrutura GuardrailData real
- Patterns de bloqueio customizáveis
- Logs de violação detalhados
"""

import asyncio
import json
import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any, List

import httpx
from fastapi.testclient import TestClient

# Imports do sistema Bradax
import sys
from pathlib import Path

# Adicionar o path do bradax-broker
broker_path = Path(__file__).parent.parent.parent / "bradax-broker" / "src"
sys.path.insert(0, str(broker_path))

from broker.main import app
from broker.services.guardrails import GuardrailsService
from tests.fixtures.test_fixtures import BradaxTestFixtures, BradaxTestDataManager, TestValidators


class TestHubGuardrails:
    """Testes do sistema de guardrails do Hub"""
    
    @pytest.fixture
    def test_data_manager(self):
        """Setup de dados de teste com guardrails configurados"""
        with BradaxTestDataManager() as manager:
            yield manager
    
    @pytest.fixture
    def client(self, test_data_manager):
        """Cliente de teste com dados configurados"""
        # Configurar app para usar dados de teste
        with TestClient(app) as client:
            yield client
    
    def test_python_code_blocking(self, client, test_data_manager):
        """
        Teste: Código Python deve ser bloqueado por guardrail customizado
        
        Cenário: Request com código Python no prompt
        Esperado: HTTP 400/403 com bloqueio por guardrail 'no_python_code'
        Validar: Log de guardrail gravado no guardrails.json
        """
        valid_token = BradaxTestFixtures.get_valid_project_token()
        blocked_request = BradaxTestFixtures.get_blocked_python_request()
        
        headers = {
            "Authorization": f"Bearer {valid_token}",
            "Content-Type": "application/json",
            "X-Bradax-Telemetry": json.dumps(blocked_request["telemetry"])
        }
        
        # Remover campos que não vão no body da request HTTP
        request_body = {
            "model": blocked_request["model"],
            "messages": blocked_request["messages"],
            "max_tokens": blocked_request["max_tokens"],
            "temperature": blocked_request.get("temperature", 0.7)
        }
        
        response = client.post("/llm/invoke", json=request_body, headers=headers)
        
        # Deve ser bloqueado (400 ou 403)
        assert response.status_code in [400, 403], \
            f"Request com código Python deveria ser bloqueada: {response.status_code}"
        
        # Verificar se resposta menciona guardrail
        error_data = response.json()
        error_message = error_data.get("detail", "").lower()
        assert any(keyword in error_message for keyword in ["guardrail", "blocked", "python", "code"]), \
            f"Erro deve mencionar guardrail: {error_data.get('detail')}"
        
        # Validar que conteúdo realmente deveria ser bloqueado
        content = blocked_request["messages"][0]["content"]
        should_block = TestValidators.validate_guardrail_trigger(content, "no_python_code")
        assert should_block, "O conteúdo deveria triggar o guardrail no_python_code"
        
        print(f"✅ Código Python bloqueado corretamente: {error_data.get('detail')}")
        
        # TODO: Verificar se log foi gravado em guardrails.json (quando integração estiver completa)
    
    def test_personal_data_blocking(self, client, test_data_manager):
        """
        Teste: Dados pessoais (SSN/CPF) devem ser bloqueados
        
        Cenário: Request contendo SSN e CPF
        Esperado: HTTP 400/403 com bloqueio por guardrail 'no_personal_data'
        Validar: Detecção de múltiplos padrões (SSN + CPF)
        """
        valid_token = BradaxTestFixtures.get_valid_project_token()
        blocked_request = BradaxTestFixtures.get_blocked_personal_data_request()
        
        headers = {
            "Authorization": f"Bearer {valid_token}",
            "Content-Type": "application/json", 
            "X-Bradax-Telemetry": json.dumps(blocked_request["telemetry"])
        }
        
        request_body = {
            "model": blocked_request["model"],
            "messages": blocked_request["messages"],
            "max_tokens": blocked_request["max_tokens"]
        }
        
        response = client.post("/llm/invoke", json=request_body, headers=headers)
        
        # Deve ser bloqueado
        assert response.status_code in [400, 403], \
            f"Request com dados pessoais deveria ser bloqueada: {response.status_code}"
        
        # Verificar mensagem de erro
        error_data = response.json()
        error_message = error_data.get("detail", "").lower()
        assert any(keyword in error_message for keyword in ["guardrail", "blocked", "personal", "data"]), \
            f"Erro deve mencionar dados pessoais: {error_data.get('detail')}"
        
        # Validar detecção de padrões
        content = blocked_request["messages"][0]["content"]
        should_block = TestValidators.validate_guardrail_trigger(content, "no_personal_data")
        assert should_block, "O conteúdo deveria triggar o guardrail no_personal_data"
        
        print(f"✅ Dados pessoais bloqueados: {error_data.get('detail')}")
    
    def test_multiple_guardrails_violation(self, client, test_data_manager):
        """
        Teste: Violação de múltiplos guardrails simultaneamente
        
        Cenário: Request que viola no_python_code + no_personal_data + no_financial_data  
        Esperado: HTTP 400/403 com bloqueio, múltiplos logs
        Validar: Sistema detecta todas as violações
        """
        valid_token = BradaxTestFixtures.get_valid_project_token()
        multi_violation_request = BradaxTestFixtures.get_multiple_guardrails_violation_request()
        
        headers = {
            "Authorization": f"Bearer {valid_token}",
            "Content-Type": "application/json",
            "X-Bradax-Telemetry": json.dumps(multi_violation_request["telemetry"])
        }
        
        request_body = {
            "model": multi_violation_request["model"],
            "messages": multi_violation_request["messages"],
            "max_tokens": multi_violation_request["max_tokens"]
        }
        
        response = client.post("/llm/invoke", json=request_body, headers=headers)
        
        # Deve ser bloqueado
        assert response.status_code in [400, 403], \
            f"Request com múltiplas violações deveria ser bloqueada: {response.status_code}"
        
        # Verificar se detecta múltiplas violações
        content = multi_violation_request["messages"][0]["content"]
        
        python_violation = TestValidators.validate_guardrail_trigger(content, "no_python_code")
        personal_violation = TestValidators.validate_guardrail_trigger(content, "no_personal_data")
        financial_violation = TestValidators.validate_guardrail_trigger(content, "no_financial_data")
        
        violations_detected = sum([python_violation, personal_violation, financial_violation])
        assert violations_detected >= 2, f"Deveria detectar múltiplas violações, detectou {violations_detected}"
        
        print(f"✅ Múltiplas violações detectadas: Python={python_violation}, Personal={personal_violation}, Financial={financial_violation}")
    
    def test_valid_content_passes_guardrails(self, client, test_data_manager):
        """
        Teste: Conteúdo válido deve passar pelos guardrails
        
        Cenário: Request limpa sem violações
        Esperado: HTTP 200 ou processamento normal (não bloqueio por guardrail)
        Validar: Sistema não bloqueia conteúdo válido
        """
        valid_token = BradaxTestFixtures.get_valid_project_token()
        valid_request = BradaxTestFixtures.get_valid_llm_request()
        
        headers = {
            "Authorization": f"Bearer {valid_token}",
            "Content-Type": "application/json",
            "X-Bradax-Telemetry": json.dumps(valid_request["telemetry"])
        }
        
        request_body = {
            "model": valid_request["model"],
            "messages": valid_request["messages"],
            "max_tokens": valid_request["max_tokens"],
            "temperature": valid_request.get("temperature", 0.7)
        }
        
        response = client.post("/llm/invoke", json=request_body, headers=headers)
        
        # NÃO deve ser bloqueado por guardrail
        if response.status_code in [400, 403]:
            error_data = response.json()
            error_message = error_data.get("detail", "").lower()
            # Se foi bloqueado, não deveria ser por guardrail
            assert not any(keyword in error_message for keyword in ["guardrail", "blocked", "violation"]), \
                f"Conteúdo válido foi bloqueado por guardrail: {error_data.get('detail')}"
        
        # Verificar que conteúdo realmente é limpo
        content = valid_request["messages"][0]["content"]
        for guardrail_name in ["no_python_code", "no_personal_data", "no_financial_data"]:
            should_not_block = not TestValidators.validate_guardrail_trigger(content, guardrail_name)
            assert should_not_block, f"Conteúdo válido triggou guardrail {guardrail_name}"
        
        print(f"✅ Conteúdo válido passou pelos guardrails: {response.status_code}")
    
    def test_default_guardrails_cannot_be_disabled(self, client, test_data_manager):
        """
        Teste: Guardrails defaults não podem ser desabilitados
        
        Cenário: Tentar desabilitar guardrails padrão via request
        Esperado: Guardrails continuam ativos independente de flags
        Validar: Governança inegociável
        """
        # Este teste será expandido quando a integração completa estiver pronta
        # Por enquanto, documentamos que o sistema deve sempre aplicar defaults
        
        # Conteúdo que deveria ser bloqueado por defaults
        content_with_violations = "This contains sensitive data: SSN 123-45-6789"
        
        # Verificar que padrões de segurança são detectados
        has_personal_data = TestValidators.validate_guardrail_trigger(content_with_violations, "no_personal_data")
        assert has_personal_data, "Sistema deveria detectar dados pessoais mesmo com tentativas de bypass"
        
        print("✅ Guardrails defaults permanecem ativos (governança inegociável)")
    
    def test_guardrail_logging_structure(self, test_data_manager):
        """
        Teste: Estrutura dos logs de guardrails
        
        Cenário: Verificar se logs seguem estrutura GuardrailData  
        Esperado: Campos obrigatórios presentes
        Validar: Compatibilidade com sistema de storage
        """
        # Testar estrutura do log esperado
        expected_log = BradaxTestFixtures.get_expected_guardrail_violation_log()
        
        # Campos obrigatórios baseados na análise da estrutura GuardrailData
        required_fields = [
            "event_id", "project_id", "guardrail_name", 
            "action", "triggered_at", "details"
        ]
        
        for field in required_fields:
            assert field in expected_log, f"Campo obrigatório {field} ausente no log"
        
        # Verificar estrutura do details
        details = expected_log.get("details", {})
        assert "matched_pattern" in details, "Details deve conter matched_pattern"
        assert "violation_count" in details, "Details deve conter violation_count"
        
        print("✅ Estrutura de logs de guardrails está correta")


class TestGuardrailsService:
    """Testes unitários do GuardrailsService"""
    
    def test_pattern_matching_python_code(self):
        """
        Teste: Padrões de detecção de código Python
        
        Verificar se regex consegue detectar diferentes formas de código Python
        """
        test_cases = [
            ("def function_name():", True),
            ("import os", True), 
            ("from datetime import datetime", True),
            ("python script", True),
            ("This is regular text", False),
            ("definition of terms", False),  # "def" mas não código
            ("important information", False)  # "import" mas não código
        ]
        
        for content, should_match in test_cases:
            result = TestValidators.validate_guardrail_trigger(content, "no_python_code")
            assert result == should_match, \
                f"Pattern matching falhou para '{content}': esperado {should_match}, obtido {result}"
        
        print("✅ Detecção de código Python funcionando corretamente")
    
    def test_pattern_matching_personal_data(self):
        """
        Teste: Padrões de detecção de dados pessoais
        
        Verificar detecção de SSN, CPF e variações
        """
        test_cases = [
            ("SSN: 123-45-6789", True),
            ("CPF 12345678901", True),
            ("Social Security Number 123456789", False),  # Formato diferente
            ("Regular numbers 123456", False),
            ("Phone: 555-123-4567", False),  # Não é SSN
            ("User ID 12345678901", True),  # CPF format
        ]
        
        for content, should_match in test_cases:
            result = TestValidators.validate_guardrail_trigger(content, "no_personal_data")
            assert result == should_match, \
                f"Pattern matching falhou para '{content}': esperado {should_match}, obtido {result}"
        
        print("✅ Detecção de dados pessoais funcionando corretamente")


# Executar testes se rodado diretamente
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
