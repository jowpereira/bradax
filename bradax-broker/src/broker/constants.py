"""
Constantes internas do bradax Hub/API

Configurações específicas do servidor Hub que valida projetos via SDK.
"""

from typing import Dict, List, Any
from enum import Enum
import os


class BradaxEnvironment(Enum):
    """Ambientes suportados pelo Hub"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class HubNetworkConstants:
    """Constantes de rede do Hub/API"""
    
    # Servidor
    DEFAULT_PORT = int(os.getenv('BRADAX_HUB_PORT', '8000'))
    BIND_HOST = os.getenv('BRADAX_HUB_HOST', '0.0.0.0')
    
    # CORS
    CORS_ORIGINS_DEV = [
        'http://localhost:3000',
        'http://localhost:8080',
        'http://127.0.0.1:3000'
    ]
    CORS_ORIGINS_PROD = [
        'https://portal.bradax.com',
        'https://app.bradax.com'
    ]
    
    # Timeouts
    REQUEST_TIMEOUT = int(os.getenv('BRADAX_HUB_REQUEST_TIMEOUT', '120'))
    LLM_TIMEOUT = int(os.getenv('BRADAX_HUB_LLM_TIMEOUT', '180'))


class HubSecurityConstants:
    """Constantes de segurança do Hub"""
    
    # JWT
    JWT_EXPIRATION_MINUTES = int(os.getenv('BRADAX_JWT_EXPIRE_MINUTES', '15'))
    JWT_ALGORITHM = 'HS256'
    JWT_SECRET_KEY = os.getenv('BRADAX_JWT_SECRET', 'dev-secret-change-in-production')
    
    # API Keys
    API_KEY_PREFIX = 'bradax_'
    API_KEY_LENGTH = 64
    
    # Rate Limiting
    REQUESTS_PER_MINUTE = int(os.getenv('BRADAX_RATE_LIMIT_RPM', '60'))
    REQUESTS_PER_HOUR = int(os.getenv('BRADAX_RATE_LIMIT_RPH', '1000'))
    MAX_CONCURRENT_REQUESTS = int(os.getenv('BRADAX_MAX_CONCURRENT', '10'))


class HubValidationConstants:
    """Constantes de validação do Hub"""
    
    # Projects
    PROJECT_ID_MIN_LENGTH = 8
    PROJECT_ID_MAX_LENGTH = 64
    PROJECT_NAME_MAX_LENGTH = 100
    
    # Payloads
    MAX_PROMPT_SIZE = int(os.getenv('BRADAX_MAX_PROMPT_SIZE', '100000'))  # 100KB
    MAX_RESPONSE_SIZE = int(os.getenv('BRADAX_MAX_RESPONSE_SIZE', '500000'))  # 500KB
    
    # Error messages
    ERROR_MESSAGE_MAX_LENGTH = 500


class HubLLMConstants:
    """Constantes para integração com LLMs"""
    
    # Modelos suportados pelo Hub
    SUPPORTED_MODELS = [
        'gpt-4.1-nano',
        'gpt-4.1-mini',
        'gpt-4.1',
        'gpt-4o-mini',
        'gpt-4o'
    ]
    
    # Limites por modelo
    MODEL_LIMITS = {
        'gpt-4.1-nano': {'max_tokens': 128000, 'cost_per_1k': 0.000025},
        'gpt-4.1-mini': {'max_tokens': 128000, 'cost_per_1k': 0.000150},
        'gpt-4.1': {'max_tokens': 128000, 'cost_per_1k': 0.003},
        'gpt-4o-mini': {'max_tokens': 128000, 'cost_per_1k': 0.000150},
        'gpt-4o': {'max_tokens': 128000, 'cost_per_1k': 0.005}
    }
    
    DEFAULT_MODEL = 'gpt-4.1-nano'
    DEFAULT_MAX_TOKENS = 8192
    DEFAULT_TEMPERATURE = 0.7


class HubBudgetConstants:
    """Constantes de orçamento e billing"""
    
    # Orçamentos padrão por ambiente
    DEFAULT_BUDGET_DEV = 100.0  # USD
    DEFAULT_BUDGET_STAGING = 500.0  # USD
    DEFAULT_BUDGET_PROD = 10000.0  # USD
    
    # Thresholds de alerta
    WARNING_THRESHOLD = 0.80  # 80%
    CRITICAL_THRESHOLD = 0.95  # 95%
    
    # Billing cycle
    BILLING_CYCLE_DAYS = 30


def get_hub_environment() -> BradaxEnvironment:
    """Retorna ambiente atual do Hub"""
    env_name = os.getenv('BRADAX_ENV', 'development').lower()
    try:
        return BradaxEnvironment(env_name)
    except ValueError:
        return BradaxEnvironment.DEVELOPMENT


def get_cors_origins() -> List[str]:
    """Retorna origens CORS baseadas no ambiente"""
    env = get_hub_environment()
    
    if env == BradaxEnvironment.PRODUCTION:
        return HubNetworkConstants.CORS_ORIGINS_PROD
    else:
        return HubNetworkConstants.CORS_ORIGINS_DEV


def get_default_budget() -> float:
    """Retorna orçamento padrão baseado no ambiente"""
    env = get_hub_environment()
    
    if env == BradaxEnvironment.PRODUCTION:
        return HubBudgetConstants.DEFAULT_BUDGET_PROD
    elif env == BradaxEnvironment.STAGING:
        return HubBudgetConstants.DEFAULT_BUDGET_STAGING
    else:
        return HubBudgetConstants.DEFAULT_BUDGET_DEV


def validate_model(model: str) -> bool:
    """Valida se modelo é suportado"""
    return model in HubLLMConstants.SUPPORTED_MODELS


def get_model_limits(model: str) -> Dict[str, Any]:
    """Retorna limites específicos do modelo"""
    return HubLLMConstants.MODEL_LIMITS.get(model, {
        'max_tokens': HubLLMConstants.DEFAULT_MAX_TOKENS,
        'cost_per_1k': 0.0
    })
