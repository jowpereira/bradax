"""
Test Fixtures para Sistema Bradax - Dados Realistas Baseados na Análise Completa
================================================================================

Fixtures baseados na análise detalhada da arquitetura completa do sistema.
Todos os dados são realistas e refletem o funcionamento real do sistema.

🚨 IMPORTANTE: Estes fixtures NÃO são mocks. São dados reais que devem
funcionar com o sistema em execução usando gpt-4.1-nano exclusivamente.

Análise base: ARCHITECTURE_MEMORY.md completo com:
- Sistema de transações ACID no JsonStorage
- SDK com configuração avançada e telemetria automática  
- Guardrails customizáveis (mas defaults inegociáveis)
- Repository pattern com interfaces bem definidas
"""

import json
import os
import platform
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

# Importação condicional do psutil (coleta telemetria real)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️ psutil não disponível - telemetria será limitada")


class BradaxTestFixtures:
    """
    Classe centralizada para geração de fixtures de teste baseadas na análise completa.
    Todos os dados refletem as estruturas reais identificadas no sistema.
    """
    
    # === TOKENS E AUTENTICAÇÃO ===
    
    @staticmethod
    def get_valid_project_token() -> str:
        """Token válido para projeto de teste (formato real do sistema)"""
        return "bradax_token_proj_test_12345abc"
    
    @staticmethod
    def get_invalid_project_token() -> str:
        """Token inválido para testes de rejeição HTTP 403"""
        return "invalid_token_should_fail"
        
    @staticmethod
    def get_expired_project_token() -> str:
        """Token com formato válido mas expirado"""
        return "bradax_token_expired_test_xyz"
    
    # === DADOS DE PROJETOS (baseado em ProjectData) ===
    
    @staticmethod
    def get_test_project_data() -> Dict[str, Any]:
        """
        Projeto de teste válido baseado na estrutura ProjectData analisada.
        Inclui allowed_llms com gpt-4.1-nano e guardrails customizados.
        """
        return {
            "project_id": "proj_test_bradax_2025",
            "name": "Bradax Test Project 2025", 
            "created_at": "2025-01-15T10:30:00Z",
            "updated_at": "2025-08-09T18:00:00Z",
            "status": "active",
            "config": {
                "max_requests_per_minute": 60,
                "max_tokens_per_day": 10000,
                "cost_budget_usd": 100.0,
                "enable_custom_guardrails": True
            },
            "api_key_hash": "sha256:a1b2c3d4e5f6789012345abcdef67890",
            "owner": "test_developer_bradax",
            "description": "Projeto para testes rigorosos do sistema Bradax com governança completa",
            "tags": ["testing", "bradax", "llm", "governance", "gpt-4.1-nano"],
            
            # 🚨 CRÍTICO: Apenas gpt-4.1-nano permitido
            "allowed_llms": ["gpt-4.1-nano"],
            
            # 🛡️ Guardrails customizados (ADICIONAIS aos defaults)
            "custom_guardrails": [
                {
                    "name": "no_python_code",
                    "pattern": r"(python|def\s+\w+|import\s+\w+|from\s+\w+\s+import)",
                    "action": "block",
                    "message": "Código Python detectado e bloqueado por guardrail customizado",
                    "enabled": True
                },
                {
                    "name": "no_personal_data",
                    "pattern": r"(\b\d{3}-\d{2}-\d{4}\b|\b\d{11}\b|\bcpf\b|\bssn\b)",
                    "action": "block", 
                    "message": "Dados pessoais (SSN/CPF) detectados e bloqueados",
                    "enabled": True
                },
                {
                    "name": "no_financial_data",
                    "pattern": r"(\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b|card\s+number)",
                    "action": "warn",
                    "message": "Possíveis dados financeiros detectados", 
                    "enabled": True
                }
            ],
            
            "project_token": BradaxTestFixtures.get_valid_project_token(),
            
            # Rate limits específicos
            "rate_limits": {
                "requests_per_minute": 60,
                "requests_per_hour": 1000,
                "tokens_per_day": 10000
            }
        }
    
    @staticmethod
    def get_blocked_project_data() -> Dict[str, Any]:
        """Projeto com status bloqueado para testes de rejeição"""
        project = BradaxTestFixtures.get_test_project_data()
        project.update({
            "project_id": "proj_test_blocked",
            "name": "Projeto Bloqueado para Testes",
            "status": "blocked",  # Status que deve ser rejeitado
            "project_token": "bradax_token_blocked_project_xyz"
        })
        return project
    
    @staticmethod
    def get_limited_project_data() -> Dict[str, Any]:
        """Projeto com LLMs limitados (apenas um modelo específico)"""
        project = BradaxTestFixtures.get_test_project_data()
        project.update({
            "project_id": "proj_test_limited",
            "allowed_llms": ["gpt-4.1-nano"],  # Apenas este modelo
            "project_token": "bradax_token_limited_project"
        })
        return project
    
    # === DADOS DE MODELOS LLM (baseado em LLMModelInfo) ===
    
    @staticmethod
    def get_llm_models_data() -> List[Dict[str, Any]]:
        """
        Catálogo completo de modelos LLM baseado na estrutura LLMModelInfo.
        Inclui gpt-4.1-nano (permitido) e outros modelos (bloqueados).
        """
        return [
            {
                # 🚨 MODELO PRINCIPAL - Único permitido nos testes
                "model_id": "gpt-4.1-nano",
                "name": "GPT-4.1 Nano",
                "provider": "openai",
                "max_tokens": 2048,
                "cost_per_1k_input": 0.001,
                "cost_per_1k_output": 0.002,
                "capabilities": ["text", "analysis", "reasoning"],
                "enabled": True,
                "description": "Modelo oficial do sistema Bradax - único permitido para testes",
                "version": "2025-08",
                "rate_limits": {
                    "requests_per_minute": 60,
                    "requests_per_day": 1000,
                    "tokens_per_day": 50000
                }
            },
            {
                # ❌ MODELO NÃO PERMITIDO - Para testes de rejeição
                "model_id": "gpt-4-turbo",
                "name": "GPT-4 Turbo",
                "provider": "openai",
                "max_tokens": 4096,
                "cost_per_1k_input": 0.01,
                "cost_per_1k_output": 0.03,
                "capabilities": ["text", "analysis", "vision"],
                "enabled": False,  # Desabilitado intencionalmente
                "description": "Modelo não permitido nos testes - deve ser rejeitado",
                "version": "2024-04"
            },
            {
                # ❌ OUTRO MODELO NÃO PERMITIDO
                "model_id": "gpt-3.5-turbo",
                "name": "GPT-3.5 Turbo",
                "provider": "openai", 
                "max_tokens": 4096,
                "cost_per_1k_input": 0.0015,
                "cost_per_1k_output": 0.002,
                "capabilities": ["text"],
                "enabled": True,  # Habilitado mas não está em allowed_llms
                "description": "Modelo habilitado mas não permitido para o projeto teste"
            }
        ]
    
    # === TELEMETRIA REAL (sem mocks) ===
    
    @staticmethod
    def get_real_machine_telemetry() -> Dict[str, Any]:
        """
        Coleta telemetria REAL da máquina atual usando psutil.
        Exatamente como o SDK faria - sem mocks.
        """
        try:
            if PSUTIL_AVAILABLE:
                # Coleta dados reais via psutil
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/' if os.name != 'nt' else 'C:')
                
                return {
                    # 🖥️ Hardware Metrics
                    "cpu_percent": round(cpu_percent, 2),
                    "memory_percent": round(memory.percent, 2),
                    "memory_used_gb": round(memory.used / (1024**3), 2),
                    "memory_total_gb": round(memory.total / (1024**3), 2),
                    "disk_percent": round((disk.used / disk.total) * 100, 2),
                    "disk_used_gb": round(disk.used / (1024**3), 2),
                    "disk_total_gb": round(disk.total / (1024**3), 2),
                    
                    # 👤 User Context
                    "username": os.getenv('USERNAME') or os.getenv('USER') or 'test_user',
                    "process_id": os.getpid(),
                    "thread_id": f"thread_{hash(os.getpid()) % 10000}",
                    
                    # 🏷️ Platform Info
                    "platform": platform.system(),
                    "platform_version": platform.version(),
                    "python_version": platform.python_version(),
                    "architecture": platform.architecture()[0],
                    "hostname": platform.node(),
                    
                    # ⏰ Temporal Context
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "timezone": str(datetime.now().astimezone().tzinfo),
                    
                    # 📊 Additional Context
                    "sdk_version": "1.0.0-test",
                    "telemetry_collection_method": "psutil_real"
                }
            else:
                # Fallback mínimo se psutil não estiver disponível
                return BradaxTestFixtures._get_minimal_telemetry()
                
        except Exception as e:
            print(f"⚠️ Erro na coleta de telemetria: {e}")
            return BradaxTestFixtures._get_minimal_telemetry()
    
    @staticmethod
    def _get_minimal_telemetry() -> Dict[str, Any]:
        """Telemetria mínima quando psutil não está disponível"""
        return {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_percent": 0.0,
            "username": os.getenv('USERNAME') or os.getenv('USER') or 'test_user',
            "process_id": os.getpid(),
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "telemetry_collection_error": "psutil_unavailable_or_error",
            "sdk_version": "1.0.0-test"
        }
    
    # === REQUESTS DE TESTE ===
    
    @staticmethod
    def get_valid_llm_request() -> Dict[str, Any]:
        """
        Request completamente válida para o sistema.
        Deve passar por todas as validações e chegar ao gpt-4.1-nano.
        """
        return {
            "model": "gpt-4.1-nano",
            "messages": [
                {
                    "role": "user",
                    "content": "Explain quantum computing in simple terms. Keep it under 100 words."
                }
            ],
            "max_tokens": 150,
            "temperature": 0.7,
            "project_token": BradaxTestFixtures.get_valid_project_token(),
            "telemetry": BradaxTestFixtures.get_real_machine_telemetry(),
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user_context": {
                "sdk_version": "1.0.0-test",
                "client_type": "test_client"
            }
        }
    
    @staticmethod
    def get_blocked_python_request() -> Dict[str, Any]:
        """
        Request que deve ser bloqueada pelo guardrail 'no_python_code'.
        Contém código Python que deve triggerar o bloqueio.
        """
        request = BradaxTestFixtures.get_valid_llm_request()
        request["messages"][0]["content"] = """
        Please write a Python function to process user data:
        
        def process_user_data(users):
            import pandas as pd
            from datetime import datetime
            
            return pd.DataFrame(users).to_csv()
        
        Make sure to include proper error handling.
        """
        return request
    
    @staticmethod
    def get_blocked_personal_data_request() -> Dict[str, Any]:
        """
        Request que deve ser bloqueada pelo guardrail 'no_personal_data'.
        Contém dados pessoais (SSN/CPF) que devem ser detectados.
        """
        request = BradaxTestFixtures.get_valid_llm_request()
        request["messages"][0]["content"] = """
        Process this user information:
        
        Name: John Doe
        SSN: 123-45-6789
        CPF: 12345678901
        
        Generate a summary report for this person.
        """
        return request
    
    @staticmethod
    def get_multiple_guardrails_violation_request() -> Dict[str, Any]:
        """
        Request que viola múltiplos guardrails simultaneamente.
        Deve ser bloqueada e gerar múltiplos logs.
        """
        request = BradaxTestFixtures.get_valid_llm_request()
        request["messages"][0]["content"] = """
        Write Python code to process this personal data:
        
        def process_sensitive_data():
            import pandas as pd
            
            users = [
                {'name': 'John', 'ssn': '123-45-6789'},
                {'name': 'Jane', 'cpf': '98765432100'}
            ]
            
            return pd.DataFrame(users)
        
        Make sure to handle credit card numbers like 4532-1234-5678-9012 properly.
        """
        return request
    
    @staticmethod
    def get_request_without_telemetry() -> Dict[str, Any]:
        """
        Request sem telemetria - deve ser rejeitada com HTTP 400.
        Simula SDK mal configurado ou tentativa de bypass.
        """
        request = BradaxTestFixtures.get_valid_llm_request()
        del request["telemetry"]  # Remove telemetria obrigatória
        return request
    
    @staticmethod
    def get_request_incomplete_telemetry() -> Dict[str, Any]:
        """
        Request com telemetria incompleta - campos obrigatórios ausentes.
        Deve ser rejeitada pois não atende aos requisitos mínimos.
        """
        request = BradaxTestFixtures.get_valid_llm_request()
        # Telemetria incompleta - faltam campos críticos
        request["telemetry"] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            # Faltam: cpu_percent, memory_percent, username, etc.
        }
        return request
    
    @staticmethod  
    def get_unauthorized_llm_request() -> Dict[str, Any]:
        """
        Request para LLM não permitido no projeto.
        Token válido mas modelo fora da lista allowed_llms.
        """
        request = BradaxTestFixtures.get_valid_llm_request()
        request["model"] = "gpt-4-turbo"  # NÃO está em allowed_llms
        return request
    
    @staticmethod
    def get_request_blocked_project() -> Dict[str, Any]:
        """
        Request com token de projeto bloqueado.
        Token existe mas projeto tem status != 'active'.
        """
        request = BradaxTestFixtures.get_valid_llm_request()
        request["project_token"] = "bradax_token_blocked_project_xyz"
        return request
    
    # === LOGS ESPERADOS ===
    
    @staticmethod
    def get_expected_success_telemetry_log() -> Dict[str, Any]:
        """
        Log de telemetria esperado após request bem-sucedida.
        Baseado na estrutura TelemetryData analisada.
        """
        machine_metrics = BradaxTestFixtures.get_real_machine_telemetry()
        
        return {
            "telemetry_id": str(uuid.uuid4()),
            "project_id": "proj_test_bradax_2025",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "llm_request_complete",
            
            # Request Context
            "request_id": str(uuid.uuid4()),
            "user_id": machine_metrics["username"],
            "endpoint": "/llm/invoke", 
            "method": "POST",
            
            # Performance Metrics
            "status_code": 200,
            "response_time_ms": 1250.5,  # Tempo típico para gpt-4.1-nano
            "request_size": 156,
            "response_size": 234,
            
            # LLM Specifics
            "model_used": "gpt-4.1-nano",
            "tokens_used": 175,
            "cost_usd": 0.002,
            
            # Security
            "guardrails_applied": ["default_content_filter"],
            
            # System Context
            "system_info": machine_metrics,
            
            # Metadata
            "metadata": {
                "sdk_version": "1.0.0-test",
                "request_successful": True,
                "client_type": "test_client"
            }
        }
    
    @staticmethod
    def get_expected_guardrail_violation_log() -> Dict[str, Any]:
        """
        Log esperado quando guardrail customizado é violado.
        Baseado na estrutura GuardrailData analisada.
        """
        return {
            "event_id": str(uuid.uuid4()),
            "project_id": "proj_test_bradax_2025",
            "guardrail_name": "no_python_code",
            "action": "block",
            "content_hash": f"sha256:{hash('python code content') % 1000000:06d}",
            "triggered_at": datetime.utcnow().isoformat() + "Z",
            "details": {
                "matched_pattern": r"(python|def\s+\w+|import\s+\w+)",
                "violation_count": 3,
                "blocked_content_snippet": "def process_user_data():",
                "project_token_prefix": BradaxTestFixtures.get_valid_project_token()[:15] + "...",
                "user_context": BradaxTestFixtures.get_real_machine_telemetry()["username"],
                "severity": "high",
                "category": "code_injection"
            }
        }
    
    @staticmethod
    def get_expected_error_log() -> Dict[str, Any]:
        """Log de telemetria para requests que falharam"""
        return {
            "telemetry_id": str(uuid.uuid4()),
            "project_id": "proj_test_bradax_2025",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "error",
            
            # Error Context
            "status_code": 403,
            "error_type": "AuthenticationError",
            "error_message": "Invalid project token",
            "error_code": "ERR_AUTH_001",
            
            # System Context  
            "system_info": BradaxTestFixtures.get_real_machine_telemetry(),
            
            "metadata": {
                "request_rejected": True,
                "rejection_reason": "invalid_token"
            }
        }

