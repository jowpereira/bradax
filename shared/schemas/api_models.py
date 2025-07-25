"""
Schemas Pydantic compartilhados entre SDK e Broker

Estes schemas definem os contratos de dados para comunicação
HTTP REST e validação de payloads.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Enums
class TokenType(str, Enum):
    BEARER = "Bearer"


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class GraphStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


# Base Models
class BaseRequest(BaseModel):
    request_id: Optional[str] = Field(None, description="ID único da requisição")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class BaseResponse(BaseModel):
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Authentication Models
class AuthRequest(BaseRequest):
    project_id: str = Field(..., description="ID do projeto")
    api_key: str = Field(..., description="Chave de API do projeto")
    scopes: List[str] = Field(default_factory=list, description="Escopos solicitados")


class AuthResponse(BaseResponse):
    access_token: str = Field(..., description="Token JWT de acesso")
    refresh_token: str = Field(..., description="Token de refresh")
    expires_in: int = Field(..., description="Tempo de expiração em segundos")
    token_type: TokenType = Field(default=TokenType.BEARER)
    scopes: List[str] = Field(..., description="Escopos concedidos")


class RefreshRequest(BaseRequest):
    refresh_token: str = Field(..., description="Token de refresh")


class ValidateRequest(BaseRequest):
    access_token: str = Field(..., description="Token JWT para validação")


class ValidateResponse(BaseResponse):
    valid: bool = Field(..., description="Se o token é válido")
    project_id: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None


# LLM Models
class Message(BaseModel):
    role: MessageRole = Field(..., description="Papel da mensagem")
    content: str = Field(..., description="Conteúdo da mensagem")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class LLMParameters(BaseModel):
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(None, gt=0)
    stop_sequences: Optional[List[str]] = None
    stream: bool = Field(default=False)


class Usage(BaseModel):
    prompt_tokens: int = Field(..., ge=0)
    completion_tokens: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)
    cost_usd: Optional[float] = Field(None, ge=0.0)


class LLMRequest(BaseRequest):
    model: str = Field(..., description="Nome do modelo LLM")
    messages: List[Message] = Field(..., min_items=1)
    parameters: Optional[LLMParameters] = None


class LLMResponse(BaseResponse):
    content: str = Field(..., description="Resposta gerada")
    model: str = Field(..., description="Modelo utilizado")
    usage: Usage = Field(..., description="Estatísticas de uso")


class LLMStreamResponse(BaseModel):
    delta: str = Field(..., description="Fragmento de texto")
    finished: bool = Field(default=False)
    usage: Optional[Usage] = None


# Vector Database Models
class VectorQueryRequest(BaseRequest):
    collection: str = Field(..., description="Nome da coleção")
    query_vector: Optional[List[float]] = None
    query_text: Optional[str] = None
    top_k: int = Field(default=10, gt=0, le=100)
    threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    filters: Optional[Dict[str, Any]] = None

    def model_validate(cls, values):
        query_vector = values.get('query_vector')
        query_text = values.get('query_text')
        
        if not query_vector and not query_text:
            raise ValueError('Either query_vector or query_text must be provided')
        
        return values


class VectorResult(BaseModel):
    id: str = Field(..., description="ID do documento")
    score: float = Field(..., description="Score de similaridade")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    text: Optional[str] = None


class VectorQueryResponse(BaseResponse):
    results: List[VectorResult] = Field(..., description="Resultados da busca")


class VectorDocument(BaseModel):
    id: str = Field(..., description="ID único do documento")
    vector: List[float] = Field(..., description="Embedding do documento")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    text: Optional[str] = None


class VectorUpsertRequest(BaseRequest):
    collection: str = Field(..., description="Nome da coleção")
    documents: List[VectorDocument] = Field(..., min_items=1)


class VectorUpsertResponse(BaseResponse):
    upserted_count: int = Field(..., ge=0)
    ids: List[str] = Field(..., description="IDs dos documentos inseridos")


# Graph Models
class GraphDeployRequest(BaseRequest):
    name: str = Field(..., description="Nome do grafo")
    definition: str = Field(..., description="Definição YAML/JSON do grafo")
    format: str = Field(default="yaml", regex="^(yaml|json)$")


class GraphDeployResponse(BaseResponse):
    graph_id: str = Field(..., description="ID único do grafo")
    version: str = Field(..., description="Versão do grafo")
    success: bool = Field(..., description="Se o deploy foi bem-sucedido")
    error: Optional[str] = None


class GraphExecuteRequest(BaseRequest):
    graph_id: str = Field(..., description="ID do grafo")
    inputs: Dict[str, Any] = Field(..., description="Inputs para execução")
    stream: bool = Field(default=False)


class GraphStep(BaseModel):
    node_id: str = Field(..., description="ID do nó")
    status: GraphStatus = Field(..., description="Status da execução")
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    started_at: datetime = Field(..., description="Timestamp de início")
    completed_at: Optional[datetime] = None


class GraphExecuteResponse(BaseResponse):
    outputs: Dict[str, Any] = Field(..., description="Outputs finais")
    steps: List[GraphStep] = Field(..., description="Histórico de execução")


# Metrics Models
class MetricsRequest(BaseRequest):
    project_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metric_types: List[str] = Field(default_factory=list)


class Metric(BaseModel):
    name: str = Field(..., description="Nome da métrica")
    type: str = Field(..., description="Tipo da métrica")
    value: float = Field(..., description="Valor da métrica")
    labels: Dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(..., description="Timestamp da métrica")


class MetricsResponse(BaseResponse):
    metrics: List[Metric] = Field(..., description="Lista de métricas")


# Health Check Models
class HealthRequest(BaseRequest):
    pass


class HealthResponse(BaseResponse):
    status: HealthStatus = Field(..., description="Status geral do sistema")
    checks: Dict[str, str] = Field(..., description="Status dos componentes")


# Error Models
class ErrorDetail(BaseModel):
    code: str = Field(..., description="Código do erro")
    message: str = Field(..., description="Mensagem do erro")
    field: Optional[str] = None


class ErrorResponse(BaseResponse):
    error: str = Field(..., description="Tipo do erro")
    message: str = Field(..., description="Mensagem de erro")
    details: Optional[List[ErrorDetail]] = None
