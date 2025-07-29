"""
LLM Management Interfaces - Bradax Broker

Interfaces para gerenciamento de modelos LLM com governança centralizada.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from enum import Enum


class LLMProviderType(Enum):
    """Tipos de provedores de LLM suportados"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"


class LLMCapability(Enum):
    """Capacidades dos modelos LLM"""
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    REASONING = "reasoning"
    FAST_RESPONSE = "fast_response"
    MULTIMODAL = "multimodal"
    FUNCTION_CALLING = "function_calling"


@dataclass
class LLMModelInfo:
    """Informações de um modelo LLM"""
    model_id: str
    name: str
    provider: LLMProviderType
    max_tokens: int
    cost_per_1k_input: float
    cost_per_1k_output: float
    capabilities: List[LLMCapability]
    enabled: bool = True
    description: Optional[str] = None
    version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "provider": self.provider.value,
            "max_tokens": self.max_tokens,
            "cost_per_1k_input": self.cost_per_1k_input,
            "cost_per_1k_output": self.cost_per_1k_output,
            "capabilities": [cap.value for cap in self.capabilities],
            "enabled": self.enabled,
            "description": self.description,
            "version": self.version
        }


@dataclass
class LLMRequest:
    """Requisição para um modelo LLM"""
    model_id: str
    messages: List[Dict[str, str]]
    project_id: str
    request_id: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stream: bool = False
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMResponse:
    """Resposta de um modelo LLM"""
    request_id: str
    model_id: str
    content: str
    finish_reason: str
    tokens_used: int
    cost_estimate: float
    response_time_ms: float
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "model_id": self.model_id,
            "content": self.content,
            "finish_reason": self.finish_reason,
            "tokens_used": self.tokens_used,
            "cost_estimate": self.cost_estimate,
            "response_time_ms": self.response_time_ms,
            "metadata": self.metadata
        }


class ILLMProvider(ABC):
    """Interface base para provedores de LLM"""
    
    @abstractmethod
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Gera resposta usando o modelo especificado"""
        pass
    
    @abstractmethod
    async def stream_response(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Gera resposta em stream"""
        pass
    
    @abstractmethod
    async def validate_request(self, request: LLMRequest) -> bool:
        """Valida se a requisição é válida para este provedor"""
        pass
    
    @abstractmethod
    def get_supported_models(self) -> List[LLMModelInfo]:
        """Retorna lista de modelos suportados"""
        pass
    
    @abstractmethod
    def get_model_info(self, model_id: str) -> Optional[LLMModelInfo]:
        """Retorna informações de um modelo específico"""
        pass


class ILLMRegistry(ABC):
    """Interface para registro de modelos LLM"""
    
    @abstractmethod
    async def register_model(self, model_info: LLMModelInfo) -> bool:
        """Registra um novo modelo"""
        pass
    
    @abstractmethod
    async def unregister_model(self, model_id: str) -> bool:
        """Remove um modelo do registro"""
        pass
    
    @abstractmethod
    async def get_model(self, model_id: str) -> Optional[LLMModelInfo]:
        """Busca informações de um modelo"""
        pass
    
    @abstractmethod
    async def list_models(self, 
                         provider: Optional[LLMProviderType] = None,
                         capability: Optional[LLMCapability] = None,
                         enabled_only: bool = True) -> List[LLMModelInfo]:
        """Lista modelos disponíveis com filtros"""
        pass
    
    @abstractmethod
    async def enable_model(self, model_id: str) -> bool:
        """Habilita um modelo"""
        pass
    
    @abstractmethod
    async def disable_model(self, model_id: str) -> bool:
        """Desabilita um modelo"""
        pass


class ILLMService(ABC):
    """Interface principal para serviços LLM"""
    
    @abstractmethod
    async def process_request(self, request: LLMRequest) -> LLMResponse:
        """Processa uma requisição LLM com governança completa"""
        pass
    
    @abstractmethod
    async def stream_request(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Processa requisição em stream"""
        pass
    
    @abstractmethod
    async def get_available_models(self, project_id: str) -> List[LLMModelInfo]:
        """Retorna modelos disponíveis para um projeto"""
        pass
    
    @abstractmethod
    async def validate_project_access(self, project_id: str, model_id: str) -> bool:
        """Valida se projeto tem acesso ao modelo"""
        pass
    
    @abstractmethod
    async def calculate_cost_estimate(self, 
                                    model_id: str, 
                                    input_tokens: int,
                                    output_tokens: int) -> float:
        """Calcula estimativa de custo"""
        pass


@dataclass
class LLMUsageMetrics:
    """Métricas de uso de LLM"""
    project_id: str
    model_id: str
    total_requests: int
    total_tokens: int
    total_cost: float
    avg_response_time: float
    error_rate: float
    period_start: str
    period_end: str


class ILLMMonitor(ABC):
    """Interface para monitoramento de LLM"""
    
    @abstractmethod
    async def record_usage(self, request: LLMRequest, response: LLMResponse) -> bool:
        """Registra uso de LLM"""
        pass
    
    @abstractmethod
    async def get_project_metrics(self, 
                                project_id: str,
                                start_date: Optional[str] = None,
                                end_date: Optional[str] = None) -> LLMUsageMetrics:
        """Retorna métricas de uso de um projeto"""
        pass
    
    @abstractmethod
    async def get_model_metrics(self,
                              model_id: str,
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None) -> Dict[str, Any]:
        """Retorna métricas de uso de um modelo"""
        pass
    
    @abstractmethod
    async def check_limits(self, project_id: str, model_id: str) -> Dict[str, Any]:
        """Verifica limites de uso para projeto"""
        pass