# === CONFIGURAÇÃO DE TESTE ===
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_DATA_DIR.mkdir(exist_ok=True)


# === PROJETOS DE TESTE ===
TEST_PROJECTS = {
    "proj_valid": {
        "project_id": "proj_valid",
        "name": "Projeto Teste Válido",
        "api_key_hash": "hash_da_chave_valida_12345",
        "config": {
            "model": "gpt-4o-mini",
            "allowed_llms": ["gpt-4o-mini", "gpt-4o"],
            "max_tokens_per_day": 10000,
            "max_requests_per_minute": 10
        },
        "status": "active",
        "created_at": "2025-01-01T10:00:00Z",
        "updated_at": "2025-01-01T10:00:00Z",
        "tags": ["test", "development"]
    },
    "proj_restricted": {
        "project_id": "proj_restricted", 
        "name": "Projeto Restrito",
        "api_key_hash": "hash_da_chave_restrita_67890",
        "config": {
            "model": "gpt-4o-mini",
            "allowed_llms": ["gpt-4o-mini"],  # Apenas mini permitido
            "max_tokens_per_day": 1000,
            "max_requests_per_minute": 2
        },
        "status": "active",
        "created_at": "2025-01-01T10:00:00Z", 
        "updated_at": "2025-01-01T10:00:00Z",
        "tags": ["test", "restricted"]
    },
    "proj_inactive": {
        "project_id": "proj_inactive",
        "name": "Projeto Inativo",
        "api_key_hash": "hash_da_chave_inativa_11111",
        "config": {
            "model": "gpt-4o",
            "allowed_llms": ["gpt-4o", "gpt-4o-mini"]
        },
        "status": "inactive",  # Status inativo
        "created_at": "2025-01-01T10:00:00Z",
        "updated_at": "2025-01-01T10:00:00Z", 
        "tags": ["test", "inactive"]
    }
}

