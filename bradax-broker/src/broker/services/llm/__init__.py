"""
LLM Services Module - Bradax Broker

Módulo completo para gerenciamento de Large Language Models.
"""

# Interfaces
from .interfaces import (
    ILLMProvider,
    LLMRequest,
    LLMResponse, 
    LLMModelInfo,
    LLMProviderType,
    LLMCapability
)

# Configuração
from .config import (
    LLMConfigurationManager,
    ProviderConfig,
    llm_config
)

# Providers com LangChain
from .providers import (
    OpenAIProvider,
    get_available_providers,
    get_provider
)

# Serviço principal
from .service import (
    LLMService,
    llm_service
)

__all__ = [
    # Interfaces
    "ILLMProvider",
    "LLMRequest", 
    "LLMResponse",
    "LLMModelInfo",
    "LLMProviderType",
    "LLMCapability",
    
    # Configuração
    "LLMConfigurationManager",
    "ProviderConfig", 
    "llm_config",
    
    # Providers (LangChain)
    "OpenAIProvider",
    "get_available_providers",
    "get_provider",
    
    # Serviço
    "LLMService",
    "llm_service"
]
