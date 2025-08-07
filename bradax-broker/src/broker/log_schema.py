"""
Schema Padrão para Logs Estruturados - Sistema Bradax
Define estrutura obrigatória e opcional para todos os logs.
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import json


class LogSeverity(Enum):
    """Severidades padronizadas para logs."""
    TRACE = "TRACE"
    DEBUG = "DEBUG"  
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    FATAL = "FATAL"


class OperationType(Enum):
    """Tipos de operação para contexto."""
    LLM_REQUEST = "llm_request"
    GUARDRAIL_CHECK = "guardrail_check"
    TELEMETRY_COLLECTION = "telemetry_collection"
    DATA_PERSISTENCE = "data_persistence"
    AUTH_VALIDATION = "auth_validation"
    API_CALL = "api_call"
    SYSTEM_HEALTH = "system_health"
    SYSTEM_STARTUP = "system_startup"
    ERROR_HANDLING = "error_handling"


@dataclass
class BradaxLogSchema:
    """Schema obrigatório para todos os logs estruturados."""
    
    # CAMPOS OBRIGATÓRIOS
    timestamp: str  # ISO 8601 UTC
    level: str      # LogSeverity.value
    service: str    # bradax.sdk, bradax.broker, etc
    logger: str     # Nome completo do logger
    message: str    # Mensagem principal
    
    # CAMPOS OPCIONAIS - CONTEXTO OPERACIONAL
    request_id: Optional[str] = None        # Correlação entre requests
    user_id: Optional[str] = None           # Identificação do usuário
    project_id: Optional[str] = None        # Projeto/tenant
    operation: Optional[str] = None         # Tipo de operação
    operation_duration_ms: Optional[float] = None  # Duração da operação
    
    # CAMPOS OPCIONAIS - CONTEXTO TÉCNICO
    module: Optional[str] = None            # Módulo Python
    function: Optional[str] = None          # Função que gerou o log
    line: Optional[int] = None              # Linha do código
    thread_id: Optional[str] = None         # ID da thread
    
    # CAMPOS OPCIONAIS - DADOS ESPECÍFICOS
    error_code: Optional[str] = None        # Código de erro padronizado
    error_details: Optional[Dict[str, Any]] = None  # Detalhes do erro
    performance_metrics: Optional[Dict[str, Any]] = None  # Métricas de performance
    custom_data: Optional[Dict[str, Any]] = None  # Dados específicos da operação
    
    # CAMPOS OPCIONAIS - METADATA
    environment: Optional[str] = None       # dev, staging, prod
    version: Optional[str] = None           # Versão do componente
    trace_id: Optional[str] = None          # Distributed tracing
    span_id: Optional[str] = None           # Span ID para tracing
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário removendo valores None."""
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None}
    
    def to_json(self) -> str:
        """Converte para JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BradaxLogSchema':
        """Cria instância a partir de dicionário."""
        # Filtrar apenas campos válidos
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
    
    def validate_required_fields(self) -> List[str]:
        """Valida se todos os campos obrigatórios estão preenchidos."""
        missing = []
        if not self.timestamp:
            missing.append("timestamp")
        if not self.level:
            missing.append("level")
        if not self.service:
            missing.append("service")
        if not self.logger:
            missing.append("logger")
        if not self.message:
            missing.append("message")
        return missing
    
    def enrich_with_context(self, 
                           request_id: Optional[str] = None,
                           user_id: Optional[str] = None,
                           project_id: Optional[str] = None,
                           operation: Optional[OperationType] = None,
                           performance_data: Optional[Dict[str, Any]] = None) -> 'BradaxLogSchema':
        """Enriquece log com contexto operacional."""
        if request_id:
            self.request_id = request_id
        if user_id:
            self.user_id = user_id
        if project_id:
            self.project_id = project_id
        if operation:
            self.operation = operation.value
        if performance_data:
            self.performance_metrics = performance_data
        return self


class LogSampler:
    """Sistema de sampling para operações de alto volume."""
    
    def __init__(self):
        self.sample_rates = {
            OperationType.LLM_REQUEST: 1.0,      # 100% - crítico
            OperationType.GUARDRAIL_CHECK: 1.0,   # 100% - crítico  
            OperationType.TELEMETRY_COLLECTION: 0.1,  # 10% - alto volume
            OperationType.DATA_PERSISTENCE: 0.5,      # 50% - médio volume
            OperationType.AUTH_VALIDATION: 1.0,       # 100% - segurança
            OperationType.API_CALL: 0.8,             # 80% - importante
            OperationType.SYSTEM_HEALTH: 0.2,        # 20% - baixo valor
            OperationType.ERROR_HANDLING: 1.0,       # 100% - crítico
        }
        self.counters = {op: 0 for op in OperationType}
    
    def should_log(self, operation: OperationType, severity: LogSeverity) -> bool:
        """Determina se deve fazer log baseado em sampling."""
        # Sempre logar erros e críticos
        if severity in [LogSeverity.ERROR, LogSeverity.CRITICAL, LogSeverity.FATAL]:
            return True
        
        # Aplicar sampling baseado na operação
        self.counters[operation] += 1
        sample_rate = self.sample_rates.get(operation, 1.0)
        
        # Sampling simples baseado em contador
        return (self.counters[operation] % int(1.0 / sample_rate)) == 0


# Instância global de sampler
log_sampler = LogSampler()


def create_structured_log(
    level: LogSeverity,
    service: str,
    logger: str, 
    message: str,
    request_id: Optional[str] = None,
    operation: Optional[OperationType] = None,
    **kwargs
) -> BradaxLogSchema:
    """
    Função utilitária para criar logs estruturados padronizados.
    
    Args:
        level: Severidade do log
        service: Nome do serviço
        logger: Nome do logger
        message: Mensagem principal
        request_id: ID de correlação
        operation: Tipo de operação
        **kwargs: Dados adicionais
        
    Returns:
        Schema de log estruturado
    """
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    log_entry = BradaxLogSchema(
        timestamp=timestamp,
        level=level.value,
        service=service,
        logger=logger,
        message=message,
        request_id=request_id,
        operation=operation.value if operation else None
    )
    
    # Adicionar dados extras
    if 'error_code' in kwargs:
        log_entry.error_code = kwargs['error_code']
    if 'error_details' in kwargs:
        log_entry.error_details = kwargs['error_details']
    if 'performance_metrics' in kwargs:
        log_entry.performance_metrics = kwargs['performance_metrics']
    if 'custom_data' in kwargs:
        log_entry.custom_data = kwargs['custom_data']
    if 'environment' in kwargs:
        log_entry.environment = kwargs['environment']
    if 'version' in kwargs:
        log_entry.version = kwargs['version']
    
    return log_entry