# === TOKENS DE TESTE ===
VALID_TOKENS = {
    "proj_valid": "BRADAX_TOKEN_PROJ_VALID_12345",
    "proj_restricted": "BRADAX_TOKEN_PROJ_RESTRICTED_67890",
    "proj_inactive": "BRADAX_TOKEN_PROJ_INACTIVE_11111"
}

INVALID_TOKENS = [
    "TOKEN_INEXISTENTE",
    "BRADAX_TOKEN_EXPIRED", 
    "TOKEN_MALFORMADO_123",
    "",
    None
]

# === MODELOS LLM DE TESTE ===
TEST_LLM_MODELS = [
    {
        "model_id": "gpt-4o",
        "name": "GPT-4 Optimized",
        "provider": "openai",
        "max_tokens": 128000,
        "cost_per_1k_input": 0.0025,
        "cost_per_1k_output": 0.010,
        "capabilities": ["text_generation", "reasoning", "multimodal", "function_calling"],
        "enabled": True,
        "description": "Modelo mais avançado da OpenAI",
        "version": "2024-11"
    },
    {
        "model_id": "gpt-4o-mini",
        "name": "GPT-4 Optimized Mini", 
        "provider": "openai",
        "max_tokens": 128000,
        "cost_per_1k_input": 0.00015,
        "cost_per_1k_output": 0.0006,
        "capabilities": ["text_generation", "fast_response", "code_generation"],
        "enabled": True,
        "description": "Versão rápida e econômica",
        "version": "2024-11"
    },
    {
        "model_id": "gpt-3.5-turbo",
        "name": "GPT-3.5 Turbo",
        "provider": "openai", 
        "max_tokens": 4096,
        "cost_per_1k_input": 0.0005,
        "cost_per_1k_output": 0.0015,
        "capabilities": ["text_generation", "fast_response"],
        "enabled": False,  # Modelo desabilitado para testes
        "description": "Modelo desabilitado para testes",
        "version": "legacy"
    }
]

