"""
Configuração centralizada do bradax SDK

Sistema de configuração que elimina hard-code e permite
configuração flexível via environment variables.
"""

import os
import sys
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# Adicionar o path para bradax-constants se não estiver instalado
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'bradax-constants', 'src'))

try:
    from bradax_constants import (
        NetworkConstants,
        SecurityConstants,
        ValidationConstants,
        TestingConstants,
        get_environment,
        get_broker_url
    )
except ImportError:
    # Fallback para desenvolvimento
    class NetworkConstants:
        DEVELOPMENT_BROKER_URL = "http://localhost:8000"
        HTTP_REQUEST_TIMEOUT = 30
        
    class SecurityConstants:
        API_KEY_PREFIX = "bradax_"
        
    class ValidationConstants:
        MIN_VALID_YEAR = 2024
        MAX_VALID_YEAR = 2035
        
    class TestingConstants:
        TEST_PROJECT_PREFIX = "proj_test_"
        
    def get_environment():
        return "development"
        
    def get_broker_url():
        return "http://localhost:8000"


@dataclass
class BradaxSDKConfig:
    """
    Configuração principal do bradax SDK.
    
    Centraliza todas as configurações e elimina valores hard-coded.
    """
    
    # URLs e endpoints
    broker_url: str
    timeout: int
    
    # Autenticação e projeto
    project_id: str
    api_key_prefix: str
    
    # Validação
    min_valid_year: int
    max_valid_year: int
    
    # Ambiente
    environment: str
    debug: bool
    
    # Guardrails personalizados (além dos defaults do projeto)
    custom_guardrails: Dict[str, Any]
    enable_guardrails: bool
    guardrail_rules: List[str]
    
    # Telemetria local (incrementa a do broker)
    local_telemetry_enabled: bool
    enable_telemetry: bool
    telemetry_buffer_size: int
    
    # Custom settings do usuário
    custom_settings: Dict[str, Any]
    
    @classmethod
    def from_environment(cls) -> "BradaxSDKConfig":
        """
        Cria configuração a partir de variáveis de ambiente.
        
        Returns:
            Configuração do SDK baseada no ambiente atual
        """
        env = get_environment()
        
        # Ler URL do broker das variáveis de ambiente ou usar default
        broker_url = os.getenv("BRADAX_SDK_BROKER_URL", get_broker_url())
        
        return cls(
            broker_url=broker_url,
            timeout=NetworkConstants.HTTP_REQUEST_TIMEOUT,
            project_id=os.getenv("BRADAX_SDK_PROJECT_ID", "test-integration-project"),
            api_key_prefix=SecurityConstants.API_KEY_PREFIX,
            min_valid_year=ValidationConstants.MIN_VALID_YEAR,
            max_valid_year=ValidationConstants.MAX_VALID_YEAR,
            environment=env,
            debug=(env == "development"),
            custom_guardrails={},  # Inicialmente vazio, configurado via set_custom_guardrail()
            enable_guardrails=True,
            guardrail_rules=["default"],
            local_telemetry_enabled=True,
            enable_telemetry=True,
            telemetry_buffer_size=100,
            custom_settings={}
        )
    
    @classmethod
    def for_testing(cls) -> "BradaxSDKConfig":
        """
        Cria configuração otimizada para testes.
        
        Returns:
            Configuração com timeouts reduzidos e debug ativo
        """
        config = cls.from_environment()
        config.timeout = TestingConstants.TEST_TIMEOUT if hasattr(TestingConstants, 'TEST_TIMEOUT') else 5
        config.debug = True
        return config

    @classmethod
    def for_testing(
        cls,
        broker_url: str = "http://localhost:8000",
        project_id: str = "test-project",
        api_key: Optional[str] = None,
        enable_telemetry: bool = True,
        enable_guardrails: bool = True,
        timeout: int = 30,
        **kwargs
    ) -> "BradaxSDKConfig":
        """
        Cria configuração para testes (development/testing).
        
        Args:
            broker_url: URL do broker
            project_id: ID do projeto
            api_key: API key (ignorada por enquanto)
            enable_telemetry: Habilitar telemetria
            enable_guardrails: Habilitar guardrails
            timeout: Timeout em segundos
            **kwargs: Parâmetros adicionais
            
        Returns:
            Configuração específica para testes
        """
        # Validar broker_url
        if not broker_url.startswith(("http://", "https://")):
            raise ValueError(f"broker_url deve começar com http:// ou https://, recebido: {broker_url}")
        
        if not project_id or not project_id.strip():
            raise ValueError("project_id não pode estar vazio")
            
        if api_key is not None and (not api_key or not api_key.strip()):
            raise ValueError("api_key não pode estar vazia")
        
        return cls(
            broker_url=broker_url,
            timeout=timeout,
            project_id=project_id,
            api_key_prefix=SecurityConstants.API_KEY_PREFIX,
            min_valid_year=ValidationConstants.MIN_VALID_YEAR,
            max_valid_year=ValidationConstants.MAX_VALID_YEAR,
            environment="testing",
            debug=True,
            custom_guardrails=kwargs.get("custom_settings", {}) if kwargs.get("custom_settings") else {},
            enable_guardrails=enable_guardrails,
            guardrail_rules=["default"],
            local_telemetry_enabled=enable_telemetry,
            enable_telemetry=enable_telemetry,
            telemetry_buffer_size=100,
            custom_settings=kwargs.get("custom_settings", {})
        )
    
    @classmethod
    def for_integration_tests(cls, **kwargs) -> "BradaxSDKConfig":
        """
        DEPRECADO: Use for_testing() em vez deste método.
        Mantido para compatibilidade com código existente.
        """
        import warnings
        warnings.warn(
            "for_integration_tests() está deprecado. Use for_testing() para nomenclatura mais adequada.",
            DeprecationWarning,
            stacklevel=2
        )
        return cls.for_testing(**kwargs)
    
    @classmethod
    def for_production(
        cls,
        broker_url: str,
        project_id: str,
        api_key: str,
        enable_telemetry: bool = True,
        enable_guardrails: bool = True,
        timeout: int = 60,
        **kwargs
    ) -> "BradaxSDKConfig":
        """
        Cria configuração para ambiente de produção.
        
        IMPORTANTE: Esta configuração é usada apenas pelo sistema de deploy automático.
        Desenvolvedores não devem usar esta configuração diretamente.
        Testes em produção são executados pela esteira de CI/CD.
        
        Args:
            broker_url: URL do broker (obrigatório, HTTPS)
            project_id: ID do projeto (obrigatório)
            api_key: API key (obrigatório)
            enable_telemetry: Habilitar telemetria
            enable_guardrails: Habilitar guardrails
            timeout: Timeout em segundos
            **kwargs: Parâmetros adicionais
            
        Returns:
            Configuração específica para produção (uso interno do deploy)
        """
        # Validações mais rigorosas para produção
        if not broker_url or not broker_url.strip():
            raise ValueError("broker_url é obrigatório para produção")
        if not broker_url.startswith("https://"):
            raise ValueError("broker_url deve usar HTTPS em produção")
        if not project_id or not project_id.strip():
            raise ValueError("project_id é obrigatório para produção")
        if not api_key or not api_key.strip():
            raise ValueError("api_key é obrigatória para produção")
        
        return cls(
            broker_url=broker_url,
            timeout=timeout,
            project_id=project_id,
            api_key_prefix=SecurityConstants.API_KEY_PREFIX,
            min_valid_year=ValidationConstants.MIN_VALID_YEAR,
            max_valid_year=ValidationConstants.MAX_VALID_YEAR,
            environment="production",
            debug=False,
            custom_guardrails=kwargs.get("custom_settings", {}) if kwargs.get("custom_settings") else {},
            enable_guardrails=enable_guardrails,
            guardrail_rules=["strict", "compliance"],
            local_telemetry_enabled=enable_telemetry,
            enable_telemetry=enable_telemetry,
            telemetry_buffer_size=1000,
            custom_settings=kwargs.get("custom_settings", {})
        )
    
    @classmethod
    def for_development(
        cls,
        broker_url: str = "http://localhost:8000",
        project_id: str = "dev-project",
        api_key: Optional[str] = None,
        enable_telemetry: bool = False,
        enable_guardrails: bool = False,
        timeout: int = 30,
        **kwargs
    ) -> "BradaxSDKConfig":
        """
        Cria configuração para ambiente de desenvolvimento local.
        
        Esta é a configuração recomendada para desenvolvedores.
        Use esta configuração para desenvolvimento e testes locais.
        
        Args:
            broker_url: URL do broker local
            project_id: ID do projeto de desenvolvimento
            api_key: API key (opcional para desenvolvimento)
            enable_telemetry: Habilitar telemetria local
            enable_guardrails: Habilitar guardrails locais
            timeout: Timeout em segundos
            **kwargs: Parâmetros adicionais
            
        Returns:
            Configuração específica para desenvolvimento
        """
        return cls(
            broker_url=broker_url,
            timeout=timeout,
            project_id=project_id,
            api_key_prefix=SecurityConstants.API_KEY_PREFIX,
            min_valid_year=ValidationConstants.MIN_VALID_YEAR,
            max_valid_year=ValidationConstants.MAX_VALID_YEAR,
            environment="development",
            debug=True,
            custom_guardrails=kwargs.get("custom_settings", {}) if kwargs.get("custom_settings") else {},
            enable_guardrails=enable_guardrails,
            guardrail_rules=["basic"],
            local_telemetry_enabled=enable_telemetry,
            enable_telemetry=enable_telemetry,
            telemetry_buffer_size=50,
            custom_settings=kwargs.get("custom_settings", {})
        )
    
    def is_production(self) -> bool:
        """Verifica se está em ambiente de produção."""
        return self.environment == "production"
    
    def is_development(self) -> bool:
        """Verifica se está em ambiente de desenvolvimento."""
        return self.environment == "development"
    
    def get_headers(self) -> Dict[str, str]:
        """Retorna headers padrão para requisições HTTP."""
        return {
            "User-Agent": f"bradax-sdk/1.0.0 (env:{self.environment})",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def set_custom_guardrail(self, name: str, rule: Dict[str, Any]) -> None:
        """
        Adiciona um guardrail personalizado.
        
        IMPORTANTE: Isso ADICIONA aos guardrails defaults do projeto,
        não substitui. O projeto sempre mantém seus guardrails obrigatórios.
        
        Args:
            name: Nome único do guardrail personalizado
            rule: Regra do guardrail com configurações específicas
        """
        self.custom_guardrails[name] = rule
    
    def remove_custom_guardrail(self, name: str) -> bool:
        """
        Remove um guardrail personalizado.
        
        Args:
            name: Nome do guardrail a remover
            
        Returns:
            True se removido, False se não existia
        """
        return self.custom_guardrails.pop(name, None) is not None
    
    def get_custom_guardrails(self) -> Dict[str, Any]:
        """Retorna cópia dos guardrails personalizados."""
        return self.custom_guardrails.copy()
    
    def has_custom_guardrails(self) -> bool:
        """Verifica se há guardrails personalizados configurados."""
        return len(self.custom_guardrails) > 0


@dataclass 
class ProjectConfig:
    """
    Configuração específica de um projeto.
    
    Armazena informações de autenticação e configurações
    específicas do projeto corporativo.
    """
    
    project_id: str
    api_key: str
    organization: Optional[str] = None
    department: Optional[str] = None
    budget_limit: Optional[float] = None
    allowed_models: Optional[List[str]] = None
    
    def __post_init__(self):
        """Validação automática após inicialização."""
        self._validate_project_id()
        self._validate_api_key()
    
    def _validate_project_id(self):
        """Valida formato do project ID."""
        if not self.project_id.startswith("proj_"):
            raise ValueError(f"Project ID deve começar com 'proj_', recebido: {self.project_id}")
        
        # Extrair ano do project ID (formato: proj_*_*_*_YYYY_*)
        parts = self.project_id.split("_")
        if len(parts) >= 5:
            try:
                year = int(parts[4])
                config = BradaxSDKConfig.from_environment()
                if year < config.min_valid_year or year > config.max_valid_year:
                    raise ValueError(
                        f"Ano no project ID deve estar entre {config.min_valid_year} "
                        f"e {config.max_valid_year}, recebido: {year}"
                    )
            except (ValueError, IndexError):
                # Se não conseguir extrair o ano, apenas avisa
                pass
    
    def _validate_api_key(self):
        """Valida formato da API key."""
        config = BradaxSDKConfig.from_environment()
        if not self.api_key.startswith(config.api_key_prefix):
            raise ValueError(
                f"API key deve começar com '{config.api_key_prefix}', "
                f"recebido: {self.api_key[:10]}..."
            )
    
    def is_test_project(self) -> bool:
        """Verifica se é um projeto de teste."""
        return self.project_id.startswith(TestingConstants.TEST_PROJECT_PREFIX)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário para logging/serialização."""
        return {
            "project_id": self.project_id,
            "api_key": f"{self.api_key[:10]}..." if self.api_key else None,
            "organization": self.organization,
            "department": self.department,
            "budget_limit": self.budget_limit,
            "allowed_models": self.allowed_models,
            "is_test": self.is_test_project()
        }


# Instância global da configuração
_sdk_config: Optional[BradaxSDKConfig] = None


def get_sdk_config() -> BradaxSDKConfig:
    """
    Retorna configuração global do SDK.
    
    Inicializa automaticamente se necessário.
    
    Returns:
        Configuração global do SDK
    """
    global _sdk_config
    if _sdk_config is None:
        _sdk_config = BradaxSDKConfig.from_environment()
    return _sdk_config


def set_sdk_config(config: BradaxSDKConfig):
    """
    Define configuração global do SDK.
    
    Args:
        config: Nova configuração a ser utilizada
    """
    global _sdk_config
    _sdk_config = config


def reset_sdk_config():
    """Reseta a configuração global (útil para testes)."""
    global _sdk_config
    _sdk_config = None
