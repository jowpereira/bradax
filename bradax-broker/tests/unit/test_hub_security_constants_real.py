"""
Testes REAIS para HubSecurityConstants - Subtarefa 3.1
Valida JWT security constants com/sem variáveis de ambiente REAIS
"""

import pytest
import os
import sys
import tempfile
import subprocess
from typing import Dict, Any

# Adicionar broker ao path para importação
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestHubSecurityConstantsReal:
    """
    Testes unitários REAIS para HubSecurityConstants
    Valida comportamento com variáveis de ambiente REAIS
    """
    
    def setup_method(self):
        """Setup para cada teste - salvar estado original das env vars"""
        self.original_env = {}
        
        # Salvar valores originais das variáveis JWT
        jwt_env_vars = [
            'BRADAX_JWT_SECRET',
            'BRADAX_JWT_EXPIRE_MINUTES',
            'BRADAX_RATE_LIMIT_RPM',
            'BRADAX_RATE_LIMIT_RPH',
            'BRADAX_MAX_CONCURRENT'
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
    
    def test_hub_security_constants_with_valid_jwt_secret_real(self):
        """
        Teste REAL: HubSecurityConstants com BRADAX_JWT_SECRET válido
        VALIDAÇÃO: Sistema funciona normalmente com secret configurado
        """
        # Configurar secret JWT válido
        valid_secret = "test-jwt-secret-for-real-testing-32-chars"
        os.environ['BRADAX_JWT_SECRET'] = valid_secret
        
        # Forçar reimportação para capturar nova env var
        if 'broker.constants' in sys.modules:
            del sys.modules['broker.constants']
        
        # Importar com secret válido - deve funcionar
        from broker.constants import HubSecurityConstants
        
        # Validar que o secret foi carregado corretamente
        assert HubSecurityConstants.JWT_SECRET_KEY == valid_secret
        assert HubSecurityConstants.JWT_SECRET_KEY is not None
        assert len(HubSecurityConstants.JWT_SECRET_KEY) >= 8
        
        # Validar outras constantes relacionadas
        assert HubSecurityConstants.JWT_ALGORITHM == 'HS256'
        assert HubSecurityConstants.JWT_EXPIRATION_MINUTES > 0
        assert isinstance(HubSecurityConstants.JWT_EXPIRATION_MINUTES, int)
    
    def test_hub_security_constants_without_jwt_secret_real(self):
        """
        Teste REAL: HubSecurityConstants SEM BRADAX_JWT_SECRET
        VALIDAÇÃO: Sistema deve falhar com ValueError específico (não fallback)
        """
        # Remover JWT secret da env
        if 'BRADAX_JWT_SECRET' in os.environ:
            del os.environ['BRADAX_JWT_SECRET']
        
        # Forçar reimportação sem secret
        if 'broker.constants' in sys.modules:
            del sys.modules['broker.constants']
        
        # Tentar importar sem secret - deve falhar com ValueError
        with pytest.raises(ValueError) as exc_info:
            from broker.constants import HubSecurityConstants
        
        # Validar mensagem de erro específica
        error_message = str(exc_info.value)
        assert "BRADAX_JWT_SECRET" in error_message
        assert "obrigatória" in error_message.lower()
        assert "openssl rand" in error_message
    
    def test_hub_security_constants_jwt_expiration_customization_real(self):
        """
        Teste REAL: Customização do tempo de expiração JWT
        VALIDAÇÃO: BRADAX_JWT_EXPIRE_MINUTES é respeitado
        """
        # Configurar secret e tempo customizado
        os.environ['BRADAX_JWT_SECRET'] = "test-secret-for-expiration-test"
        os.environ['BRADAX_JWT_EXPIRE_MINUTES'] = "30"
        
        # Forçar reimportação
        if 'broker.constants' in sys.modules:
            del sys.modules['broker.constants']
        
        from broker.constants import HubSecurityConstants
        
        # Validar tempo customizado
        assert HubSecurityConstants.JWT_EXPIRATION_MINUTES == 30
        assert isinstance(HubSecurityConstants.JWT_EXPIRATION_MINUTES, int)
    
    def test_hub_security_constants_rate_limiting_customization_real(self):
        """
        Teste REAL: Customização de rate limiting via env vars
        VALIDAÇÃO: Variáveis de rate limit são aplicadas corretamente
        """
        # Configurar secret e rate limits customizados
        os.environ['BRADAX_JWT_SECRET'] = "test-secret-for-rate-limit"
        os.environ['BRADAX_RATE_LIMIT_RPM'] = "120"
        os.environ['BRADAX_RATE_LIMIT_RPH'] = "5000"
        os.environ['BRADAX_MAX_CONCURRENT'] = "25"
        
        # Forçar reimportação
        if 'broker.constants' in sys.modules:
            del sys.modules['broker.constants']
        
        from broker.constants import HubSecurityConstants
        
        # Validar rate limits customizados
        assert HubSecurityConstants.REQUESTS_PER_MINUTE == 120
        assert HubSecurityConstants.REQUESTS_PER_HOUR == 5000
        assert HubSecurityConstants.MAX_CONCURRENT_REQUESTS == 25
        
        # Validar tipos
        assert isinstance(HubSecurityConstants.REQUESTS_PER_MINUTE, int)
        assert isinstance(HubSecurityConstants.REQUESTS_PER_HOUR, int)
        assert isinstance(HubSecurityConstants.MAX_CONCURRENT_REQUESTS, int)
    
    def test_hub_security_constants_default_values_real(self):
        """
        Teste REAL: Valores padrão quando env vars opcionais não estão definidas
        VALIDAÇÃO: Defaults corretos são aplicados
        """
        # Configurar apenas o secret obrigatório
        os.environ['BRADAX_JWT_SECRET'] = "test-secret-for-defaults"
        
        # Remover env vars opcionais
        optional_vars = [
            'BRADAX_JWT_EXPIRE_MINUTES',
            'BRADAX_RATE_LIMIT_RPM', 
            'BRADAX_RATE_LIMIT_RPH',
            'BRADAX_MAX_CONCURRENT'
        ]
        
        for var in optional_vars:
            if var in os.environ:
                del os.environ[var]
        
        # Forçar reimportação
        if 'broker.constants' in sys.modules:
            del sys.modules['broker.constants']
        
        from broker.constants import HubSecurityConstants
        
        # Validar valores padrão esperados
        assert HubSecurityConstants.JWT_EXPIRATION_MINUTES == 15  # Default
        assert HubSecurityConstants.REQUESTS_PER_MINUTE == 60     # Default
        assert HubSecurityConstants.REQUESTS_PER_HOUR == 1000     # Default
        assert HubSecurityConstants.MAX_CONCURRENT_REQUESTS == 10 # Default
    
    def test_hub_security_constants_jwt_secret_validation_real(self):
        """
        Teste REAL: Validação do formato/qualidade do JWT secret
        VALIDAÇÃO: Secrets válidos são aceitos, implementation pode aceitar qualquer string
        """
        test_cases = [
            ("valid-secret-32-chars-long-enough", "Secret válido"),
            ("short", "Secret curto ainda funciona"),
            ("a" * 500, "Secret muito longo ainda funciona")
        ]
        
        for secret_value, description in test_cases:
            # Configurar secret
            os.environ['BRADAX_JWT_SECRET'] = secret_value
            
            # Forçar reimportação
            if 'broker.constants' in sys.modules:
                del sys.modules['broker.constants']
            
            # Deve funcionar (implementação atual aceita qualquer string não vazia)
            from broker.constants import HubSecurityConstants
            assert HubSecurityConstants.JWT_SECRET_KEY == secret_value
            
        # Teste específico para secret vazio/None (único caso que deve falhar)
        if 'BRADAX_JWT_SECRET' in os.environ:
            del os.environ['BRADAX_JWT_SECRET']
        
        if 'broker.constants' in sys.modules:
            del sys.modules['broker.constants']
        
        # Secret não definido deve causar erro
        with pytest.raises(ValueError):
            from broker.constants import HubSecurityConstants
    
    def test_hub_security_constants_api_key_constants_real(self):
        """
        Teste REAL: Constantes relacionadas a API keys
        VALIDAÇÃO: Configurações de API key estão corretas
        """
        # Configurar secret mínimo
        os.environ['BRADAX_JWT_SECRET'] = "test-secret-for-api-keys"
        
        # Forçar reimportação
        if 'broker.constants' in sys.modules:
            del sys.modules['broker.constants']
        
        from broker.constants import HubSecurityConstants
        
        # Validar constantes de API key
        assert HubSecurityConstants.API_KEY_PREFIX == 'bradax_'
        assert HubSecurityConstants.API_KEY_LENGTH == 64
        assert isinstance(HubSecurityConstants.API_KEY_LENGTH, int)
        assert len(HubSecurityConstants.API_KEY_PREFIX) > 0
    
    def test_hub_security_constants_integration_with_config_real(self):
        """
        Teste REAL: Integração das constantes com sistema de config
        VALIDAÇÃO: Constantes são usadas corretamente pelo sistema Settings
        """
        # Configurar secret para integração
        os.environ['BRADAX_JWT_SECRET'] = "integration-test-secret-32-chars"
        os.environ['BRADAX_JWT_EXPIRE_MINUTES'] = "45"
        
        # Forçar reimportação
        modules_to_reload = ['broker.constants', 'broker.config']
        for module in modules_to_reload:
            if module in sys.modules:
                del sys.modules[module]
        
        # Importar constantes e config
        from broker.constants import HubSecurityConstants
        from broker.config import Settings
        
        # Criar config que deve usar as constantes
        settings = Settings()
        
        # Validar integração - Settings deve usar os valores das HubSecurityConstants
        assert settings.jwt_secret_key == HubSecurityConstants.JWT_SECRET_KEY
        assert settings.jwt_expiration_minutes == HubSecurityConstants.JWT_EXPIRATION_MINUTES
        assert settings.jwt_algorithm == HubSecurityConstants.JWT_ALGORITHM
        
        # Validar valores específicos
        assert settings.jwt_secret_key == "integration-test-secret-32-chars"
        assert settings.jwt_expiration_minutes == 45
    
    def test_hub_security_constants_hotfix_validation_real(self):
        """
        Teste REAL: Validação específica do Hotfix 2 - JWT Security
        VALIDAÇÃO: Sistema exige BRADAX_JWT_SECRET e falha apropriadamente
        """
        # Teste cenário do hotfix: sistema deve EXIGIR secret e não ter fallback
        
        # 1. Sem secret - deve falhar (não ter fallback inseguro)
        if 'BRADAX_JWT_SECRET' in os.environ:
            del os.environ['BRADAX_JWT_SECRET']
        
        if 'broker.constants' in sys.modules:
            del sys.modules['broker.constants']
        
        with pytest.raises(ValueError) as exc_info:
            from broker.constants import HubSecurityConstants
        
        # Validar que erro é específico e claro
        error_msg = str(exc_info.value)
        assert "BRADAX_JWT_SECRET" in error_msg
        assert "obrigatória" in error_msg.lower()
        
        # 2. Com secret válido - deve funcionar
        os.environ['BRADAX_JWT_SECRET'] = "hotfix-validation-secret"
        
        if 'broker.constants' in sys.modules:
            del sys.modules['broker.constants']
        
        # Deve importar sem erro
        from broker.constants import HubSecurityConstants
        assert HubSecurityConstants.JWT_SECRET_KEY == "hotfix-validation-secret"
        
        # 3. Validar que não há fallback inseguro no código
        # Se o hotfix estiver correto, não deve haver secret hardcoded ou gerado automaticamente


# Execução standalone para validação rápida
if __name__ == "__main__":
    print("🔐 Testes de HubSecurityConstants - JWT Security")
    print("🎯 Objetivo: Validar Hotfix 2 - Obrigatoriedade de BRADAX_JWT_SECRET")
    print()
    
    # Teste crítico do hotfix
    test_instance = TestHubSecurityConstantsReal()
    test_instance.setup_method()
    
    try:
        test_instance.test_hub_security_constants_hotfix_validation_real()
        print("✅ Hotfix 2 (JWT Security) validado - secret obrigatório funcionando")
    except Exception as e:
        print(f"❌ PROBLEMA NO HOTFIX 2: {e}")
    finally:
        test_instance.teardown_method()
    
    # Executar todos os testes
    pytest.main([__file__, "-v", "--tb=short"])
