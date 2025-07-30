"""
Constantes internas do bradax SDK

Configurações específicas do SDK para uso em projetos que baixam via Nexus.
"""

from typing import Dict, List, Any
from enum import Enum
import os


class BradaxEnvironment(Enum):
    """Ambientes suportados pelo SDK"""
    DEVELOPMENT = "development"
    TESTING = "testing" 
    STAGING = "staging"
    PRODUCTION = "production"


class SDKNetworkConstants:
    """Constantes de rede específicas do SDK"""
    
    # URLs do Hub/API (onde o SDK se conecta)
    DEVELOPMENT_HUB_URL = os.getenv('BRADAX_HUB_URL_DEV', 'http://localhost:8000')
    STAGING_HUB_URL = os.getenv('BRADAX_HUB_URL_STAGING', 'https://staging-api.bradax.com')
    PRODUCTION_HUB_URL = os.getenv('BRADAX_HUB_URL_PROD', 'https://api.bradax.com')
    
    # Timeouts do cliente SDK
    REQUEST_TIMEOUT = int(os.getenv('BRADAX_SDK_TIMEOUT', '30'))
    CONNECTION_TIMEOUT = int(os.getenv('BRADAX_SDK_CONNECT_TIMEOUT', '10'))
    READ_TIMEOUT = int(os.getenv('BRADAX_SDK_READ_TIMEOUT', '60'))


class SDKSecurityConstants:
    """Constantes de segurança do SDK"""
    
    # API Keys
    API_KEY_PREFIX = 'bradax_'
    API_KEY_MIN_LENGTH = 32
    
    # Headers
    USER_AGENT = f"bradax-sdk/{os.getenv('BRADAX_SDK_VERSION', '1.0.0')}"
    CONTENT_TYPE = 'application/json'


class SDKValidationConstants:
    """Constantes de validação do SDK"""
    
    # Project IDs
    PROJECT_ID_MIN_LENGTH = 8
    PROJECT_ID_MAX_LENGTH = 64
    PROJECT_ID_PREFIX = 'proj_'
    
    # Limites de payload
    MAX_PROMPT_LENGTH = int(os.getenv('BRADAX_MAX_PROMPT_LENGTH', '50000'))
    MAX_RESPONSE_LENGTH = int(os.getenv('BRADAX_MAX_RESPONSE_LENGTH', '100000'))


class SDKModelConstants:
    """Constantes de modelos LLM disponíveis via SDK"""
    
    # Modelos disponíveis
    AVAILABLE_MODELS = [
        'gpt-4.1-nano',
        'gpt-4.1-mini',
        'gpt-4.1',
        'gpt-4o-mini',
        'gpt-4o'
    ]
    
    DEFAULT_MODEL = 'gpt-4.1-nano'
    DEFAULT_MAX_TOKENS = 128000
    DEFAULT_TEMPERATURE = 0.7


def get_sdk_environment() -> BradaxEnvironment:
    """Retorna ambiente atual do SDK"""
    env_name = os.getenv('BRADAX_ENV', 'development').lower()
    try:
        return BradaxEnvironment(env_name)
    except ValueError:
        return BradaxEnvironment.DEVELOPMENT


def get_hub_url() -> str:
    """Retorna URL do Hub baseada no ambiente"""
    env = get_sdk_environment()
    
    if env == BradaxEnvironment.PRODUCTION:
        return SDKNetworkConstants.PRODUCTION_HUB_URL
    elif env == BradaxEnvironment.STAGING:
        return SDKNetworkConstants.STAGING_HUB_URL
    else:
        return SDKNetworkConstants.DEVELOPMENT_HUB_URL


def validate_project_id(project_id: str) -> bool:
    """Valida formato do project ID"""
    if not project_id:
        return False
    
    return (
        project_id.startswith(SDKValidationConstants.PROJECT_ID_PREFIX) and
        SDKValidationConstants.PROJECT_ID_MIN_LENGTH <= len(project_id) <= SDKValidationConstants.PROJECT_ID_MAX_LENGTH
    )


def validate_api_key(api_key: str) -> bool:
    """Valida formato da API key"""
    if not api_key:
        return False
    
    return (
        api_key.startswith(SDKSecurityConstants.API_KEY_PREFIX) and
        len(api_key) >= SDKSecurityConstants.API_KEY_MIN_LENGTH
    )


class SDKConstants:
    """Classe unificada com constantes principais do SDK para retrocompatibilidade"""
    
    # Timeout
    DEFAULT_TIMEOUT = SDKNetworkConstants.REQUEST_TIMEOUT
    
    # URL do broker
    DEFAULT_BROKER_URL = SDKNetworkConstants.DEVELOPMENT_HUB_URL
    
    # Regras de guardrails padrão
    GUARDRAIL_RULES = [
        {
            "id": "no_secrets",
            "pattern": r"(password|senha|secret|token|key)",
            "severity": "high",
            "description": "Detecta possíveis secrets/senhas nos prompts"
        },
        {
            "id": "no_pii",
            "pattern": r"(\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})",
            "severity": "medium", 
            "description": "Detecta CPF/CNPJ nos prompts"
        }
    ]
