"""
Testes REAIS estruturais para Code Deduplication - Subtarefa 4.1
Valida que project_auth_new.py não existe - Hotfix 3 de remoção de duplicação
"""

import pytest
import os
import sys
import glob
from typing import List, Dict, Any

# Adicionar broker ao path para importação
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestCodeDeduplicationStructuralReal:
    """
    Testes estruturais REAIS para validar remoção de duplicação de código
    SEM MOCKS - Verificação real da estrutura de arquivos
    """
    
    def setup_method(self):
        """Setup para cada teste"""
        # Caminhos base para verificação
        self.broker_src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'broker')
        self.auth_path = os.path.join(self.broker_src_path, 'auth')
    
    def test_project_auth_new_does_not_exist_real(self):
        """
        Teste REAL: Confirmar que project_auth_new.py não existe
        VALIDAÇÃO: Arquivo duplicado foi removido conforme Hotfix 3
        """
        # Verificar se o arquivo duplicado NÃO existe
        duplicated_file_paths = [
            os.path.join(self.auth_path, 'project_auth_new.py'),
            os.path.join(self.broker_src_path, 'project_auth_new.py'),
            os.path.join(self.broker_src_path, 'auth', 'project_auth_new.py'),
        ]
        
        existing_duplicates = []
        
        for file_path in duplicated_file_paths:
            if os.path.exists(file_path):
                existing_duplicates.append(file_path)
        
        # NÃO deve haver arquivo duplicado
        assert len(existing_duplicates) == 0, f"DUPLICAÇÃO DETECTADA: Arquivo duplicado ainda existe: {existing_duplicates}"
    
    def test_only_single_project_auth_exists_real(self):
        """
        Teste REAL: Confirmar que existe apenas UM arquivo project_auth.py
        VALIDAÇÃO: Estrutura limpa sem duplicatas
        """
        # Buscar todos os arquivos project_auth* na estrutura
        search_patterns = [
            os.path.join(self.broker_src_path, '**/project_auth*.py'),
            os.path.join(self.broker_src_path, 'project_auth*.py'),
        ]
        
        found_files = []
        
        for pattern in search_patterns:
            files = glob.glob(pattern, recursive=True)
            found_files.extend(files)
        
        # Remover duplicatas da lista
        found_files = list(set(found_files))
        
        # Deve existir APENAS o arquivo principal
        expected_file = os.path.join(self.auth_path, 'project_auth.py')
        
        # Normalizar caminhos para comparação
        found_files_normalized = [os.path.normpath(f) for f in found_files]
        expected_file_normalized = os.path.normpath(expected_file)
        
        # Deve ter exatamente 1 arquivo e deve ser o correto
        assert len(found_files_normalized) == 1, f"Múltiplos arquivos project_auth encontrados: {found_files}"
        assert expected_file_normalized in found_files_normalized, f"Arquivo principal não encontrado. Encontrados: {found_files}"
    
    def test_no_backup_or_temp_files_real(self):
        """
        Teste REAL: Confirmar ausência de arquivos backup/temporários
        VALIDAÇÃO: Limpeza completa após remoção de duplicação
        """
        # Padrões de arquivos temporários/backup que não devem existir
        temp_patterns = [
            os.path.join(self.broker_src_path, '**/project_auth*.bak'),
            os.path.join(self.broker_src_path, '**/project_auth*.backup'),
            os.path.join(self.broker_src_path, '**/project_auth*.old'),
            os.path.join(self.broker_src_path, '**/project_auth*.tmp'),
            os.path.join(self.broker_src_path, '**/project_auth*~'),
            os.path.join(self.broker_src_path, '**/*project_auth*.swp'),
        ]
        
        temp_files_found = []
        
        for pattern in temp_patterns:
            files = glob.glob(pattern, recursive=True)
            temp_files_found.extend(files)
        
        # NÃO deve haver arquivos temporários
        assert len(temp_files_found) == 0, f"Arquivos temporários encontrados: {temp_files_found}"
    
    def test_main_project_auth_file_exists_and_functional_real(self):
        """
        Teste REAL: Confirmar que arquivo principal existe e é funcional
        VALIDAÇÃO: Remoção de duplicação não quebrou funcionalidade
        """
        main_file = os.path.join(self.auth_path, 'project_auth.py')
        
        # Arquivo principal deve existir
        assert os.path.exists(main_file), f"Arquivo principal project_auth.py não encontrado em {main_file}"
        
        # Arquivo deve ter conteúdo significativo
        with open(main_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Validações básicas de conteúdo
        assert len(content) > 100, "Arquivo project_auth.py está muito pequeno"
        assert 'class ProjectAuth' in content, "Classe ProjectAuth não encontrada"
        assert 'def ' in content, "Nenhuma função/método encontrado"
        
        # Verificar que arquivo é sintáticamente válido (pode ser importado)
        try:
            from broker.auth.project_auth import ProjectAuth
            # Se chegou aqui, import funcionou
            assert ProjectAuth is not None
        except ImportError as e:
            pytest.fail(f"Arquivo project_auth.py não pode ser importado: {e}")
        except SyntaxError as e:
            pytest.fail(f"Arquivo project_auth.py tem erro de sintaxe: {e}")
    
    def test_no_duplicate_class_definitions_real(self):
        """
        Teste REAL: Verificar ausência de definições duplicadas de classe
        VALIDAÇÃO: Não há múltiplas definições de ProjectAuth no código
        """
        # Buscar todos os arquivos Python no módulo broker
        python_files = glob.glob(os.path.join(self.broker_src_path, '**', '*.py'), recursive=True)
        
        project_auth_class_files = []
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Procurar definições de classe ProjectAuth
                if 'class ProjectAuth' in content:
                    project_auth_class_files.append(py_file)
            except (UnicodeDecodeError, PermissionError):
                # Ignorar arquivos que não podem ser lidos
                continue
        
        # Deve haver APENAS uma definição da classe
        assert len(project_auth_class_files) == 1, f"Múltiplas definições de ProjectAuth encontradas: {project_auth_class_files}"
        
        # E deve ser no arquivo correto
        expected_file = os.path.join(self.auth_path, 'project_auth.py')
        expected_file_normalized = os.path.normpath(expected_file)
        found_file_normalized = os.path.normpath(project_auth_class_files[0])
        
        assert found_file_normalized == expected_file_normalized, f"ProjectAuth definida em local incorreto: {project_auth_class_files[0]}"
    
    def test_imports_still_work_after_deduplication_real(self):
        """
        Teste REAL: Confirmar que imports continuam funcionando
        VALIDAÇÃO: Remoção de duplicação não quebrou imports existentes
        """
        # Imports que devem continuar funcionando
        import_tests = [
            "from broker.auth.project_auth import ProjectAuth",
            "from broker.auth.project_auth import ProjectCredentials", 
            "from broker.auth.project_auth import ProjectSession",
            "from broker.auth import ProjectAuth",
            "from broker.auth import project_auth",
        ]
        
        failed_imports = []
        
        for import_stmt in import_tests:
            try:
                # Tentar executar o import
                exec(import_stmt)
            except ImportError as e:
                failed_imports.append(f"{import_stmt} -> {e}")
            except Exception as e:
                failed_imports.append(f"{import_stmt} -> {e}")
        
        # Todos os imports devem funcionar
        assert len(failed_imports) == 0, f"Imports falharam após deduplicação: {failed_imports}"
    
    def test_auth_module_init_is_clean_real(self):
        """
        Teste REAL: Verificar que __init__.py do auth está limpo
        VALIDAÇÃO: Não há referências a arquivos duplicados no __init__
        """
        init_file = os.path.join(self.auth_path, '__init__.py')
        
        if os.path.exists(init_file):
            with open(init_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Não deve haver referências a arquivos duplicados
            forbidden_references = [
                'project_auth_new',
                'project_auth_old', 
                'project_auth_backup',
                'project_auth_temp',
            ]
            
            violations = []
            
            for forbidden in forbidden_references:
                if forbidden in content:
                    violations.append(forbidden)
            
            assert len(violations) == 0, f"Referências a arquivos duplicados encontradas em __init__.py: {violations}"
    
    def test_file_structure_consistency_real(self):
        """
        Teste REAL: Verificar consistência da estrutura de arquivos
        VALIDAÇÃO: Estrutura auth/ está organizada e limpa
        """
        # Arquivos esperados no diretório auth/
        expected_files = {
            '__init__.py': True,    # Obrigatório
            'project_auth.py': True,  # Obrigatório
        }
        
        # Arquivos que NÃO devem existir
        forbidden_files = [
            'project_auth_new.py',
            'project_auth_old.py',
            'project_auth_backup.py',
            'project_auth_temp.py',
            'project_auth.bak',
            'project_auth.backup',
        ]
        
        if os.path.exists(self.auth_path):
            actual_files = os.listdir(self.auth_path)
            
            # Verificar arquivos obrigatórios
            missing_required = []
            for required_file, is_required in expected_files.items():
                if is_required and required_file not in actual_files:
                    missing_required.append(required_file)
            
            assert len(missing_required) == 0, f"Arquivos obrigatórios faltando: {missing_required}"
            
            # Verificar arquivos proibidos
            forbidden_found = []
            for forbidden_file in forbidden_files:
                if forbidden_file in actual_files:
                    forbidden_found.append(forbidden_file)
            
            assert len(forbidden_found) == 0, f"Arquivos proibidos encontrados: {forbidden_found}"
    
    def test_git_history_cleanup_simulation_real(self):
        """
        Teste REAL: Simular verificação de limpeza do histórico git
        VALIDAÇÃO: Estrutura atual reflete estado limpo pós-deduplicação
        """
        # Este teste verifica o estado atual (que deve refletir limpeza)
        
        # 1. Arquivo duplicado não deve existir
        duplicate_file = os.path.join(self.auth_path, 'project_auth_new.py')
        assert not os.path.exists(duplicate_file), "Arquivo duplicado ainda existe - limpeza incompleta"
        
        # 2. Arquivo principal deve existir e ser funcional
        main_file = os.path.join(self.auth_path, 'project_auth.py')
        assert os.path.exists(main_file), "Arquivo principal foi removido incorretamente"
        
        # 3. Funcionalidade deve estar preservada
        try:
            from broker.auth.project_auth import ProjectAuth
            auth = ProjectAuth()
            assert auth is not None, "Funcionalidade ProjectAuth foi quebrada"
        except Exception as e:
            pytest.fail(f"Funcionalidade ProjectAuth não funciona: {e}")
        
        # 4. Estrutura deve estar limpa
        auth_files = []
        if os.path.exists(self.auth_path):
            auth_files = [f for f in os.listdir(self.auth_path) if f.endswith('.py')]
        
        # Deve ter poucos arquivos Python (estrutura limpa)
        max_expected_files = 5  # __init__.py, project_auth.py, e poucos outros
        assert len(auth_files) <= max_expected_files, f"Muitos arquivos em auth/ - possível duplicação: {auth_files}"


# Execução standalone para validação rápida
if __name__ == "__main__":
    print("🧹 Testes Estruturais Code Deduplication - Subtarefa 4.1")
    print("🎯 Objetivo: Validar que project_auth_new.py não existe")
    print("🚫 SEM MOCKS - Verificação real da estrutura de arquivos")
    print()
    
    # Teste crítico de deduplicação
    test_instance = TestCodeDeduplicationStructuralReal()
    test_instance.setup_method()
    
    try:
        test_instance.test_project_auth_new_does_not_exist_real()
        print("✅ Deduplicação validada - Arquivo duplicado não existe")
    except Exception as e:
        print(f"❌ PROBLEMA NA DEDUPLICAÇÃO: {e}")
    
    # Executar todos os testes
    pytest.main([__file__, "-v", "--tb=short"])