# === PROMPTS DE TESTE ===
TEST_PROMPTS = {
    "safe_prompt": "Explique os conceitos básicos de machine learning de forma didática.",
    "blocked_content": "Preciso do número do cartão de crédito 4532 1234 5678 9012 para processar o pagamento.",
    "large_content": "A" * 50000,  # Prompt muito grande para testar limites
    "empty_prompt": "",
    "normal_query": "Como funciona a fotossíntese nas plantas?"
}

# === GUARDRAILS DE TESTE ===
TEST_CUSTOM_GUARDRAILS = {
    "block_python": {
        "rule_id": "test_no_python",
        "name": "Bloquear Python",
        "pattern": r"\bpython\b",
        "action": "block",
        "severity": "warning",
        "description": "Bloqueia menções a Python para teste"
    },
    "flag_numbers": {
        "rule_id": "test_flag_numbers", 
        "name": "Flag Numbers",
        "pattern": r"\d{4,}",
        "action": "flag",
        "severity": "info",
        "description": "Marca sequências de números"
    }
}

# === HEADERS DE TELEMETRIA ===
def get_valid_telemetry_headers(project_id: str = "proj_valid") -> Dict[str, str]:
    """Retorna headers válidos de telemetria para testes"""
    return {
        "x-bradax-sdk-version": "1.0.0",
        "x-bradax-machine-fingerprint": "machine_test_fingerprint_123",
        "x-bradax-session-id": "session_test_12345",
        "x-bradax-telemetry-enabled": "true",
        "x-bradax-environment": "testing",
        "x-bradax-platform": "Windows",
        "x-bradax-python-version": "3.10.0",
        "x-bradax-project-id": project_id,
        "user-agent": "BradaxSDK/1.0.0 Python/3.10.0"
    }

