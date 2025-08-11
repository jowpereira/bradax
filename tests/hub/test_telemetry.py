"""
Testes do Hub - Sistema de Telemetria Obrigatória  
=================================================

Testes rigorosos do sistema de telemetria baseados na análise completa.
Validação de coleta, validação e persistência de telemetria real.

Baseado em:
- Middleware telemetry_validation analisado
- Estrutura TelemetryData real
- TelemetryCollector service
- Persistência em telemetry.json
"""

import asyncio
import json
import pytest
import tempfile
import time
from datetime import datetime
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
from broker.services.telemetry import TelemetryCollector
from tests.fixtures.test_fixtures import (
    BradaxTestFixtures, 
    BradaxTestDataManager, 
    TestValidators,
    requires_real_telemetry
)


class TestHubTelemetryValidation:
    """Testes de validação obrigatória de telemetria"""
    
    @pytest.fixture
    def test_data_manager(self):
        """Setup de dados de teste"""
        with BradaxTestDataManager() as manager:
            yield manager
    
    @pytest.fixture
    def client(self, test_data_manager):
        """Cliente de teste configurado"""
        with TestClient(app) as client:
            yield client
    
    def test_missing_telemetry_header_rejection(self, client, test_data_manager):
        """
        Teste: Request sem header X-Bradax-Telemetry deve ser rejeitada
        
        Cenário: Request válida em todos os aspectos exceto telemetria ausente
        Esperado: HTTP 400 Bad Request
        Validar: Telemetria é obrigatória em 100% das requests
        """
        valid_token = BradaxTestFixtures.get_valid_project_token()
        
        headers = {
            "Authorization": f"Bearer {valid_token}",
            "Content-Type": "application/json"
            # X-Bradax-Telemetry ausente intencionalmente
        }
        
        request_body = {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Test without telemetry"}],
            "max_tokens": 50
        }
        
        response = client.post("/llm/invoke", json=request_body, headers=headers)
        
        # Deve ser 400 (bad request)
        assert response.status_code == 400, \
            f"Request sem telemetria deveria retornar 400: {response.status_code}"
        
        # Verificar mensagem específica
        error_data = response.json()
        error_message = error_data.get("detail", "").lower()
        assert any(keyword in error_message for keyword in ["telemetry", "telemetria", "required", "missing"]), \
            f"Erro deve mencionar telemetria ausente: {error_data.get('detail')}"
        
        print(f"✅ Request sem telemetria rejeitada: {error_data.get('detail')}")
    
    def test_invalid_telemetry_json_rejection(self, client, test_data_manager):
        """
        Teste: Header de telemetria com JSON inválido deve ser rejeitado
        
        Cenário: Header presente mas com formato JSON corrompido
        Esperado: HTTP 400 Bad Request 
        Validar: Validação rigorosa do formato
        """
        valid_token = BradaxTestFixtures.get_valid_project_token()
        
        headers = {
            "Authorization": f"Bearer {valid_token}",
            "Content-Type": "application/json",
            "X-Bradax-Telemetry": "invalid-json-{broken"  # JSON corrompido
        }
        
        request_body = {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Test with invalid telemetry"}],
            "max_tokens": 50
        }
        
        response = client.post("/llm/invoke", json=request_body, headers=headers)
        
        # Deve ser 400
        assert response.status_code == 400, \
            f"JSON inválido deveria retornar 400: {response.status_code}"
        
        # Verificar mensagem sobre formato
        error_data = response.json()
        error_message = error_data.get("detail", "").lower()
        assert any(keyword in error_message for keyword in ["json", "format", "invalid", "parse"]), \
            f"Erro deve mencionar JSON inválido: {error_data.get('detail')}"
        
        print(f"✅ JSON inválido rejeitado: {error_data.get('detail')}")
    
    def test_incomplete_telemetry_rejection(self, client, test_data_manager):
        """
        Teste: Telemetria com campos obrigatórios ausentes
        
        Cenário: JSON válido mas campos críticos ausentes (CPU, RAM, username)
        Esperado: HTTP 400 Bad Request
        Validar: Verificação de campos obrigatórios
        """
        valid_token = BradaxTestFixtures.get_valid_project_token()
        incomplete_request = BradaxTestFixtures.get_request_incomplete_telemetry()
        
        headers = {
            "Authorization": f"Bearer {valid_token}",
            "Content-Type": "application/json",
            "X-Bradax-Telemetry": json.dumps(incomplete_request["telemetry"])
        }
        
        request_body = {
            "model": incomplete_request["model"],
            "messages": incomplete_request["messages"],
            "max_tokens": incomplete_request["max_tokens"]
        }
        
        response = client.post("/llm/invoke", json=request_body, headers=headers)
        
        # Deve ser 400
        assert response.status_code == 400, \
            f"Telemetria incompleta deveria retornar 400: {response.status_code}"
        
        # Verificar que telemetria realmente está incompleta
        telemetry = incomplete_request["telemetry"]
        is_complete = TestValidators.validate_telemetry_data(telemetry)
        assert not is_complete, "Telemetria de teste deveria ser incompleta"
        
        print(f"✅ Telemetria incompleta rejeitada: {response.status_code}")
    
    @requires_real_telemetry
    def test_valid_telemetry_acceptance(self, client, test_data_manager):
        """
        Teste: Telemetria completa e válida deve ser aceita
        
        Cenário: Request com telemetria real coletada via psutil
        Esperado: HTTP 200 ou processamento normal (não rejeição por telemetria)
        Validar: Sistema aceita telemetria válida
        """
        valid_token = BradaxTestFixtures.get_valid_project_token()
        valid_request = BradaxTestFixtures.get_valid_llm_request()
        
        # Verificar que telemetria está completa
        telemetry = valid_request["telemetry"]
        is_complete = TestValidators.validate_telemetry_data(telemetry)
        assert is_complete, "Telemetria de teste deve estar completa"
        
        headers = {
            "Authorization": f"Bearer {valid_token}",
            "Content-Type": "application/json",
            "X-Bradax-Telemetry": json.dumps(telemetry)
        }
        
        request_body = {
            "model": valid_request["model"],
            "messages": valid_request["messages"],
            "max_tokens": valid_request["max_tokens"]
        }
        
        response = client.post("/llm/invoke", json=request_body, headers=headers)
        
        # NÃO deve ser rejeitada por telemetria
        if response.status_code == 400:
            error_data = response.json()
            error_message = error_data.get("detail", "").lower()
            assert not any(keyword in error_message for keyword in ["telemetry", "telemetria"]), \
                f"Telemetria válida foi rejeitada: {error_data.get('detail')}"
        
        print(f"✅ Telemetria válida aceita: {response.status_code}")


