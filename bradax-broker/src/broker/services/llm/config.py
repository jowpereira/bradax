"""
LLM Configuration Management

Gerencia configurações, modelos e capabilidades do sistema LLM.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"  # Para futuro
    GEMINI = "gemini"       # Para futuro


@dataclass
class LLMModelInfo:
    """Informações sobre um modelo LLM"""
    model_id: str
    name: str
    provider: str  # Note: usando 'provider' não 'provider_type'
    max_tokens: int
    supports_streaming: bool = True
    supports_functions: bool = False
    cost_per_token: float = 0.0
    description: str = ""
    provider_model_name: Optional[str] = None  # Nome do modelo no provider (pode ser diferente do model_id)


@dataclass
class ProviderConfig:
    """Configuração de um provedor LLM"""
    name: str
    provider_type: str
    api_key: Optional[str] = None
    api_key_env_var: str = "OPENAI_API_KEY"  # Adicionando este campo que estava faltando
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    enabled: bool = True


class LLMConfigurationManager:
    """Gerenciador central de configurações LLM"""
    
    def __init__(self):
        # NÃO inicializa modelos automaticamente
        # Modelos vêm do projeto via token
        pass
    
    def get_model_catalog(self) -> Dict[str, LLMModelInfo]:
        """
        Catálogo de modelos DISPONÍVEIS no sistema
        IMPORTANTE: Não define quais usar - isso vem do projeto
        """
        return {
            "gpt-4o-mini": LLMModelInfo(
                model_id="gpt-4o-mini",
                name="GPT-4O Mini",
                provider="openai",
                max_tokens=4096,
                supports_streaming=True,
                supports_functions=True,
                cost_per_token=0.00015,
                description="Modelo econômico para tarefas gerais",
                provider_model_name="gpt-4o-mini"
            ),
            "gpt-4o": LLMModelInfo(
                model_id="gpt-4o",
                name="GPT-4O",
                provider="openai",
                max_tokens=4096,
                supports_streaming=True,
                supports_functions=True,
                cost_per_token=0.03,
                description="Modelo premium para tarefas complexas",
                provider_model_name="gpt-4o"
            ),
            "gpt-3.5-turbo": LLMModelInfo(
                model_id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                provider="openai",
                max_tokens=4096,
                supports_streaming=True,
                supports_functions=True,
                cost_per_token=0.002,
                description="Modelo rápido para conversas",
                provider_model_name="gpt-3.5-turbo"
            )
        }
    
    def get_model_info(self, model_id: str) -> Optional[LLMModelInfo]:
        """Busca informações específicas de um modelo pelo ID"""
        catalog = self.get_model_catalog()
        return catalog.get(model_id)
    
    def validate_model_available(self, model_id: str) -> bool:
        """Valida se modelo está disponível no catálogo"""
        return model_id in self.get_model_catalog()
    
    def get_available_model_ids(self) -> List[str]:
        """Lista IDs de modelos disponíveis"""
        return list(self.get_model_catalog().keys())
    
    def validate_model_for_project(self, model_id: str, allowed_models: List[str]) -> bool:
        """Valida se um modelo está permitido para o projeto"""
        catalog = self.get_model_catalog()
        return (model_id in allowed_models and model_id in catalog)


# Instância global do gerenciador de configuração LLM
llm_config = LLMConfigurationManager()