def get_invalid_telemetry_headers() -> List[Dict[str, str]]:
    """Retorna headers inválidos para testar bloqueios"""
    base_headers = get_valid_telemetry_headers()
    
    invalid_variants = []
    
    # Falta header crítico
    missing_critical = base_headers.copy()
    del missing_critical["x-bradax-telemetry-enabled"]
    invalid_variants.append(missing_critical)
    
    # Telemetria desabilitada
    disabled_telemetry = base_headers.copy()
    disabled_telemetry["x-bradax-telemetria-enabled"] = "false"
    invalid_variants.append(disabled_telemetry)
    
    # Headers vazios
    invalid_variants.append({})
    
    # Machine fingerprint faltando
    missing_fingerprint = base_headers.copy()
    del missing_fingerprint["x-bradax-machine-fingerprint"]
    invalid_variants.append(missing_fingerprint)
    
    return invalid_variants

# === UTILIDADES DE SETUP ===

def create_test_data_files():
    """Cria arquivos de dados de teste no diretório correto"""
    
    # Criar projects.json
    projects_data = {"projects": list(TEST_PROJECTS.values())}
    with open(TEST_DATA_DIR / "projects.json", "w", encoding="utf-8") as f:
        json.dump(projects_data, f, indent=2, ensure_ascii=False)
    
    # Criar llm_models.json
    with open(TEST_DATA_DIR / "llm_models.json", "w", encoding="utf-8") as f:
        json.dump(TEST_LLM_MODELS, f, indent=2, ensure_ascii=False)
    
    # Criar telemetry.json vazio
    with open(TEST_DATA_DIR / "telemetry.json", "w", encoding="utf-8") as f:
        json.dump([], f)
        
    # Criar guardrails.json vazio  
    with open(TEST_DATA_DIR / "guardrails.json", "w", encoding="utf-8") as f:
        json.dump([], f)

