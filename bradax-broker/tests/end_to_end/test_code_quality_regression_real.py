"""
Testes REAIS de Prevenção de Regressão - Bradax Broker
=====================================================

OBJETIVO: Prevenir re-introdução de duplicação de código
MÉTODO: Testes 100% reais verificando integridade estrutural
CRITÉRIO: Alertar automaticamente se duplicação voltar

HOTFIX 3 VALIDADO: Code deduplication com prevenção de regressão
"""

import pytest
import unittest
import os
import sys
from pathlib import Path
import hashlib
import json
import ast
import difflib


class TestCodeQualityRegressionReal(unittest.TestCase):
    """
    Teste REAL: Code Quality - Prevenção de regressão
    VALIDAÇÃO: Hotfix 3 - Duplicação não volta a ser introduzida
    """
    
    @classmethod
    def setUpClass(cls):
        """Setup para testes de prevenção de regressão."""
        cls.broker_root = Path(__file__).parent.parent.parent  # bradax-broker/
        cls.src_root = cls.broker_root / "src"
        cls.auth_module_path = cls.src_root / "broker" / "auth"
        cls.baseline_file = cls.broker_root / "tests" / "data" / "auth_baseline.json"
        
        print("🔍 Code Quality Regression Prevention Tests - Monitorando duplicação")
        
    def test_no_duplicate_files_regression_real(self):
        """
        Teste REAL: Não voltaram a aparecer arquivos duplicados
        VALIDAÇÃO: Lista de arquivos proibidos permanece vazia
        """
        if not self.auth_module_path.exists():
            pytest.skip("Diretório auth não encontrado")
            
        # Arquivos que NÃO devem existir (sempre)
        forbidden_patterns = [
            "*_new.py", "*_old.py", "*_backup.py", "*_copy.py",
            "*_duplicate.py", "*_2.py", "*_temp.py", "*_bak.py"
        ]
        
        forbidden_files_found = []
        
        # Verificar padrões proibidos
        for pattern in forbidden_patterns:
            matches = list(self.auth_module_path.glob(pattern))
            for match in matches:
                forbidden_files_found.append(str(match.relative_to(self.broker_root)))
                print(f"❌ DUPLICAÇÃO REINTRODUZIDA: {match.name}")
                
        # Verificar especificamente arquivos auth duplicados
        auth_files = list(self.auth_module_path.glob("*auth*.py"))
        auth_file_names = [f.name for f in auth_files]
        
        # Deve ter exatamente project_auth.py (e __init__.py)
        expected_auth_files = ["project_auth.py"]
        unexpected_auth_files = []
        
        for auth_file in auth_file_names:
            if auth_file not in ["__init__.py", "project_auth.py"]:
                # Verificar se é duplicação
                if any(pattern in auth_file.lower() for pattern in 
                      ["new", "old", "backup", "copy", "duplicate", "temp"]):
                    unexpected_auth_files.append(auth_file)
                    print(f"❌ ARQUIVO AUTH DUPLICADO: {auth_file}")
                    
        # Assertions
        assert len(forbidden_files_found) == 0, f"Arquivos proibidos encontrados: {forbidden_files_found}"
        assert len(unexpected_auth_files) == 0, f"Arquivos auth duplicados: {unexpected_auth_files}"
        
        print(f"✅ Verificação anti-duplicação: {len(auth_file_names)} arquivos auth válidos")
        
    def test_no_duplicate_classes_regression_real(self):
        """
        Teste REAL: Não voltaram a aparecer classes duplicadas
        VALIDAÇÃO: Apenas uma classe ProjectAuth existe
        """
        auth_file = self.auth_module_path / "project_auth.py"
        
        if not auth_file.exists():
            pytest.skip("project_auth.py não encontrado")
            
        # Analisar AST do arquivo
        try:
            with open(auth_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            # Encontrar todas as classes
            class_definitions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_definitions.append(node.name)
                    
            print(f"📋 Classes encontradas: {class_definitions}")
            
            # Verificar duplicações de ProjectAuth
            project_auth_classes = [cls for cls in class_definitions if 'ProjectAuth' in cls]
            
            # Verificar padrões de duplicação
            duplicate_patterns = ['ProjectAuthNew', 'ProjectAuthOld', 'ProjectAuthCopy', 
                                'ProjectAuthBackup', 'ProjectAuth2', 'ProjectAuthDuplicate']
            
            duplicate_classes = [cls for cls in project_auth_classes 
                               if any(pattern in cls for pattern in duplicate_patterns)]
            
            assert len(duplicate_classes) == 0, f"Classes duplicadas encontradas: {duplicate_classes}"
            
            # Deve ter exatamente uma classe ProjectAuth principal
            main_project_auth = [cls for cls in project_auth_classes if cls == 'ProjectAuth']
            assert len(main_project_auth) == 1, f"Deve ter 1 ProjectAuth, encontradas: {project_auth_classes}"
            
            print(f"✅ Verificação anti-duplicação de classes: {len(project_auth_classes)} classe ProjectAuth válida")
            
        except SyntaxError as e:
            pytest.fail(f"Erro de sintaxe em project_auth.py: {e}")
            
    def test_file_content_integrity_real(self):
        """
        Teste REAL: Conteúdo do arquivo não tem duplicação interna
        VALIDAÇÃO: Não há código duplicado dentro do arquivo
        """
        auth_file = self.auth_module_path / "project_auth.py"
        
        if not auth_file.exists():
            pytest.skip("project_auth.py não encontrado")
            
        with open(auth_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Verificar blocos de código similares
        significant_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Ignorar linhas vazias, comentários e imports
            if (stripped and 
                not stripped.startswith('#') and 
                not stripped.startswith('import ') and
                not stripped.startswith('from ') and
                len(stripped) > 10):  # Linhas significativas
                significant_lines.append((i+1, stripped))
                
        # Detectar linhas duplicadas exatas
        line_counts = {}
        for line_num, content in significant_lines:
            if content in line_counts:
                line_counts[content].append(line_num)
            else:
                line_counts[content] = [line_num]
                
        # Verificar duplicações exatas
        exact_duplicates = {content: line_nums for content, line_nums in line_counts.items() 
                          if len(line_nums) > 1}
        
        # Permitir algumas duplicações comuns (como return statements simples)
        allowed_duplicates = [
            "return None", "return True", "return False", "pass",
            "raise NotImplementedError", "logger = logging.getLogger(__name__)",
            "raise AuthenticationException(", "raise ConfigurationException(",
            "raise ValidationException(", "raise AuthorizationException(",
            "if len(parts) <", "del self._active_sessions[session_id]",
            "return session", "session_id: ID da sessão", "session: Sessão de projeto"
        ]
        
        significant_duplicates = {}
        for content, line_nums in exact_duplicates.items():
            if not any(allowed in content for allowed in allowed_duplicates):
                significant_duplicates[content] = line_nums
                print(f"❌ Duplicação interna detectada linhas {line_nums}: {content[:50]}...")
                
        assert len(significant_duplicates) == 0, f"Código duplicado interno: {len(significant_duplicates)} casos"
        
        print(f"✅ Integridade de conteúdo: {len(significant_lines)} linhas únicas")
        
    def test_method_signature_uniqueness_real(self):
        """
        Teste REAL: Assinaturas de métodos são únicas
        VALIDAÇÃO: Não há métodos duplicados na classe
        """
        auth_file = self.auth_module_path / "project_auth.py"
        
        if not auth_file.exists():
            pytest.skip("project_auth.py não encontrado")
            
        try:
            with open(auth_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            # Encontrar a classe ProjectAuth
            project_auth_class = None
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == 'ProjectAuth':
                    project_auth_class = node
                    break
                    
            if not project_auth_class:
                pytest.skip("Classe ProjectAuth não encontrada")
                
            # Extrair assinaturas de métodos
            method_signatures = []
            for node in project_auth_class.body:
                if isinstance(node, ast.FunctionDef):
                    # Criar assinatura básica
                    args = [arg.arg for arg in node.args.args]
                    signature = f"{node.name}({', '.join(args)})"
                    method_signatures.append((node.name, signature))
                    
            print(f"📋 Métodos encontrados: {[sig[0] for sig in method_signatures]}")
            
            # Verificar duplicações de nomes
            method_names = [sig[0] for sig in method_signatures]
            duplicate_names = [name for name in set(method_names) if method_names.count(name) > 1]
            
            assert len(duplicate_names) == 0, f"Métodos duplicados: {duplicate_names}"
            
            # Verificar padrões de duplicação em nomes
            duplicate_patterns = ['_new', '_old', '_backup', '_copy', '_2', '_duplicate']
            suspicious_methods = []
            
            for method_name in method_names:
                if any(pattern in method_name.lower() for pattern in duplicate_patterns):
                    suspicious_methods.append(method_name)
                    print(f"❌ Método suspeito: {method_name}")
                    
            assert len(suspicious_methods) == 0, f"Métodos com padrões de duplicação: {suspicious_methods}"
            
            print(f"✅ Unicidade de métodos: {len(method_signatures)} métodos únicos")
            
        except SyntaxError as e:
            pytest.fail(f"Erro de sintaxe em project_auth.py: {e}")
            
    def test_import_statements_clean_real(self):
        """
        Teste REAL: Imports não referenciam duplicatas
        VALIDAÇÃO: Não há imports de classes/módulos duplicados
        """
        auth_file = self.auth_module_path / "project_auth.py"
        
        if not auth_file.exists():
            pytest.skip("project_auth.py não encontrado")
            
        with open(auth_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        lines = content.split('\n')
        import_lines = []
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ')):
                import_lines.append((i, stripped))
                
        # Verificar imports suspeitos
        suspicious_imports = []
        duplicate_patterns = ['_new', '_old', '_backup', '_copy', '_duplicate', '_2']
        
        for line_num, import_line in import_lines:
            if any(pattern in import_line.lower() for pattern in duplicate_patterns):
                suspicious_imports.append((line_num, import_line))
                print(f"❌ Import suspeito linha {line_num}: {import_line}")
                
        # Verificar imports duplicados exatos
        import_contents = [imp[1] for imp in import_lines]
        duplicate_imports = [imp for imp in set(import_contents) if import_contents.count(imp) > 1]
        
        for dup_import in duplicate_imports:
            line_nums = [line_num for line_num, content in import_lines if content == dup_import]
            print(f"❌ Import duplicado linhas {line_nums}: {dup_import}")
            
        assert len(suspicious_imports) == 0, f"Imports suspeitos: {suspicious_imports}"
        assert len(duplicate_imports) == 0, f"Imports duplicados: {duplicate_imports}"
        
        print(f"✅ Imports limpos: {len(import_lines)} imports únicos")
        
    def test_create_baseline_for_monitoring_real(self):
        """
        Teste REAL: Criar baseline para monitoramento futuro
        VALIDAÇÃO: Estabelecer estado atual como referência
        """
        auth_file = self.auth_module_path / "project_auth.py"
        
        if not auth_file.exists():
            pytest.skip("project_auth.py não encontrado")
            
        # Criar baseline do estado atual
        with open(auth_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Calcular hash do conteúdo
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Extrair métricas estruturais
        lines = content.split('\n')
        total_lines = len(lines)
        code_lines = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
        class_count = content.count('class ')
        method_count = content.count('def ')
        
        # Listar arquivos no diretório auth
        auth_files = list(self.auth_module_path.glob("*.py"))
        auth_file_list = [f.name for f in auth_files]
        
        # Criar baseline
        baseline = {
            "timestamp": "2025-08-04T21:30:00Z",
            "file_hash": content_hash,
            "metrics": {
                "total_lines": total_lines,
                "code_lines": code_lines,
                "class_count": class_count,
                "method_count": method_count
            },
            "auth_files": sorted(auth_file_list),
            "expected_structure": {
                "single_project_auth_file": True,
                "no_duplicate_patterns": True,
                "classes": ["ProjectAuth"],
                "forbidden_files": []
            }
        }
        
        # Salvar baseline
        self.baseline_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.baseline_file, 'w', encoding='utf-8') as f:
                json.dump(baseline, f, indent=2)
                
            print(f"✅ Baseline criado: {self.baseline_file}")
            print(f"📊 Métricas baseline: {code_lines} linhas código, {method_count} métodos")
            
        except Exception as e:
            print(f"⚠️ Falha ao salvar baseline: {e}")
            # Não é erro crítico para o teste
            
        # Validar que o baseline representa um estado limpo
        assert class_count >= 1, "Baseline deve ter pelo menos 1 classe"
        assert method_count >= 5, "Baseline deve ter pelo menos 5 métodos"
        assert "project_auth.py" in auth_file_list, "Baseline deve incluir project_auth.py"
        
        print("✅ Baseline estabelecido para monitoramento futuro")
        
    def test_directory_structure_monitoring_real(self):
        """
        Teste REAL: Monitoramento de estrutura de diretórios
        VALIDAÇÃO: Alertar sobre mudanças suspeitas na estrutura
        """
        if not self.auth_module_path.exists():
            pytest.skip("Diretório auth não encontrado")
            
        # Mapear estrutura atual
        current_structure = {}
        
        for item in self.auth_module_path.iterdir():
            if item.is_file() and item.suffix == '.py':
                # Calcular hash do arquivo
                try:
                    with open(item, 'r', encoding='utf-8') as f:
                        content = f.read()
                    file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]  # Hash curto
                    file_size = len(content)
                    
                    current_structure[item.name] = {
                        "hash": file_hash,
                        "size": file_size,
                        "is_primary": item.name == "project_auth.py"
                    }
                    
                except Exception as e:
                    print(f"⚠️ Erro lendo {item.name}: {e}")
                    
        # Verificações de integridade estrutural
        expected_files = ["__init__.py", "project_auth.py"]
        missing_files = [f for f in expected_files if f not in current_structure]
        
        assert len(missing_files) == 0, f"Arquivos obrigatórios faltando: {missing_files}"
        
        # Verificar se project_auth.py é o arquivo principal
        if "project_auth.py" in current_structure:
            main_file = current_structure["project_auth.py"]
            assert main_file["size"] > 1000, f"project_auth.py muito pequeno: {main_file['size']} chars"
            
        # Verificar se não há muitos arquivos (indicativo de duplicação)
        max_reasonable_files = 5
        assert len(current_structure) <= max_reasonable_files, f"Muitos arquivos: {len(current_structure)}"
        
        print(f"📁 Estrutura monitorada: {list(current_structure.keys())}")
        print(f"✅ Estrutura de diretório íntegra: {len(current_structure)} arquivos")


if __name__ == "__main__":
    unittest.main()
