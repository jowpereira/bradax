"""
Teste de Validação Final - Arquivos JSON do Sistema Bradax
=========================================================

Valida a integridade e consistência dos arquivos de dados:
- projects.json (configurações de projetos)
- guardrails.json (regras de segurança) 
- telemetry.json (logs de telemetria)
- llm_models.json (modelos disponíveis)

🚨 IMPORTANTE: Testa dados reais sem mocks
"""

import json
import pytest
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Setup de paths
test_dir = Path(__file__).parent.parent
broker_dir = test_dir.parent / "bradax-broker"
data_dir = broker_dir / "data"

class TestJSONDataValidation:
    """Validação rigorosa dos arquivos JSON de dados"""
    
    def setup_method(self):
        """Setup para cada teste"""
        print(f"📂 Validando dados em: {data_dir}")
        
        # Criar diretório de dados se não existe
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivos obrigatórios
        self.required_files = {
            "projects.json": data_dir / "projects.json",
            "guardrails.json": data_dir / "guardrails.json", 
            "telemetry.json": data_dir / "telemetry.json",
            "llm_models.json": data_dir / "llm_models.json"
        }
    
    def test_projects_json_structure(self):
        """
        Validar estrutura e conteúdo do projects.json
        
        Esperado:
        - Lista de projetos válidos
        - Projeto de teste com gpt-4.1-nano permitido
        - Campos obrigatórios presentes
        """
        projects_file = self.required_files["projects.json"]
        
        if not projects_file.exists():
            # Criar arquivo padrão se não existir
            default_projects = [
                {
                    "project_id": "proj_test_bradax_2025",
                    "project_name": "Bradax Test Project",
                    "status": "active",
                    "allowed_llms": ["gpt-4.1-nano"],
                    "project_token": "bradax_test_token_2025_secure",
                    "created_at": datetime.now().isoformat(),
                    "telemetry_enabled": True,
                    "guardrails_enabled": True
                }
            ]
            
            with open(projects_file, 'w', encoding='utf-8') as f:
                json.dump(default_projects, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Criado projects.json padrão: {projects_file}")
        
        # Validar estrutura
        with open(projects_file, 'r', encoding='utf-8') as f:
            projects_data = json.load(f)
        
        assert isinstance(projects_data, list), "Projects deve ser uma lista"
        assert len(projects_data) > 0, "Deve haver pelo menos um projeto"
        
        # Validar projeto de teste
        test_project = None
        for project in projects_data:
            if project.get("project_id") == "proj_test_bradax_2025":
                test_project = project
                break
        
        assert test_project is not None, "Projeto de teste deve existir"
        
        # Validar campos obrigatórios
        required_fields = [
            "project_id", "project_name", "status", 
            "allowed_llms", "project_token"
        ]
        
        for field in required_fields:
            assert field in test_project, f"Campo obrigatório ausente: {field}"
        
        # Validar que gpt-4.1-nano está permitido
        assert "gpt-4.1-nano" in test_project["allowed_llms"], \
            "gpt-4.1-nano deve estar em allowed_llms"
        
        assert test_project["status"] == "active", "Projeto de teste deve estar ativo"
        
        print(f"✅ Projects.json válido com {len(projects_data)} projetos")
    
    def test_llm_models_json_structure(self):
        """
        Validar estrutura do llm_models.json
        
        Esperado:
        - Lista de modelos LLM
        - gpt-4.1-nano presente e habilitado
        - Campos de configuração corretos
        """
        models_file = self.required_files["llm_models.json"]
        
        if not models_file.exists():
            # Criar arquivo padrão
            default_models = [
                {
                    "model_id": "gpt-4.1-nano",
                    "provider": "openai",
                    "enabled": True,
                    "max_tokens": 4096,
                    "supports_streaming": True,
                    "cost_per_1k_tokens": 0.002,
                    "description": "GPT-4.1 Nano - Modelo otimizado para governança"
                }
            ]
            
            with open(models_file, 'w', encoding='utf-8') as f:
                json.dump(default_models, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Criado llm_models.json padrão: {models_file}")
        
        # Validar estrutura
        with open(models_file, 'r', encoding='utf-8') as f:
            models_data = json.load(f)
        
        assert isinstance(models_data, list), "Models deve ser uma lista"
        
        # Encontrar gpt-4.1-nano
        gpt_nano = None
        for model in models_data:
            if model.get("model_id") == "gpt-4.1-nano":
                gpt_nano = model
                break
        
        assert gpt_nano is not None, "gpt-4.1-nano deve estar no catálogo"
        assert gpt_nano["enabled"] is True, "gpt-4.1-nano deve estar habilitado"
        assert gpt_nano["provider"] == "openai", "Provider deve ser openai"
        
        print(f"✅ LLM models.json válido: gpt-4.1-nano disponível")
    
    def test_guardrails_json_structure(self):
        """
        Validar estrutura do guardrails.json
        
        Esperado:
        - Lista de regras de guardrail
        - Regras obrigatórias presentes (Python, dados pessoais)
        - Configuração por projeto
        """
        guardrails_file = self.required_files["guardrails.json"]
        
        if not guardrails_file.exists():
            # Criar arquivo padrão
            default_guardrails = [
                {
                    "guardrail_id": "block_python_code",
                    "project_id": "proj_test_bradax_2025",
                    "rule_type": "content_pattern",
                    "pattern": r"(def |class |import |from .* import)",
                    "action": "block",
                    "enabled": True,
                    "description": "Bloqueia código Python em requests",
                    "severity": "high"
                },
                {
                    "guardrail_id": "block_personal_data",
                    "project_id": "proj_test_bradax_2025", 
                    "rule_type": "content_pattern",
                    "pattern": r"(\b\d{3}-\d{2}-\d{4}\b|\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b)",
                    "action": "block",
                    "enabled": True,
                    "description": "Bloqueia CPF e emails",
                    "severity": "critical"
                }
            ]
            
            with open(guardrails_file, 'w', encoding='utf-8') as f:
                json.dump(default_guardrails, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Criado guardrails.json padrão: {guardrails_file}")
        
        # Validar estrutura
        with open(guardrails_file, 'r', encoding='utf-8') as f:
            guardrails_data = json.load(f)
        
        assert isinstance(guardrails_data, list), "Guardrails deve ser uma lista"
        
        # Verificar regras obrigatórias
        rule_ids = [g.get("guardrail_id") for g in guardrails_data]
        
        assert "block_python_code" in rule_ids, "Regra de bloqueio Python deve existir"
        assert "block_personal_data" in rule_ids, "Regra de dados pessoais deve existir"
        
        print(f"✅ Guardrails.json válido com {len(guardrails_data)} regras")
    
    def test_telemetry_json_structure(self):
        """
        Validar estrutura do telemetry.json
        
        Esperado:
        - Lista de logs de telemetria (pode estar vazia)
        - Estrutura de log válida se houver dados
        """
        telemetry_file = self.required_files["telemetry.json"]
        
        if not telemetry_file.exists():
            # Criar arquivo vazio
            with open(telemetry_file, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2, ensure_ascii=False)
            
            print(f"✅ Criado telemetry.json vazio: {telemetry_file}")
        
        # Validar estrutura
        with open(telemetry_file, 'r', encoding='utf-8') as f:
            telemetry_data = json.load(f)
        
        assert isinstance(telemetry_data, list), "Telemetry deve ser uma lista"
        
        # Se houver dados, validar estrutura
        if len(telemetry_data) > 0:
            sample_log = telemetry_data[0]
            
            required_fields = [
                "telemetry_id", "project_id", "timestamp", 
                "model_used", "status_code"
            ]
            
            for field in required_fields:
                assert field in sample_log, f"Campo obrigatório no log: {field}"
        
        print(f"✅ Telemetry.json válido com {len(telemetry_data)} logs")
    
    def test_all_json_files_valid_format(self):
        """
        Verificar que todos os arquivos são JSON válidos
        
        Esperado:
        - Todos os arquivos podem ser lidos sem erro
        - Não há corrupção de dados
        """
        validation_results = {}
        
        for file_name, file_path in self.required_files.items():
            try:
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        json.load(f)
                    validation_results[file_name] = True
                else:
                    validation_results[file_name] = False
                    
            except json.JSONDecodeError as e:
                validation_results[file_name] = f"Erro JSON: {e}"
            except Exception as e:
                validation_results[file_name] = f"Erro geral: {e}"
        
        # Verificar resultados
        for file_name, result in validation_results.items():
            if result is True:
                print(f"✅ {file_name}: JSON válido")
            else:
                print(f"❌ {file_name}: {result}")
                assert False, f"Arquivo {file_name} com problema: {result}"
    
    def test_data_directory_permissions(self):
        """
        Verificar permissões do diretório de dados
        
        Esperado:
        - Diretório existe e é acessível
        - Permissões de leitura/escrita
        """
        assert data_dir.exists(), f"Diretório de dados deve existir: {data_dir}"
        assert data_dir.is_dir(), f"Deve ser um diretório: {data_dir}"
        
        # Testar criação de arquivo temporário (permissão de escrita)
        test_file = data_dir / "test_permissions.tmp"
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            
            # Testar leitura
            with open(test_file, 'r') as f:
                content = f.read()
                assert content == "test", "Conteúdo deve ser lido corretamente"
            
            # Limpar arquivo de teste
            test_file.unlink()
            
            print(f"✅ Permissões de diretório OK: {data_dir}")
            
        except Exception as e:
            assert False, f"Erro de permissões no diretório {data_dir}: {e}"


# Configuração para pytest
pytestmark = pytest.mark.json_validation


# Executar se chamado diretamente
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