def cleanup_test_data_files():
    """Remove arquivos de teste"""
    for file_path in TEST_DATA_DIR.glob("*.json"):
        file_path.unlink(missing_ok=True)

# === PAYLOADS DE TESTE ===

def get_valid_invoke_payload(
    model: str = "gpt-4o-mini", 
    prompt: str = None,
    project_id: str = "proj_valid"
) -> Dict[str, Any]:
    """Retorna payload válido para teste de invoke"""
    return {
        "operation": "chat",
        "model": model,
        "payload": {
            "prompt": prompt or TEST_PROMPTS["safe_prompt"],
            "model": model,
            "max_tokens": 100,
            "temperature": 0.7
        },
        "project_id": project_id,
        "custom_guardrails": {}
    }

def get_blocked_invoke_payload(
    model: str = "gpt-4o-mini",
    project_id: str = "proj_valid"
) -> Dict[str, Any]:
    """Retorna payload que deve ser bloqueado por guardrails"""
    return {
        "operation": "chat", 
        "model": model,
        "payload": {
            "prompt": TEST_PROMPTS["blocked_content"],
            "model": model,
            "max_tokens": 100,
            "temperature": 0.7
        },
        "project_id": project_id,
        "custom_guardrails": {}
    }

def get_unauthorized_model_payload(
    project_id: str = "proj_restricted"
) -> Dict[str, Any]:
    """Retorna payload com modelo não autorizado para o projeto"""
    return {
        "operation": "chat",
        "model": "gpt-4o",  # proj_restricted só permite gpt-4o-mini
        "payload": {
            "prompt": TEST_PROMPTS["safe_prompt"], 
            "model": "gpt-4o",
            "max_tokens": 100,
            "temperature": 0.7
        },
        "project_id": project_id,
        "custom_guardrails": {}
    }

