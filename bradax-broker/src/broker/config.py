"""
Configuração centralizada do bradax Hub/API

Sistema de configuração que elimina hard-code e permite
configuração flexível via environment variables.
"""

import os
from typing import Dict, Any, List
from pydantic import BaseModel, validator

# Usar constants internas do Hub
from .constants import (
    BradaxEnvironment,
    HubNetworkConstants,
    HubSecurityConstants,
    HubValidationConstants,
    HubLLMConstants,
    HubBudgetConstants,
    get_hub_environment,
    get_cors_origins,
    get_default_budget,
    validate_model,
    get_model_limits
)


class Settings(BaseModel):
    """
    Configurações do Hub/API usando Pydantic.
    
    Todas as configurações são externalizáveis via environment variables.
    """
    
    # Ambiente
    environment: BradaxEnvironment = get_hub_environment()
    debug: bool = False
    
    # Servidor
    host: str = HubNetworkConstants.BIND_HOST
    port: int = HubNetworkConstants.DEFAULT_PORT
    
    # CORS
    cors_origins: List[str] = None
    
    # Timeouts
    request_timeout: int = HubNetworkConstants.REQUEST_TIMEOUT
    llm_timeout: int = HubNetworkConstants.LLM_TIMEOUT
    
    # Segurança
    jwt_secret_key: str = HubSecurityConstants.JWT_SECRET_KEY
    jwt_expiration_minutes: int = HubSecurityConstants.JWT_EXPIRATION_MINUTES
    jwt_algorithm: str = HubSecurityConstants.JWT_ALGORITHM
    
    # Rate Limiting
    requests_per_minute: int = HubSecurityConstants.REQUESTS_PER_MINUTE
    requests_per_hour: int = HubSecurityConstants.REQUESTS_PER_HOUR
    max_concurrent: int = HubSecurityConstants.MAX_CONCURRENT_REQUESTS
    
    # Modelos LLM
    supported_models: List[str] = HubLLMConstants.SUPPORTED_MODELS
    default_model: str = HubLLMConstants.DEFAULT_MODEL
    default_max_tokens: int = HubLLMConstants.DEFAULT_MAX_TOKENS
    
    # Orçamento
    default_budget: float = None
    budget_warning_threshold: float = HubBudgetConstants.WARNING_THRESHOLD
    budget_critical_threshold: float = HubBudgetConstants.CRITICAL_THRESHOLD
    
    def __init__(self, **kwargs):
        # Configurações automáticas baseadas no ambiente
        if 'cors_origins' not in kwargs:
            kwargs['cors_origins'] = get_cors_origins()
        
        if 'default_budget' not in kwargs:
            kwargs['default_budget'] = get_default_budget()
        
        super().__init__(**kwargs)
        
        if self.environment == BradaxEnvironment.DEVELOPMENT:
            self.debug = True
    
    @validator('environment', pre=True)
    def validate_environment(cls, v):
        if isinstance(v, str):
            return BradaxEnvironment(v.lower())
        return v
    
    @validator('supported_models')
    def validate_models(cls, v):
        for model in v:
            if not validate_model(model):
                raise ValueError(f"Modelo não suportado: {model}")
        return v
    
    @validator('jwt_secret_key')
    def validate_jwt_secret(cls, v, values):
        env = values.get('environment', BradaxEnvironment.DEVELOPMENT)
        if env == BradaxEnvironment.PRODUCTION and v == 'dev-secret-change-in-production':
            raise ValueError("JWT secret deve ser alterado em produção")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte configurações para dicionário"""
        return {
            'environment': self.environment.value,
            'debug': self.debug,
            'server': {
                'host': self.host,
                'port': self.port
            },
            'cors_origins': self.cors_origins,
            'timeouts': {
                'request': self.request_timeout,
                'llm': self.llm_timeout
            },
            'security': {
                'jwt_expiration_minutes': self.jwt_expiration_minutes,
                'requests_per_minute': self.requests_per_minute,
                'requests_per_hour': self.requests_per_hour,
                'max_concurrent': self.max_concurrent
            },
            'models': {
                'supported': self.supported_models,
                'default': self.default_model,
                'default_max_tokens': self.default_max_tokens
            },
            'budget': {
                'default': self.default_budget,
                'warning_threshold': self.budget_warning_threshold,
                'critical_threshold': self.budget_critical_threshold
            }
        }


# Instância global de configurações
settings = Settings()


def get_cors_origins_for_environment() -> List[str]:
    """Retorna origens CORS para o ambiente atual"""
    return get_cors_origins()


def get_model_configuration(model: str) -> Dict[str, Any]:
    """Retorna configuração específica de um modelo"""
    if not validate_model(model):
        raise ValueError(f"Modelo não suportado: {model}")
    
    return get_model_limits(model)


def is_production() -> bool:
    """Verifica se está em ambiente de produção"""
    return settings.environment == BradaxEnvironment.PRODUCTION


def is_development() -> bool:
    """Verifica se está em ambiente de desenvolvimento"""
    return settings.environment == BradaxEnvironment.DEVELOPMENT


def get_configuration_summary() -> Dict[str, Any]:
    """Retorna resumo da configuração atual"""
    return {
        'environment': settings.environment.value,
        'port': settings.port,
        'cors_origins_count': len(settings.cors_origins),
        'supported_models_count': len(settings.supported_models),
        'default_model': settings.default_model,
        'jwt_expiration': settings.jwt_expiration_minutes,
        'rate_limits': {
            'rpm': settings.requests_per_minute,
            'rph': settings.requests_per_hour,
            'concurrent': settings.max_concurrent
        },
        'budget': {
            'default': settings.default_budget,
            'warning_at': f"{settings.budget_warning_threshold * 100}%",
            'critical_at': f"{settings.budget_critical_threshold * 100}%"
        }
    }