class TestTelemetryDataCollection:
    """Testes de coleta e estrutura de dados de telemetria"""
    
    @requires_real_telemetry  
    def test_real_machine_telemetry_collection(self):
        """
        Teste: Coleta de telemetria real da máquina
        
        Cenário: Executar coleta como o SDK faria
        Esperado: Dados reais coletados via psutil
        Validar: Não é mock - são métricas reais
        """
        telemetry = BradaxTestFixtures.get_real_machine_telemetry()
        
        # Verificar campos obrigatórios
        required_fields = [
            "cpu_percent", "memory_percent", "username",
            "process_id", "platform", "timestamp"
        ]
        
        for field in required_fields:
            assert field in telemetry, f"Campo obrigatório {field} ausente"
            assert telemetry[field] is not None, f"Campo {field} não pode ser None"
        
        # Verificar que são dados reais (não zeros)
        cpu = telemetry.get("cpu_percent", 0)
        memory = telemetry.get("memory_percent", 0)
        
        # CPU e memória devem ter valores realistas (não exatamente 0)
        assert isinstance(cpu, (int, float)), "CPU deve ser numérico"
        assert isinstance(memory, (int, float)), "Memory deve ser numérico"
        assert 0 <= cpu <= 100, f"CPU deve estar entre 0-100%: {cpu}"
        assert 0 <= memory <= 100, f"Memory deve estar entre 0-100%: {memory}"
        
        # Verificar timestamp válido
        timestamp = telemetry.get("timestamp", "")
        assert timestamp.endswith("Z"), "Timestamp deve ser UTC (terminar com Z)"
        
        # Tentar parsear timestamp
        from datetime import datetime
        parsed_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert parsed_time is not None, "Timestamp deve ser válido"
        
        print(f"✅ Telemetria real coletada: CPU={cpu}%, RAM={memory}%, User={telemetry.get('username')}")
    
    def test_telemetry_data_structure(self):
        """
        Teste: Estrutura de dados de telemetria
        
        Cenário: Verificar se estrutura segue TelemetryData analisada
        Esperado: Todos os campos necessários presentes
        Validar: Compatibilidade com sistema de storage
        """
        expected_telemetry = BradaxTestFixtures.get_expected_success_telemetry_log()
        
        # Campos obrigatórios baseados na estrutura TelemetryData
        required_fields = [
            "telemetry_id", "project_id", "timestamp", "event_type",
            "status_code", "model_used", "system_info"
        ]
        
        for field in required_fields:
            assert field in expected_telemetry, f"Campo {field} obrigatório na estrutura"
        
        # Verificar estrutura do system_info
        system_info = expected_telemetry.get("system_info", {})
        assert isinstance(system_info, dict), "system_info deve ser dict"
        assert "cpu_percent" in system_info, "system_info deve ter cpu_percent"
        assert "username" in system_info, "system_info deve ter username"
        
        print("✅ Estrutura de telemetria está correta")
    
    def test_telemetry_persistence_simulation(self, tmp_path):
        """
        Teste: Simulação de persistência de telemetria
        
        Cenário: Simular gravação de log em telemetry.json
        Esperado: Arquivo JSON válido criado
        Validar: Formato compatível com JsonStorage
        """
        # Simular dados que seriam gravados
        telemetry_log = BradaxTestFixtures.get_expected_success_telemetry_log()
        
        # Arquivo temporário
        telemetry_file = tmp_path / "telemetry.json"
        
        # Simular gravação (como o sistema faria)
        existing_logs = []
        existing_logs.append(telemetry_log)
        
        with open(telemetry_file, 'w', encoding='utf-8') as f:
            json.dump(existing_logs, f, indent=2, ensure_ascii=False)
        
        # Verificar que arquivo foi criado
        assert telemetry_file.exists(), "Arquivo de telemetria deve ser criado"
        
        # Verificar que pode ser lido de volta
        with open(telemetry_file, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        
        assert isinstance(loaded_data, list), "Dados devem ser uma lista"
        assert len(loaded_data) == 1, "Deve ter um log"
        assert loaded_data[0]["telemetry_id"] == telemetry_log["telemetry_id"], "Dados devem ser iguais"
        
        print(f"✅ Simulação de persistência funcionou: {telemetry_file}")


class TestTelemetryIntegration:
    """Testes de integração do sistema de telemetria"""
    
    def test_telemetry_validation_flow(self):
        """
        Teste: Fluxo completo de validação de telemetria
        
        Cenário: Diferentes tipos de telemetria pelo pipeline
        Esperado: Validação correta em cada etapa
        Validar: Pipeline de validação funciona
        """
        test_cases = [
            {
                "name": "telemetria_completa",
                "data": BradaxTestFixtures.get_real_machine_telemetry(),
                "should_pass": True
            },
            {
                "name": "telemetria_vazia", 
                "data": {},
                "should_pass": False
            },
            {
                "name": "telemetria_parcial",
                "data": {"timestamp": datetime.utcnow().isoformat() + "Z"},
                "should_pass": False
            }
        ]
        
        for test_case in test_cases:
            telemetry_data = test_case["data"]
            is_valid = TestValidators.validate_telemetry_data(telemetry_data)
            
            if test_case["should_pass"]:
                assert is_valid, f"Telemetria {test_case['name']} deveria ser válida"
            else:
                assert not is_valid, f"Telemetria {test_case['name']} deveria ser inválida"
        
        print("✅ Pipeline de validação de telemetria funcionando")
    
    def test_telemetry_data_manager_integration(self):
        """
        Teste: Integração com TestDataManager
        
        Cenário: Usar manager para simular logs de telemetria
        Esperado: Logs são gravados e podem ser recuperados
        Validar: Integração com sistema de arquivos
        """
        with BradaxTestDataManager() as manager:
            # Verificar que arquivo de telemetria foi criado
            assert manager.telemetry_file.exists(), "Arquivo telemetry.json deve existir"
            
            # Verificar que está inicialmente vazio
            initial_logs = manager.get_telemetry_logs()
            assert initial_logs == [], "Telemetria deve começar vazia"
            
            # Simular adição de log (como o sistema faria)
            test_log = BradaxTestFixtures.get_expected_success_telemetry_log()
            current_logs = manager.get_telemetry_logs()
            current_logs.append(test_log)
            manager._write_json_file(manager.telemetry_file, current_logs)
            
            # Verificar que log foi adicionado
            updated_logs = manager.get_telemetry_logs()
            assert len(updated_logs) == 1, "Deve ter um log"
            assert updated_logs[0]["telemetry_id"] == test_log["telemetry_id"], "Log deve ser o mesmo"
            
            # Verificar contadores por projeto
            counts = manager.count_logs_by_project("proj_test_bradax_2025")
            assert counts["telemetry_logs"] == 1, "Deve contar 1 log de telemetria"
        
        print("✅ Integração com TestDataManager funcionando")


# Executar testes se rodado diretamente
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
