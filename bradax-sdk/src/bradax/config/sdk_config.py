"""
Configuração centralizada do bradax SDK

Sistema de configuração que elimina hard-code e permite
configuração flexível via environment variables.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass

# Usar constants internas do SDK
from ..constants import (
    BradaxEnvironment,
    SDKNetworkConstants,
    SDKSecurityConstants,
    SDKValidationConstants,
    SDKModelConstants,
    get_sdk_environment,
    get_hub_url,
    validate_project_id,
    validate_api_key
)


@dataclass
class BradaxSDKConfig:
    """
    Configuração principal do bradax SDK.
    
    Centraliza todas as configurações e elimina valores hard-coded.
    """
    
    # Configuração de rede
    hub_url: str = None
    request_timeout: int = SDKNetworkConstants.REQUEST_TIMEOUT
    connection_timeout: int = SDKNetworkConstants.CONNECTION_TIMEOUT
    read_timeout: int = SDKNetworkConstants.READ_TIMEOUT
    
    # Configuração de ambiente
    environment: BradaxEnvironment = None
    debug: bool = False
    
    # Headers
    user_agent: str = SDKSecurityConstants.USER_AGENT
    content_type: str = SDKSecurityConstants.CONTENT_TYPE
    
    def __post_init__(self):
        """Inicialização automática após criação"""
        if self.environment is None:
            self.environment = get_sdk_environment()
        
        if self.hub_url is None:
            self.hub_url = get_hub_url()
        
        if self.environment == BradaxEnvironment.DEVELOPMENT:
            self.debug = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte configuração para dicionário"""
        return {
            'hub_url': self.hub_url,
            'environment': self.environment.value,
            'debug': self.debug,
            'timeouts': {
                'request': self.request_timeout,
                'connection': self.connection_timeout,
                'read': self.read_timeout
            },
            'headers': {
                'user_agent': self.user_agent,
                'content_type': self.content_type
            }
        }


@dataclass
class ProjectConfig:
    """
    Configuração específica de projeto.
    
    Gerencia configurações por projeto individual.
    """
    
    project_id: str = ""
    name: str = ""
    api_key: str = ""
    
    # Configurações de modelo
    default_model: str = SDKModelConstants.DEFAULT_MODEL
    max_tokens: int = SDKModelConstants.DEFAULT_MAX_TOKENS
    temperature: float = SDKModelConstants.DEFAULT_TEMPERATURE
    
    def __post_init__(self):
        """Validação automática após criação"""
        if self.project_id and not validate_project_id(self.project_id):
            raise ValueError(f"Project ID inválido: {self.project_id}")
        
        if self.api_key and not validate_api_key(self.api_key):
            raise ValueError(f"API Key inválida")
        
        if self.default_model not in SDKModelConstants.AVAILABLE_MODELS:
            raise ValueError(f"Modelo não suportado: {self.default_model}")
    
    def is_test_project(self) -> bool:
        """Verifica se é um projeto de teste"""
        return self.project_id.startswith('proj_test_')
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte configuração do projeto para dicionário"""
        return {
            'project_id': self.project_id,
            'name': self.name,
            'model_config': {
                'default_model': self.default_model,
                'max_tokens': self.max_tokens,
                'temperature': self.temperature
            },
            'is_test': self.is_test_project()
        }


def create_sdk_config(environment: Optional[str] = None) -> BradaxSDKConfig:
    """
    Factory para criar configuração do SDK.
    
    Args:
        environment: Ambiente específico (opcional)
        
    Returns:
        Configuração do SDK
    """
    if environment:
        os.environ['BRADAX_ENV'] = environment
    
    return BradaxSDKConfig()


def create_project_config(
    project_id: str,
    api_key: str,
    name: str = "",
    model: str = SDKModelConstants.DEFAULT_MODEL
) -> ProjectConfig:
    """
    Factory para criar configuração de projeto.
    
    Args:
        project_id: ID do projeto
        api_key: API key do projeto
        name: Nome do projeto (opcional)
        model: Modelo padrão (opcional)
        
    Returns:
        Configuração do projeto
    """
    return ProjectConfig(
        project_id=project_id,
        api_key=api_key,
        name=name or f"Project {project_id}",
        default_model=model
    )


# ---------------------------------------------------------------------------
# Helpers de configuração global
# ---------------------------------------------------------------------------
_GLOBAL_SDK_CONFIG: BradaxSDKConfig | None = None


def get_sdk_config() -> BradaxSDKConfig:
    """Retorna instância global de configuração do SDK."""
    global _GLOBAL_SDK_CONFIG
    if _GLOBAL_SDK_CONFIG is None:
        _GLOBAL_SDK_CONFIG = BradaxSDKConfig()
    return _GLOBAL_SDK_CONFIG


def set_sdk_config(config: BradaxSDKConfig) -> None:
    """Define configuração global do SDK."""
    global _GLOBAL_SDK_CONFIG
    _GLOBAL_SDK_CONFIG = config


def reset_sdk_config() -> None:
    """Reseta configuração global do SDK."""
    global _GLOBAL_SDK_CONFIG
    _GLOBAL_SDK_CONFIG = None


def get_global_config() -> Dict[str, Any]:
    """
    Retorna configuração global consolidada.
    
    Returns:
        Dicionário com toda a configuração
    """
    sdk_config = create_sdk_config()
    
    return {
        'sdk': sdk_config.to_dict(),
        'environment': get_sdk_environment().value,
        'hub_url': get_hub_url(),
        'available_models': SDKModelConstants.AVAILABLE_MODELS,
        'validation': {
            'api_key_prefix': SDKSecurityConstants.API_KEY_PREFIX,
            'project_id_prefix': SDKValidationConstants.PROJECT_ID_PREFIX,
            'max_prompt_length': SDKValidationConstants.MAX_PROMPT_LENGTH
        }
    }
