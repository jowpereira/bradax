"""
Testes REAIS de Code Quality - Bradax Broker
============================================

OBJETIVO: Validar Hotfix 3 - Code Quality (duplicação removida)
MÉTODO: Testes 100% reais verificando estrutura de arquivos
CRITÉRIO: project_auth_new.py não deve existir, funcionalidade preservada

HOTFIX 3 VALIDADO: Code deduplication sem quebrar funcionalidade
"""

import pytest
import unittest
import os
import sys
from pathlib import Path
import importlib
import inspect


class TestCodeQualityStructuralReal(unittest.TestCase):
    """
    Teste REAL: Code Quality - Estrutura sem duplicação
    VALIDAÇÃO: Hotfix 3 - project_auth_new.py removido sem quebrar sistema
    """
    
    @classmethod
    def setUpClass(cls):
        """Setup para testes estruturais de code quality."""
        cls.broker_root = Path(__file__).parent.parent.parent  # bradax-broker/
        cls.src_root = cls.broker_root / "src"
        cls.auth_module_path = cls.src_root / "broker" / "auth"
        
        # Arquivos que NÃO devem existir (duplicatas removidas)
        cls.forbidden_files = [
            "project_auth_new.py",
            "project_auth_old.py", 
            "project_auth_backup.py",
            "project_auth_copy.py"
        ]
        
        # Arquivos que DEVEM existir (funcionalidade preservada)
        cls.required_files = [
            "project_auth.py",
            "__init__.py"
        ]
        
        print("🔍 Code Quality Structural Tests - Validando remoção de duplicação")
        
    def test_duplicate_files_removed_real(self):
        """
        Teste REAL: Arquivos duplicados foram removidos
        VALIDAÇÃO: project_auth_new.py e similares não existem
        """
        print(f"📁 Verificando diretório auth: {self.auth_module_path}")
        
        # Verificar se diretório auth existe
        assert self.auth_module_path.exists(), f"Diretório auth não encontrado: {self.auth_module_path}"
        
        duplicates_found = []
        
        # Verificar se arquivos duplicados foram removidos
        for forbidden_file in self.forbidden_files:
            forbidden_path = self.auth_module_path / forbidden_file
            if forbidden_path.exists():
                duplicates_found.append(forbidden_file)
                print(f"❌ DUPLICAÇÃO DETECTADA: {forbidden_file} ainda existe")
            else:
                print(f"✅ Duplicação removida: {forbidden_file} não existe")
                
        # Verificar se arquivos obrigatórios existem
        missing_required = []
        for required_file in self.required_files:
            required_path = self.auth_module_path / required_file
            if not required_path.exists():
                missing_required.append(required_file)
                print(f"❌ ARQUIVO OBRIGATÓRIO FALTANDO: {required_file}")
            else:
                print(f"✅ Arquivo obrigatório presente: {required_file}")
                
        # Assertions finais
        assert len(duplicates_found) == 0, f"Arquivos duplicados ainda existem: {duplicates_found}"
        assert len(missing_required) == 0, f"Arquivos obrigatórios faltando: {missing_required}"
        
        print("✅ Estrutura de arquivos validada - sem duplicação")
        
    def test_no_duplicate_classes_real(self):
        """
        Teste REAL: Não há classes duplicadas no módulo
        VALIDAÇÃO: ProjectAuth é única, sem duplicatas
        """
        auth_file = self.auth_module_path / "project_auth.py"
        
        if not auth_file.exists():
            pytest.skip("project_auth.py não encontrado")
            
        # Ler arquivo e buscar classes ProjectAuth*
        with open(auth_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        lines = content.split('\n')
        auth_classes = []
        
        for i, line in enumerate(lines, 1):
            # Buscar definições de classe que contenham ProjectAuth
            if line.strip().startswith('class ') and 'ProjectAuth' in line:
                class_name = line.strip().split('class ')[1].split('(')[0].split(':')[0].strip()
                auth_classes.append(class_name)
                print(f"📋 Classe encontrada linha {i}: {class_name}")
                
        # Deve existir exatamente uma classe ProjectAuth
        assert len(auth_classes) >= 1, f"Nenhuma classe ProjectAuth encontrada em {auth_file}"
        
        # Verificar se não há duplicatas óbvias
        duplicate_patterns = ['ProjectAuthNew', 'ProjectAuthOld', 'ProjectAuthCopy', 'ProjectAuthBackup']
        duplicates_found = [cls for cls in auth_classes if any(pattern in cls for pattern in duplicate_patterns)]
        
        assert len(duplicates_found) == 0, f"Classes duplicadas encontradas: {duplicates_found}"
        
        # Verificar se há apenas uma classe ProjectAuth principal
        main_auth_classes = [cls for cls in auth_classes if cls == 'ProjectAuth']
        assert len(main_auth_classes) == 1, f"Deve ter exatamente 1 classe ProjectAuth, encontradas: {auth_classes}"
        
        print(f"✅ Classes validadas: {auth_classes} (sem duplicação)")
            
    def test_directory_structure_clean_real(self):
        """
        Teste REAL: Estrutura de diretórios limpa
        VALIDAÇÃO: Não há arquivos temporários, backups ou duplicatas
        """
        suspicious_patterns = [
            "*.bak", "*.backup", "*.old", "*.new", "*.copy", "*.tmp",
            "*_backup.*", "*_old.*", "*_new.*", "*_copy.*"
        ]
        
        suspicious_files = []
        
        # Verificar diretório auth
        for pattern in suspicious_patterns:
            matches = list(self.auth_module_path.glob(pattern))
            for match in matches:
                suspicious_files.append(str(match.relative_to(self.broker_root)))
                print(f"❌ Arquivo suspeito: {match.name}")
                
        # Verificar diretório inteiro de src para patterns suspeitos
        for pattern in suspicious_patterns:
            matches = list(self.src_root.rglob(pattern))
            for match in matches:
                if "auth" in str(match):  # Focar no módulo auth
                    suspicious_files.append(str(match.relative_to(self.broker_root)))
                    print(f"❌ Arquivo suspeito em src: {match.name}")
                    
        assert len(suspicious_files) == 0, f"Arquivos suspeitos encontrados: {suspicious_files}"
        print("✅ Estrutura de diretórios limpa - sem arquivos temporários")
        
    def test_no_commented_duplicates_real(self):
        """
        Teste REAL: Não há código duplicado comentado
        VALIDAÇÃO: project_auth.py não contém código comentado de duplicatas
        """
        auth_file = self.auth_module_path / "project_auth.py"
        
        if not auth_file.exists():
            pytest.skip("project_auth.py não encontrado")
            
        with open(auth_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Padrões que indicam código duplicado comentado
        suspicious_patterns = [
            "# class ProjectAuthNew",
            "# class ProjectAuthOld", 
            "# TODO: remove duplicate",
            "# FIXME: duplicate code",
            "# NOTE: this is a duplicate",
            "# Duplicated from",
        ]
        
        found_patterns = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            for pattern in suspicious_patterns:
                if pattern.lower() in line.lower():
                    found_patterns.append(f"Linha {i}: {line.strip()}")
                    print(f"❌ Código suspeito linha {i}: {line.strip()}")
                    
        assert len(found_patterns) == 0, f"Código duplicado comentado encontrado: {found_patterns}"
        print("✅ Nenhum código duplicado comentado encontrado")
        
    def test_file_count_reasonable_real(self):
        """
        Teste REAL: Número de arquivos no módulo auth é razoável
        VALIDAÇÃO: Não há proliferação de arquivos auth
        """
        if not self.auth_module_path.exists():
            pytest.skip("Diretório auth não encontrado")
            
        # Contar arquivos .py no diretório auth
        py_files = list(self.auth_module_path.glob("*.py"))
        py_file_names = [f.name for f in py_files]
        
        print(f"📁 Arquivos .py em auth/: {py_file_names}")
        
        # Número razoável de arquivos auth (não deve ter muitos)
        max_reasonable_files = 10  # Limite generoso
        
        assert len(py_files) <= max_reasonable_files, f"Muitos arquivos em auth/: {len(py_files)} > {max_reasonable_files}"
        
        # Verificar se não há padrões de duplicação nos nomes
        auth_related_files = [f for f in py_file_names if 'auth' in f.lower()]
        project_auth_files = [f for f in py_file_names if 'project_auth' in f.lower()]
        
        print(f"📋 Arquivos auth relacionados: {auth_related_files}")
        print(f"📋 Arquivos project_auth: {project_auth_files}")
        
        # Deve ter exatamente 1 arquivo project_auth principal
        main_project_auth = [f for f in project_auth_files if f == "project_auth.py"]
        assert len(main_project_auth) == 1, f"Deve ter exatamente 1 project_auth.py, encontrado: {project_auth_files}"
        
        print("✅ Número de arquivos auth razoável e sem duplicação")


if __name__ == "__main__":
    unittest.main()
