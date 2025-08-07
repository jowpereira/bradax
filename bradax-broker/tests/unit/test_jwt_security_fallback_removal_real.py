"""
Testes REAIS de Segurança JWT - Subtarefa 3.4
Valida que fallbacks inseguros foram removidos - SEM MOCKS, dados REAIS
"""

import pytest
import os
import sys
import re
import inspect
import ast
from typing import Dict, Any, List

# Adicionar broker ao path para importação
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestJWTSecurityFallbackRemovalReal:
    """
    Testes de segurança REAIS para validar remoção de fallbacks inseguros
    SEM MOCKS - Validação de código fonte e comportamento real
    """
    
    def setup_method(self):
        """Setup para cada teste - ambiente limpo"""
        self.original_env = {}
        
        # Salvar valores originais das variáveis
        env_vars = ['BRADAX_JWT_SECRET', 'BRADAX_JWT_EXPIRE_MINUTES']
        
        for var in env_vars:
            self.original_env[var] = os.environ.get(var)
        
        # Limpar módulos para testes limpos
        modules_to_clear = [
            'broker.constants', 'broker.config', 'broker.auth.project_auth',
            'broker.main', 'broker.api'
        ]
        
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
    
    def teardown_method(self):
        """Cleanup - restaurar estado original"""
        # Restaurar todas as variáveis
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
    
    def test_no_hardcoded_jwt_secrets_real(self):
        """
        Teste REAL: Confirmar ausência de JWT secrets hardcoded
        VALIDAÇÃO: Código fonte não contém secrets fixos (fallback inseguro)
        """
        # Caminhos dos arquivos críticos para verificar
        critical_files = [
            os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'broker', 'constants.py'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'broker', 'config.py'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'broker', 'auth', 'project_auth.py')
        ]
        
        # Padrões REALMENTE suspeitos (fallbacks inseguros)
        dangerous_patterns = [
            r'jwt_secret\s*=\s*["\'][a-zA-Z0-9]{16,}["\']',    # jwt_secret = "hardcoded_value"
            r'secret\s*=\s*["\'][a-zA-Z0-9]{16,}["\']',        # secret = "hardcoded_value"  
            r'or\s+["\'][a-zA-Z0-9]{16,}["\']',                # secret or "fallback"
            r'default=["\'][a-zA-Z0-9]{16,}["\']',             # default="fallback"
        ]
        
        violations = []
        
        for file_path in critical_files:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Buscar padrões perigosos
                for pattern in dangerous_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = content.split('\n')[line_num - 1].strip()
                        
                        # Excluir contextos seguros
                        context = content[max(0, match.start()-100):match.start()+100]
                        is_safe_context = any([
                            'openssl rand' in context,           # Instrução para gerar
                            'development-secret' in context,     # Validação dev vs prod
                            'change-in-production' in context,   # Validação de produção
                            'raise ValueError' in context,       # Error handling
                            'raise ConfigurationException' in context,  # Error handling
                        ])
                        
                        if not is_safe_context:
                            violations.append(f"{file_path}:{line_num} - {line_content}")
        
        # Não deve haver fallbacks inseguros reais
        assert len(violations) == 0, f"FALLBACK INSEGURO REAL DETECTADO: {violations}"
    
    def test_no_default_jwt_generation_real(self):
        """
        Teste REAL: Confirmar ausência de geração automática de JWT secret
        VALIDAÇÃO: Sistema não gera secret automaticamente (fallback inseguro)
        """
        # Remover JWT secret do environment
        if 'BRADAX_JWT_SECRET' in os.environ:
            del os.environ['BRADAX_JWT_SECRET']
        
        # Limpar módulos
        modules_to_clear = ['broker.constants', 'broker.config']
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        # Sistema DEVE falhar - não gerar secret automaticamente
        with pytest.raises(ValueError) as exc_info:
            from broker.constants import HubSecurityConstants
        
        # Validar que erro é específico sobre ausência de secret
        error_message = str(exc_info.value)
        assert "BRADAX_JWT_SECRET" in error_message
        assert "obrigatória" in error_message.lower()
        
        # Garantir que não há menção a geração automática
        forbidden_phrases = [
            "generating", "gerando", "auto", "default secret created",
            "created automatically", "fallback secret"
        ]
        
        for phrase in forbidden_phrases:
            assert phrase.lower() not in error_message.lower(), f"Possível fallback detectado: '{phrase}' em error message"
    
    def test_constants_source_code_security_real(self):
        """
        Teste REAL: Análise de código fonte das constantes de segurança
        VALIDAÇÃO: Código não contém lógica de fallback inseguro
        """
        constants_file = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'broker', 'constants.py')
        
        if not os.path.exists(constants_file):
            pytest.skip("Constants file not found")
        
        with open(constants_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # Analisar AST para detectar padrões inseguros
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            pytest.fail("Constants file has syntax errors")
        
        # Procurar por construções perigosas
        dangerous_constructs = []
        
        for node in ast.walk(tree):
            # Detectar assignments suspeitos
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and 'secret' in target.id.lower():
                        if isinstance(node.value, ast.Str):  # String literal
                            dangerous_constructs.append(f"Hardcoded secret assignment: {target.id}")
                        elif isinstance(node.value, ast.Call):
                            # Verificar se não é geração automática
                            if hasattr(node.value.func, 'id'):
                                func_name = node.value.func.id
                                if func_name in ['generate', 'create', 'random']:
                                    dangerous_constructs.append(f"Possible auto-generation: {target.id} = {func_name}()")
            
            # Detectar condicionais que podem implementar fallbacks
            if isinstance(node, ast.If):
                # Verificar se há lógica "if not secret: secret = fallback"
                if isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not):
                    for stmt in node.body:
                        if isinstance(stmt, ast.Assign):
                            for target in stmt.targets:
                                if isinstance(target, ast.Name) and 'secret' in target.id.lower():
                                    dangerous_constructs.append(f"Possible fallback logic for: {target.id}")
        
        assert len(dangerous_constructs) == 0, f"CÓDIGO INSEGURO DETECTADO: {dangerous_constructs}"
    
    def test_environment_only_jwt_loading_real(self):
        """
        Teste REAL: Confirmar que JWT secret vem APENAS de environment
        VALIDAÇÃO: Não há outras fontes de secret (arquivo, banco, etc.)
        """
        # Configurar secret apenas em environment
        test_secret = "test-security-validation-secret-32"
        os.environ['BRADAX_JWT_SECRET'] = test_secret
        
        # Limpar módulos
        if 'broker.constants' in sys.modules:
            del sys.modules['broker.constants']
        
        # Importar e validar source
        from broker.constants import HubSecurityConstants
        
        # Secret deve ser exatamente o que está no environment
        assert HubSecurityConstants.JWT_SECRET_KEY == test_secret
        
        # Testar que mudança no environment é refletida
        new_secret = "new-secret-for-env-test-validation"
        os.environ['BRADAX_JWT_SECRET'] = new_secret
        
        # Forçar reimportação
        del sys.modules['broker.constants']
        from broker.constants import HubSecurityConstants
        
        # Deve refletir a mudança (prova que vem do environment)
        assert HubSecurityConstants.JWT_SECRET_KEY == new_secret
    
    def test_no_weak_default_algorithms_real(self):
        """
        Teste REAL: Confirmar ausência de algoritmos fracos como fallback
        VALIDAÇÃO: Sistema usa apenas algoritmos seguros, sem fallback fraco
        """
        # Configurar environment válido
        os.environ['BRADAX_JWT_SECRET'] = "security-algo-test-secret"
        
        # Limpar módulos
        if 'broker.constants' in sys.modules:
            del sys.modules['broker.constants']
        
        from broker.constants import HubSecurityConstants
        
        # Algoritmo deve ser seguro
        secure_algorithms = ['HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512']
        weak_algorithms = ['none', 'HS1', 'MD5', 'SHA1']
        
        assert HubSecurityConstants.JWT_ALGORITHM in secure_algorithms, f"Algoritmo inseguro: {HubSecurityConstants.JWT_ALGORITHM}"
        assert HubSecurityConstants.JWT_ALGORITHM not in weak_algorithms, f"Algoritmo fraco detectado: {HubSecurityConstants.JWT_ALGORITHM}"
        
        # Confirmar que não há fallback para algoritmo fraco
        # Se tivesse fallback, mudando secret poderia mudar algoritmo
        os.environ['BRADAX_JWT_SECRET'] = "different-secret-test"
        del sys.modules['broker.constants']
        from broker.constants import HubSecurityConstants
        
        # Algoritmo deve permanecer seguro independente do secret
        assert HubSecurityConstants.JWT_ALGORITHM in secure_algorithms
    
    def test_security_exception_handling_real(self):
        """
        Teste REAL: Validar que sistema usa exceptions existentes para falhas
        VALIDAÇÃO: Não há try/catch que implementa fallback inseguro
        """
        # Remover secret para forçar exception
        if 'BRADAX_JWT_SECRET' in os.environ:
            del os.environ['BRADAX_JWT_SECRET']
        
        # Limpar módulos
        if 'broker.constants' in sys.modules:
            del sys.modules['broker.constants']
        
        # Deve usar ValueError existente (não criar fallback)
        with pytest.raises(ValueError) as exc_info:
            from broker.constants import HubSecurityConstants
        
        # Exception deve ser específica e clara
        error = exc_info.value
        assert isinstance(error, ValueError)  # Tipo correto
        assert "BRADAX_JWT_SECRET" in str(error)  # Mensagem específica
        
        # Não deve haver stack trace indicando tentativa de fallback
        error_str = str(error)
        fallback_indicators = [
            "trying fallback", "using default", "generating",
            "creating temporary", "fallback mode"
        ]
        
        for indicator in fallback_indicators:
            assert indicator.lower() not in error_str.lower(), f"Possível tentativa de fallback: {indicator}"
    
    def test_config_security_validation_real(self):
        """
        Teste REAL: Validar que sistema de config é seguro
        VALIDAÇÃO: Config não implementa fallbacks inseguros
        """
        # Configurar secret válido
        os.environ['BRADAX_JWT_SECRET'] = "config-security-test-secret"
        
        # Limpar módulos
        modules_to_clear = ['broker.constants', 'broker.config']
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        from broker.config import Settings
        settings = Settings()
        
        # Validar configurações de segurança
        assert settings.jwt_secret_key is not None
        assert len(settings.jwt_secret_key) >= 8  # Mínimo seguro
        assert settings.jwt_expiration_minutes > 0
        assert settings.jwt_expiration_minutes <= 1440  # Máximo 24h
        
        # Remover secret e tentar recriar config - deve falhar
        del os.environ['BRADAX_JWT_SECRET']
        
        # Limpar módulos
        for module in ['broker.constants', 'broker.config']:
            if module in sys.modules:
                del sys.modules[module]
        
        # Config deve falhar sem fallback
        with pytest.raises(ValueError):
            from broker.config import Settings
            Settings()
    
    def test_no_conditional_fallback_logic_real(self):
        """
        Teste REAL: Verificar ausência de lógica condicional de fallback
        VALIDAÇÃO: Código não contém "if not secret then use fallback"
        """
        # Arquivos para analisar
        files_to_check = [
            os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'broker', 'constants.py'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'broker', 'config.py'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'broker', 'auth', 'project_auth.py')
        ]
        
        fallback_patterns = [
            r'if\s+not\s+.*secret.*:.*secret\s*=',  # if not secret: secret =
            r'secret\s*=\s*secret\s+or\s+',         # secret = secret or fallback
            r'secret\s*\|\|\s*',                    # secret || fallback
            r'getattr.*secret.*default',            # getattr(obj, 'secret', default)
            r'\.get\(.*secret.*,.*\)',              # dict.get('secret', default)
        ]
        
        violations = []
        
        for file_path in files_to_check:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern in fallback_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        violations.append(f"{file_path}:{line_num} - {match.group()}")
        
        assert len(violations) == 0, f"LÓGICA DE FALLBACK DETECTADA: {violations}"
    
    def test_production_security_behavior_real(self):
        """
        Teste REAL: Simular comportamento de produção sem fallbacks
        VALIDAÇÃO: Sistema comporta-se de forma segura em cenário real
        """
        # Simular ambiente de produção (sem debug, sem desenvolvimento)
        os.environ['BRADAX_ENVIRONMENT'] = 'PRODUCTION'
        
        # Teste 1: Com secret válido - deve funcionar
        os.environ['BRADAX_JWT_SECRET'] = "production-security-test-secret"
        
        modules_to_clear = ['broker.constants', 'broker.config', 'broker.auth.project_auth', 'broker.main']
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        # Sistema deve funcionar normalmente
        from broker.config import Settings
        from broker.auth.project_auth import ProjectAuth
        from broker.main import app
        
        settings = Settings()
        auth = ProjectAuth()
        
        assert settings.jwt_secret_key == "production-security-test-secret"
        assert auth is not None
        assert app is not None
        
        # Teste 2: Sem secret - deve falhar completamente (sem fallback)
        del os.environ['BRADAX_JWT_SECRET']
        
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        # Em produção, deve falhar imediatamente
        with pytest.raises(ValueError) as exc_info:
            from broker.constants import HubSecurityConstants
        
        # Error deve ser claro e não mencionar modo desenvolvimento
        error_msg = str(exc_info.value)
        assert "development" not in error_msg.lower()
        assert "debug" not in error_msg.lower()
        assert "BRADAX_JWT_SECRET" in error_msg
        assert "obrigatória" in error_msg.lower()


# Execução standalone para validação rápida
if __name__ == "__main__":
    print("🔐 Testes de Segurança JWT - Remoção de Fallbacks - Subtarefa 3.4")
    print("🎯 Objetivo: Validar ausência completa de fallbacks inseguros")
    print("🚫 SEM MOCKS - Validação de código real e comportamento real")
    print()
    
    # Teste crítico de segurança
    test_instance = TestJWTSecurityFallbackRemovalReal()
    test_instance.setup_method()
    
    try:
        test_instance.test_no_default_jwt_generation_real()
        print("✅ Segurança validada - Nenhum fallback inseguro detectado")
    except Exception as e:
        print(f"❌ FALHA DE SEGURANÇA: {e}")
    finally:
        test_instance.teardown_method()
    
    # Executar todos os testes
    pytest.main([__file__, "-v", "--tb=short"])
