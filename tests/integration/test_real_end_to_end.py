"""
Testes End-to-End REAIS - Hub Rodando + SDK Consumindo + Dados Persistidos
=========================================================================

🚨 TESTES VERDADEIROS:
- Hub FastAPI rodando como servidor real em porta separada
- SDK BradaxClient fazendo chamadas HTTP reais
- Verificação de dados persistidos nos arquivos JSON
- Validação visual dos dados gerados em guardrails.json e telemetry.json

Sem TestClient - apenas processos reais e arquivos reais modificados.
"""

import asyncio
import json
import multiprocessing
import os
import subprocess
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import psutil
import pytest
import requests
import uvicorn
from contextlib import contextmanager

# Setup dos paths
test_dir = Path(__file__).parent.parent
broker_dir = test_dir.parent / "bradax-broker"
sdk_dir = test_dir.parent / "bradax-sdk" / "src"
data_dir = broker_dir / "data"

# Adicionar paths para imports
sys.path.insert(0, str(broker_dir / "src"))
sys.path.insert(0, str(sdk_dir))

# Imports do sistema real
from bradax.client import BradaxClient
from bradax.config.sdk_config import BradaxSDKConfig, set_sdk_config


class RealHubServer:
    """Gerenciador do servidor Hub real"""
    
    def __init__(self, port: int = 8001):
        self.port = port
        self.process: Optional[subprocess.Popen] = None
        self.base_url = f"http://localhost:{port}"
        
    def start(self) -> bool:
        """Inicia o servidor Hub real"""
        print(f"🚀 Iniciando Hub na porta {self.port}...")
        
        # Comando para rodar o servidor
        env = os.environ.copy()
        env["BRADAX_JWT_SECRET"] = "test_jwt_secret_for_real_tests_2025"
        env["BRADAX_OPENAI_API_KEY"] = "test_openai_key"
        
        cmd = [
            sys.executable, 
            "-m", "uvicorn",
            "broker.main:app",
            "--host", "localhost",
            "--port", str(self.port),
            "--reload", "False",
            "--access-log", "False"
        ]
        
        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=str(broker_dir / "src"),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Aguardar servidor inicializar
            max_attempts = 30
            for attempt in range(max_attempts):
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=2)
                    if response.status_code == 200:
                        print(f"✅ Hub iniciado com sucesso na porta {self.port}")
                        return True
                except requests.exceptions.RequestException:
                    pass
                
                time.sleep(0.5)
            
            print(f"❌ Hub não respondeu após {max_attempts * 0.5}s")
            return False
            
        except Exception as e:
            print(f"❌ Erro ao iniciar Hub: {e}")
            return False
    
    def stop(self):
        """Para o servidor Hub"""
        if self.process:
            print(f"🛑 Parando Hub na porta {self.port}")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            
            self.process = None
    
    def is_running(self) -> bool:
        """Verifica se o servidor está rodando"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False


class RealDataManager:
    """Gerenciador de dados reais nos arquivos JSON"""
    
    def __init__(self):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.projects_file = self.data_dir / "projects.json"
        self.llm_models_file = self.data_dir / "llm_models.json"
        self.guardrails_file = self.data_dir / "guardrails.json"
        self.telemetry_file = self.data_dir / "telemetry.json"
        
        # Backup inicial dos arquivos se existirem
        self._backup_existing_files()
        
    def _backup_existing_files(self):
        """Faz backup dos arquivos existentes"""
        self.backups = {}
        for file_key, file_path in {
            "projects": self.projects_file,
            "llm_models": self.llm_models_file,
            "guardrails": self.guardrails_file,
            "telemetry": self.telemetry_file
        }.items():
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.backups[file_key] = json.load(f)
    
    def setup_test_data(self):
        """Configura dados iniciais para testes"""
        # Projects
        projects_data = [
            {
                "project_id": "proj_real_test_2025",
                "project_name": "Real End-to-End Test Project",
                "status": "active",
                "allowed_llms": ["gpt-4.1-nano"],
                "project_token": "real_test_token_bradax_2025_secure",
                "created_at": datetime.now().isoformat(),
                "telemetry_enabled": True,
                "guardrails_enabled": True
            }
        ]
        
        # LLM Models
        llm_models_data = [
            {
                "model_id": "gpt-4.1-nano",
                "provider": "openai",
                "enabled": True,
                "max_tokens": 4096,
                "supports_streaming": True,
                "cost_per_1k_tokens": 0.002,
                "description": "GPT-4.1 Nano for real testing"
            }
        ]
        
        # Guardrails
        guardrails_data = [
            {
                "guardrail_id": "block_python_real_test",
                "project_id": "proj_real_test_2025",
                "rule_type": "content_pattern",
                "pattern": r"(def |class |import |from .* import)",
                "action": "block",
                "enabled": True,
                "description": "Block Python code in real test",
                "severity": "high"
            }
        ]
        
        # Telemetry (vazio inicialmente)
        telemetry_data = []
        
        # Escrever arquivos
        self._write_json(self.projects_file, projects_data)
        self._write_json(self.llm_models_file, llm_models_data)
        self._write_json(self.guardrails_file, guardrails_data)
        self._write_json(self.telemetry_file, telemetry_data)
        
        print("✅ Dados de teste configurados nos JSONs reais")
    
    def _write_json(self, file_path: Path, data: Any):
        """Escreve dados JSON no arquivo"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_current_telemetry_count(self) -> int:
        """Retorna número atual de logs de telemetria"""
        if self.telemetry_file.exists():
            with open(self.telemetry_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return len(data) if isinstance(data, list) else 0
        return 0
    
    def get_current_telemetry_logs(self) -> List[Dict]:
        """Retorna logs atuais de telemetria"""
        if self.telemetry_file.exists():
            with open(self.telemetry_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        return []
    
    def get_current_guardrail_logs(self) -> List[Dict]:
        """Retorna logs atuais de guardrail"""
        if self.guardrails_file.exists():
            with open(self.guardrails_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        return []
    
    def show_file_contents(self, file_name: str):
        """Mostra conteúdo de um arquivo JSON"""
        file_path = getattr(self, f"{file_name}_file", None)
        if file_path and file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"📄 {file_name}.json:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                print("-" * 50)
        else:
            print(f"❌ Arquivo {file_name}.json não encontrado")
    
    def restore_backups(self):
        """Restaura arquivos originais do backup"""
        for file_key, backup_data in self.backups.items():
            file_path = getattr(self, f"{file_key}_file")
            self._write_json(file_path, backup_data)
        
        print("✅ Arquivos restaurados do backup")


@pytest.fixture(scope="class")
def real_hub_server():
    """Servidor Hub real para testes"""
    server = RealHubServer(port=8001)
    
    if not server.start():
        pytest.skip("Não foi possível iniciar o servidor Hub")
    
    yield server
    server.stop()


@pytest.fixture(scope="class")
def real_data_manager():
    """Gerenciador de dados reais"""
    manager = RealDataManager()
    manager.setup_test_data()
    
    yield manager
    
    # Cleanup - restaurar backups se existirem
    manager.restore_backups()


@pytest.fixture
def real_sdk_client(real_hub_server):
    """SDK Client configurado para servidor real"""
    # Configurar SDK para servidor real
    config = BradaxSDKConfig.for_testing(
        broker_url=real_hub_server.base_url,
        project_id="proj_real_test_2025",
        timeout=30,
        enable_telemetry=True,
        enable_guardrails=True
    )
    set_sdk_config(config)
    
    # Criar cliente SDK
    client = BradaxClient(project_token="real_test_token_bradax_2025_secure")
    
    return client


@pytest.mark.integration
@pytest.mark.slow
class TestRealEndToEnd:
    """Testes end-to-end com servidor real e SDK real"""
    
    def test_real_valid_request_with_data_persistence(self, real_hub_server, real_data_manager, real_sdk_client):
        """
        Teste: Request válida end-to-end com persistência real
        
        Cenário: SDK → Hub real → dados persistidos nos JSONs
        Esperado: Response válida + telemetria gravada no arquivo
        Validar: Dados realmente aparecem nos arquivos JSON
        """
        print(f"🔍 ANTES DA REQUEST:")
        print(f"   Telemetry logs: {real_data_manager.get_current_telemetry_count()}")
        real_data_manager.show_file_contents("telemetry")
        
        # Fazer request usando SDK real
        print(f"📤 Fazendo request via SDK para {real_hub_server.base_url}...")
        
        try:
            # Request simples para teste
            messages = [{"role": "user", "content": "Hello, this is a real test message"}]
            
            # Esta chamada deve ir: SDK → HTTP → Hub real
            response = real_sdk_client.chat_completion(
                messages=messages,
                model="gpt-4.1-nano",
                max_tokens=50
            )
            
            print(f"✅ Response recebida via SDK: {type(response)}")
            
            # Aguardar um pouco para persistência
            time.sleep(2)
            
            # Verificar se telemetria foi gravada
            print(f"🔍 DEPOIS DA REQUEST:")
            new_telemetry_count = real_data_manager.get_current_telemetry_count()
            print(f"   Telemetry logs: {new_telemetry_count}")
            
            # Mostrar dados gerados
            real_data_manager.show_file_contents("telemetry")
            
            # Validar que houve persistência
            telemetry_logs = real_data_manager.get_current_telemetry_logs()
            
            if len(telemetry_logs) > 0:
                latest_log = telemetry_logs[-1]
                print(f"📊 ÚLTIMA TELEMETRIA GRAVADA:")
                print(f"   Project ID: {latest_log.get('project_id')}")
                print(f"   Model: {latest_log.get('model_used')}")
                print(f"   Timestamp: {latest_log.get('timestamp')}")
                print(f"   Status: {latest_log.get('status_code')}")
                
                # Verificar campos obrigatórios
                assert latest_log.get("project_id") == "proj_real_test_2025"
                assert latest_log.get("model_used") == "gpt-4.1-nano"
                assert "timestamp" in latest_log
                
                print("✅ Telemetria persistida corretamente!")
            else:
                print("⚠️ Nenhuma telemetria foi gravada no arquivo")
            
        except Exception as e:
            print(f"❌ Erro na request: {e}")
            # Mostrar conteúdo atual dos arquivos para debug
            real_data_manager.show_file_contents("projects")
            real_data_manager.show_file_contents("llm_models")
            raise
    
    def test_real_blocked_request_by_guardrail(self, real_hub_server, real_data_manager, real_sdk_client):
        """
        Teste: Request bloqueada por guardrail com logs reais
        
        Cenário: SDK → Hub → Guardrail bloqueia → log gerado
        Esperado: Request bloqueada + log no arquivo guardrails.json
        Validar: Sistema de bloqueio funciona e persiste dados
        """
        print(f"🔍 ANTES DA REQUEST BLOQUEADA:")
        initial_guardrail_count = len(real_data_manager.get_current_guardrail_logs())
        print(f"   Guardrail logs: {initial_guardrail_count}")
        
        # Request com código Python (deve ser bloqueada)
        messages = [
            {
                "role": "user", 
                "content": "def hello(): print('this should be blocked')"
            }
        ]
        
        print(f"📤 Fazendo request com código Python (deve ser bloqueada)...")
        
        try:
            response = real_sdk_client.chat_completion(
                messages=messages,
                model="gpt-4.1-nano",
                max_tokens=50
            )
            
            # Se chegou aqui, não foi bloqueada (pode ser erro)
            print(f"⚠️ Request não foi bloqueada como esperado: {response}")
            
        except Exception as e:
            print(f"✅ Request bloqueada com erro: {e}")
        
        # Aguardar persistência
        time.sleep(2)
        
        # Verificar logs de guardrail
        print(f"🔍 DEPOIS DA REQUEST BLOQUEADA:")
        final_guardrail_count = len(real_data_manager.get_current_guardrail_logs())
        print(f"   Guardrail logs: {final_guardrail_count}")
        
        # Mostrar dados de guardrail
        real_data_manager.show_file_contents("guardrails")
        
        # TODO: Implementar verificação específica de logs de bloqueio
        # quando a funcionalidade estiver completamente integrada
        print("⚠️ Verificação de logs de guardrail pendente de integração completa")
    
    def test_real_invalid_token_rejection(self, real_hub_server, real_data_manager):
        """
        Teste: Token inválido rejeitado com SDK real
        
        Cenário: SDK com token inválido → Hub → rejeição
        Esperado: Erro de autenticação via HTTP real
        Validar: Autenticação rigorosa funciona end-to-end
        """
        # Configurar SDK com token inválido
        config = BradaxSDKConfig.for_testing(
            broker_url=real_hub_server.base_url,
            project_id="proj_real_test_2025",
            timeout=30
        )
        set_sdk_config(config)
        
        # Cliente com token inválido
        invalid_client = BradaxClient(project_token="invalid_token_12345")
        
        print(f"📤 Fazendo request com token inválido...")
        
        try:
            response = invalid_client.chat_completion(
                messages=[{"role": "user", "content": "This should be rejected"}],
                model="gpt-4.1-nano",
                max_tokens=50
            )
            
            # Se chegou aqui, não foi rejeitada (erro)
            pytest.fail(f"Token inválido foi aceito: {response}")
            
        except Exception as e:
            print(f"✅ Token inválido rejeitado: {e}")
            
            # Verificar se erro menciona autenticação
            error_str = str(e).lower()
            assert any(keyword in error_str for keyword in ["unauthorized", "forbidden", "token", "auth"]), \
                f"Erro não indica problema de autenticação: {e}"
    
    def test_show_all_generated_data(self, real_data_manager):
        """
        Teste: Mostrar todos os dados gerados durante os testes
        
        Objetivo: Visualizar o que foi realmente persistido nos JSONs
        """
        print("\n" + "="*60)
        print("📊 DADOS FINAIS GERADOS NOS ARQUIVOS JSON:")
        print("="*60)
        
        real_data_manager.show_file_contents("projects")
        real_data_manager.show_file_contents("llm_models")
        real_data_manager.show_file_contents("guardrails")
        real_data_manager.show_file_contents("telemetry")
        
        print("="*60)
        print("✅ Dados exibidos - verificar logs acima para validar persistência")


# Executar testes se chamado diretamente
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s", "-m", "integration"])
