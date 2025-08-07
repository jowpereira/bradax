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


class SDKTelemetryConstants:
    """Constantes específicas de telemetria do SDK"""
    
    # Versão do SDK
    SDK_VERSION = "1.0.0"
    
    # Headers de telemetria
    HEADER_SDK_VERSION = "x-bradax-sdk-version"
    HEADER_MACHINE_FINGERPRINT = "x-bradax-machine-fingerprint"
    HEADER_SESSION_ID = "x-bradax-session-id"
    HEADER_TELEMETRY_ENABLED = "x-bradax-telemetry-enabled"
    HEADER_ENVIRONMENT = "x-bradax-environment"
    HEADER_PLATFORM = "x-bradax-platform"
    HEADER_PYTHON_VERSION = "x-bradax-python-version"
    HEADER_TIMESTAMP = "x-bradax-timestamp"
    HEADER_REQUEST_SOURCE = "x-bradax-request-source"
    
    # Valores padrão dos headers
    TELEMETRY_ENABLED_VALUE = "true"
    REQUEST_SOURCE_VALUE = "sdk"
    DEFAULT_ENVIRONMENT = "development"
    
    # URLs
    DEFAULT_BROKER_URL = "http://localhost:8001"
    
    # URLs padrão do broker para telemetria
    DEFAULT_BROKER_URL = "http://localhost:8001"
    DEVELOPMENT_BROKER_URL = "http://localhost:8001"
    STAGING_BROKER_URL = "https://staging-broker.bradax.com"
    PRODUCTION_BROKER_URL = "https://broker.bradax.com"
    
    # Ambiente padrão
    DEFAULT_ENVIRONMENT = "development"
    
    # Headers de telemetria
    HEADER_SDK_VERSION = "x-bradax-sdk-version"
    HEADER_MACHINE_FINGERPRINT = "x-bradax-machine-fingerprint"
    HEADER_SESSION_ID = "x-bradax-session-id"
    HEADER_TELEMETRY_ENABLED = "x-bradax-telemetry-enabled"
    HEADER_ENVIRONMENT = "x-bradax-environment"
    HEADER_PLATFORM = "x-bradax-platform"
    HEADER_PYTHON_VERSION = "x-bradax-python-version"
    HEADER_TIMESTAMP = "x-bradax-timestamp"
    HEADER_REQUEST_SOURCE = "x-bradax-request-source"
    
    # Configurações de cache
    DEFAULT_CACHE_MAX_AGE_MINUTES = 60


class SDKModelConstants:
    """Constantes de modelos LLM do SDK"""
    
    # Modelo padrão
    DEFAULT_MODEL = "gpt-4.1-nano"
    
    # Parâmetros padrão
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 1000


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
