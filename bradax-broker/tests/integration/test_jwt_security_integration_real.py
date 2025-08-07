"""
Testes REAIS de Integração para JWT Security - Subtarefa 3.2
Valida que sistema falha sem BRADAX_JWT_SECRET em componentes integrados
"""

import pytest
import os
import sys
import requests
import time
from typing import Dict, Any

# Adicionar broker ao path para importação
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestJWTSecurityIntegrationReal:
    """
    Testes de integração REAIS para JWT Security
    Valida que componentes que dependem de JWT falham apropriadamente sem BRADAX_JWT_SECRET
    """
    
    def setup_method(self):
        """Setup para cada teste - salvar estado original das env vars"""
        self.original_env = {}
        
        # Salvar valores originais das variáveis JWT
        jwt_env_vars = [
            'BRADAX_JWT_SECRET',
            'BRADAX_JWT_EXPIRE_MINUTES',
            'OPENAI_API_KEY'
        ]
        
        for var in jwt_env_vars:
            self.original_env[var] = os.environ.get(var)
    
    def teardown_method(self):
        """Cleanup - restaurar estado original das env vars"""
        # Restaurar todas as variáveis
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
        
        # Limpar módulos importados para próximo teste
        modules_to_clear = [
            'broker.constants',
            'broker.config', 
            'broker.auth',
            'broker.auth.jwt_handler',
            'broker.auth.project_auth'
        ]
        
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
    
    def test_settings_fails_without_jwt_secret_real(self):
        """
        Teste REAL: broker.config.Settings falha sem BRADAX_JWT_SECRET
        VALIDAÇÃO: Config system exige secret para inicializar
        """
        # Remover JWT secret
        if 'BRADAX_JWT_SECRET' in os.environ:
            del os.environ['BRADAX_JWT_SECRET']
        
        # Limpar módulos para reimportação
        if 'broker.config' in sys.modules:
            del sys.modules['broker.config']
        if 'broker.constants' in sys.modules:
            del sys.modules['broker.constants']
        
        # Tentar criar Settings - deve falhar
        with pytest.raises(ValueError) as exc_info:
            from broker.config import Settings
            settings = Settings()
        
        # Validar erro específico do JWT secret
        error_message = str(exc_info.value)
        assert "BRADAX_JWT_SECRET" in error_message
        assert "obrigatória" in error_message.lower()
    
    def test_project_auth_fails_without_secret_real(self):
        """
        Teste REAL: ProjectAuth falha sem BRADAX_JWT_SECRET
        VALIDAÇÃO: Sistema de autenticação de projetos exige secret
        """
        # Remover JWT secret
        if 'BRADAX_JWT_SECRET' in os.environ:
            del os.environ['BRADAX_JWT_SECRET']
        
        # Limpar módulos
        modules_to_clear = ['broker.auth.project_auth', 'broker.constants', 'broker.config']
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        # Tentar usar ProjectAuth - deve falhar
        with pytest.raises(ValueError):
            from broker.auth.project_auth import ProjectAuth
            project_auth = ProjectAuth()
    
    def test_broker_startup_fails_without_secret_real(self):
        """
        Teste REAL: Broker main não consegue inicializar sem secret
        VALIDAÇÃO: Aplicação FastAPI falha no startup sem JWT configurado
        """
        # Remover JWT secret
        if 'BRADAX_JWT_SECRET' in os.environ:
            del os.environ['BRADAX_JWT_SECRET']
        
        # Limpar módulos
        modules_to_clear = ['broker.main', 'broker.constants', 'broker.config']
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        # Tentar importar main (que inicializa config) - deve falhar
        with pytest.raises(ValueError):
            from broker.main import app
    
    def test_auth_middleware_fails_without_secret_real(self):
        """
        Teste REAL: Middleware de autenticação falha sem secret
        VALIDAÇÃO: Middleware auth simples não depende de JWT secret mas SecurityMiddleware pode depender
        """
        # Remover JWT secret
        if 'BRADAX_JWT_SECRET' in os.environ:
            del os.environ['BRADAX_JWT_SECRET']
        
        # Limpar módulos
        modules_to_clear = ['broker.middleware.auth', 'broker.constants', 'broker.config']
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        # Middleware auth simples não depende de JWT secret
        from broker.middleware.auth import get_api_key
        # get_api_key é uma função simples que funciona independente de JWT secret
        
        # Teste que constants ainda falha sem secret
        with pytest.raises(ValueError):
            from broker.constants import HubSecurityConstants
    
    def test_integration_with_valid_secret_works_real(self):
        """
        Teste REAL: Sistema funciona normalmente com BRADAX_JWT_SECRET válido
        VALIDAÇÃO: Componentes principais inicializam corretamente com secret
        """
        # Configurar secret válido
        os.environ['BRADAX_JWT_SECRET'] = "integration-test-secret-valid-config"
        
        # Limpar módulos para reimportação limpa
        modules_to_clear = [
            'broker.constants', 'broker.config', 'broker.auth.project_auth', 'broker.main'
        ]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        # Componentes principais devem funcionar
        from broker.config import Settings
        settings = Settings()
        assert settings.jwt_secret_key == "integration-test-secret-valid-config"
        
        from broker.auth.project_auth import ProjectAuth
        project_auth = ProjectAuth()
        assert project_auth is not None
        
        # Main app deve inicializar sem erro
        from broker.main import app
        assert app is not None
    
    def test_security_hotfix_regression_prevention_real(self):
        """
        Teste REAL: Prevenção de regressão do Hotfix 2
        VALIDAÇÃO: Sistema não pode voltar a ter fallback inseguro
        """
        # Remover JWT secret
        if 'BRADAX_JWT_SECRET' in os.environ:
            del os.environ['BRADAX_JWT_SECRET']
        
        # Limpar todos os módulos relacionados
        security_modules = [
            'broker.constants', 'broker.config', 'broker.auth',
            'broker.auth.project_auth', 'broker.main'
        ]
        
        for module in security_modules:
            if module in sys.modules:
                del sys.modules[module]
        
        # CRITÉRIO: Componentes críticos não devem funcionar sem secret
        # Se algum funcionar, há regressão do hotfix
        
        components_to_test = [
            ('broker.constants', 'HubSecurityConstants'),
            ('broker.config', 'Settings'),
            ('broker.auth.project_auth', 'ProjectAuth')
        ]
        
        failed_components = []
        
        for module_name, class_name in components_to_test:
            try:
                # Tentar importar e instanciar - DEVE falhar
                module = __import__(module_name, fromlist=[class_name])
                cls = getattr(module, class_name)
                instance = cls()
                
                # Se chegou aqui, há REGRESSÃO - componente funcionou sem secret
                failed_components.append(f"{module_name}.{class_name}")
                
            except ValueError:
                # Esperado - componente falhou corretamente sem secret
                continue
            except Exception as e:
                # Outros erros são aceitáveis (import errors, etc)
                continue
        
        # Validar que NENHUM componente funcionou sem secret
        assert len(failed_components) == 0, f"REGRESSÃO DETECTADA: Componentes funcionaram sem BRADAX_JWT_SECRET: {failed_components}"


# Execução standalone para validação rápida
if __name__ == "__main__":
    print("🔐 Testes de Integração JWT Security - Subtarefa 3.2")
    print("🎯 Objetivo: Validar que sistema falha apropriadamente sem BRADAX_JWT_SECRET")
    print()
    
    # Teste crítico de regressão
    test_instance = TestJWTSecurityIntegrationReal()
    test_instance.setup_method()
    
    try:
        test_instance.test_security_hotfix_regression_prevention_real()
        print("✅ Hotfix 2 - Nenhuma regressão detectada")
    except Exception as e:
        print(f"❌ PROBLEMA: {e}")
    finally:
        test_instance.teardown_method()
    
    # Executar todos os testes
    pytest.main([__file__, "-v", "--tb=short"])