# === VALIDADORES DE RESPOSTA ===

def validate_telemetry_log(log_entry: Dict[str, Any]) -> bool:
    """Valida se entrada de telemetria contém campos obrigatórios"""
    required_fields = [
        "event_id", "timestamp", "project_id", "event_type",
        "model_used", "tokens_consumed", "duration_ms", "status_code"
    ]
    return all(field in log_entry for field in required_fields)

def validate_project_data(project_data: Dict[str, Any]) -> bool:
    """Valida se dados do projeto estão corretos"""
    required_fields = ["project_id", "name", "config", "status"]
    if not all(field in project_data for field in required_fields):
        return False
        
    config = project_data.get("config", {})
    required_config = ["model", "allowed_llms"]
    return all(field in config for field in required_config)


# === EXPECTATIVAS DE TESTE ===

# Códigos HTTP esperados para diferentes cenários
HTTP_EXPECTATIONS = {
    "valid_request": 200,
    "invalid_token": 403, 
    "missing_telemetry": 403,
    "blocked_content": 400,
    "unauthorized_model": 403,
    "inactive_project": 403,
    "disabled_model": 403
}

# Mensagens esperadas nos logs
LOG_EXPECTATIONS = {
    "telemetry_violation": "VIOLAÇÃO DE SEGURANÇA",
    "auth_failure": "Token de projeto inválido", 
    "model_unauthorized": "Modelo não autorizado",
    "guardrail_blocked": "Conteúdo bloqueado",
    "project_inactive": "Projeto inativo"
}

if __name__ == "__main__":
    # Teste das fixtures expandidas
    print("🧪 Testando fixtures expandidas...")
    
    # Testar coleta de telemetria real
    telemetry = BradaxTestFixtures.get_real_machine_telemetry()
    print(f"✅ Telemetria coletada: CPU={telemetry.get('cpu_percent')}%, RAM={telemetry.get('memory_percent')}%")
    
    # Testar manager de dados
    with BradaxTestDataManager() as manager:
        print(f"✅ Test data manager configurado: {len(manager.get_config_dict())} arquivos")
        
        # Validar integridade
        integrity = manager.validate_json_integrity()
        print(f"✅ Integridade JSON: {all(integrity.values())}")
    
    # Testar validadores
    test_content = "def process_data(): import pandas as pd"
    python_detected = TestValidators.validate_guardrail_trigger(test_content, "no_python_code")
    print(f"✅ Guardrail python detectado: {python_detected}")
    
    print("🎯 Fixtures completas e prontas para uso!")


class BradaxTestDataManager:
    """
    Gerenciador de dados de teste em arquivos temporários.
    Baseado na análise do JsonStorage com transações ACID.
    
    Simula o ambiente real do sistema com arquivos JSON controlados.
    """
    
    def __init__(self, temp_dir: Optional[Path] = None):
        self.temp_dir = temp_dir or Path(tempfile.mkdtemp(prefix="bradax_test_"))
        self.temp_dir.mkdir(exist_ok=True)
        
        # Arquivos de dados baseados na estrutura real
        self.projects_file = self.temp_dir / "projects.json"
        self.llm_models_file = self.temp_dir / "llm_models.json"
        self.telemetry_file = self.temp_dir / "telemetry.json"
        self.guardrails_file = self.temp_dir / "guardrails.json"
        self.system_file = self.temp_dir / "system_info.json"
        
        print(f"� Test data manager criado: {self.temp_dir}")
    
    def setup_test_data(self):
        """
        Configura todos os arquivos de teste com dados realistas.
        Baseado nas estruturas ProjectData, LLMModelInfo identificadas.
        """
        
        # 📋 Arquivo de projetos (múltiplos cenários)
        projects_data = [
            BradaxTestFixtures.get_test_project_data(),      # Projeto válido
            BradaxTestFixtures.get_blocked_project_data(),   # Projeto bloqueado
            BradaxTestFixtures.get_limited_project_data()    # Projeto com LLMs limitados
        ]
        self._write_json_file(self.projects_file, projects_data)
        
        # 🤖 Arquivo de modelos LLM
        self._write_json_file(self.llm_models_file, BradaxTestFixtures.get_llm_models_data())
        
        # 📊 Arquivo de telemetria (inicialmente vazio, será populado pelos testes)
        self._write_json_file(self.telemetry_file, [])
        
        # 🛡️ Arquivo de guardrails (inicialmente vazio, será populado por violações)
        self._write_json_file(self.guardrails_file, [])
        
        # ⚙️ Arquivo de sistema (informações da máquina de teste)
        system_info = {
            "system_id": str(uuid.uuid4()),
            "created_at": datetime.utcnow().isoformat() + "Z",
            "test_environment": True,
            "machine_info": BradaxTestFixtures.get_real_machine_telemetry()
        }
        self._write_json_file(self.system_file, system_info)
        
        print(f"✅ Dados de teste configurados:")
        print(f"  📋 Projects: {len(projects_data)} projetos")
        print(f"  🤖 LLM Models: {len(BradaxTestFixtures.get_llm_models_data())} modelos")
        print(f"  � Data dir: {self.temp_dir}")
        
        return self
    
    def _write_json_file(self, file_path: Path, data: Any):
        """Escreve dados em arquivo JSON com formatação limpa"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def read_json_file(self, file_path: Path) -> Any:
        """Lê dados de arquivo JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as e:
            print(f"❌ Erro ao ler JSON {file_path}: {e}")
            return []
    
    def get_telemetry_logs(self) -> List[Dict[str, Any]]:
        """Retorna logs de telemetria gravados pelos testes"""
        return self.read_json_file(self.telemetry_file)
    
    def get_guardrail_logs(self) -> List[Dict[str, Any]]:
        """Retorna logs de guardrails gravados pelos testes"""
        return self.read_json_file(self.guardrails_file)
    
    def cleanup(self):
        """Remove arquivos temporários"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            print(f"🧹 Dados de teste removidos: {self.temp_dir}")
    
    def get_config_dict(self) -> Dict[str, str]:
        """
        Retorna configuração para ser injetada nos testes.
        Simula as configurações reais do sistema.
        """
        return {
            "data_dir": str(self.temp_dir),
            "projects_file": str(self.projects_file),
            "llm_models_file": str(self.llm_models_file),
            "telemetry_file": str(self.telemetry_file),
            "guardrails_file": str(self.guardrails_file),
            "system_file": str(self.system_file)
        }
    
    def __enter__(self):
        """Context manager - setup automático"""
        return self.setup_test_data()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager - cleanup automático"""
        self.cleanup()


class TestValidators:
    """Validadores para verificar se os testes estão funcionando corretamente"""
    
    @staticmethod
    def validate_guardrail_trigger(content: str, guardrail_name: str) -> bool:
        """
        Valida se conteúdo deve triggar o guardrail especificado.
        Baseado nos padrões definidos nas fixtures.
        """
        patterns = {
            "no_python_code": r"(python|def\s+\w+|import\s+\w+|from\s+\w+\s+import)",
            "no_personal_data": r"(\b\d{3}-\d{2}-\d{4}\b|\b\d{11}\b|\bcpf\b|\bssn\b)",
            "no_financial_data": r"(\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b|card\s+number)"
        }
        
        import re
        pattern = patterns.get(guardrail_name, "")
        return bool(re.search(pattern, content, re.IGNORECASE)) if pattern else False


# Instância global das fixtures para importação simples
fixtures = BradaxTestFixtures()
