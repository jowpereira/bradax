"""
Logger Estruturado Avançado - Sistema Bradax
Wrapper otimizado que facilita o uso do logging estruturado com schema padronizado.
Implementação completa com context manager para operações e métricas de performance.
"""
import logging
import time
from typing import Dict, Any, Optional, Union, List
from contextlib import contextmanager
from .log_schema import (
    BradaxLogSchema, LogSeverity, OperationType, 
    create_structured_log, log_sampler
)
from .logging_config import get_logger


class StructuredLogger:
    """
    Logger estruturado otimizado com contexto operacional e sampling.
    
    Implementa logging estruturado com:
    - Context manager para medição de performance
    - Sampling inteligente baseado em operação
    - Métodos especializados para diferentes tipos de operação
    - Contexto persistente para correlação de logs
    """
    
    def __init__(self, 
                 service_name: str,
                 logger_name: str,
                 default_request_id: Optional[str] = None,
                 default_user_id: Optional[str] = None,
                 default_project_id: Optional[str] = None):
        """
        Inicializa logger estruturado.
        
        Args:
            service_name: Nome do serviço (bradax.broker, bradax.sdk)
            logger_name: Nome específico do logger
            default_request_id: Request ID padrão para correlação
            default_user_id: User ID padrão
            default_project_id: Project ID padrão
        """
        self.service_name = service_name
        self.logger = get_logger(logger_name)
        self.default_request_id = default_request_id
        self.default_user_id = default_user_id
        self.default_project_id = default_project_id
        
        # Cache para evitar múltiplas verificações de sampling para a mesma operação
        self._sampling_cache: Dict[str, bool] = {}
    
    def clear_sampling_cache(self) -> None:
        """Limpa cache de sampling (útil para testes ou mudanças de configuração)."""
        self._sampling_cache.clear()
    
    def _should_log(self, level: LogSeverity, operation: Optional[OperationType] = None) -> bool:
        """
        Determina se deve fazer log baseado em sampling otimizado com cache.
        """
        if operation is None:
            return True  # Sempre logar se não especificar operação
            
        # Usar cache para evitar recálculo frequente
        cache_key = f"{operation.value}_{level.value}"
        if cache_key in self._sampling_cache:
            return self._sampling_cache[cache_key]
            
        should_log = log_sampler.should_log(operation, level)
        self._sampling_cache[cache_key] = should_log
        return should_log
    
    def _log_structured(self,
                       level: LogSeverity,
                       message: str,
                       operation: Optional[OperationType] = None,
                       request_id: Optional[str] = None,
                       user_id: Optional[str] = None,
                       project_id: Optional[str] = None,
                       duration_ms: Optional[float] = None,
                       error_code: Optional[str] = None,
                       error_details: Optional[Dict[str, Any]] = None,
                       performance_metrics: Optional[Dict[str, Any]] = None,
                       custom_data: Optional[Dict[str, Any]] = None,
                       **kwargs) -> None:
        """Método interno para logging estruturado."""
        
        # Verificar sampling
        if not self._should_log(level, operation):
            return
        
        # Usar valores padrão se não especificados
        final_request_id = request_id or self.default_request_id
        final_user_id = user_id or self.default_user_id
        final_project_id = project_id or self.default_project_id
        
        # Criar log estruturado
        log_entry = create_structured_log(
            level=level,
            service=self.service_name,
            logger=self.logger.name,
            message=message,
            request_id=final_request_id,
            operation=operation,
            error_code=error_code,
            error_details=error_details,
            performance_metrics=performance_metrics,
            custom_data=custom_data,
            **kwargs
        )
        
        # Enriquecer com contexto
        log_entry.enrich_with_context(
            request_id=final_request_id,
            user_id=final_user_id,
            project_id=final_project_id,
            operation=operation,
            performance_data=performance_metrics
        )
        
        if duration_ms is not None:
            log_entry.operation_duration_ms = duration_ms
        
        # Enviar para logger nativo
        log_level = getattr(logging, level.value)
        self.logger.log(
            log_level, 
            message, 
            extra={"structured_data": log_entry.to_json()}
        )
    
    def debug(self, message: str, **kwargs):
        """Log de debug."""
        self._log_structured(LogSeverity.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log de informação."""
        self._log_structured(LogSeverity.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log de warning."""
        self._log_structured(LogSeverity.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log de erro."""
        self._log_structured(LogSeverity.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log crítico."""
        self._log_structured(LogSeverity.CRITICAL, message, **kwargs)
    
    # Métodos específicos por operação
    def log_llm_request(self, 
                       message: str,
                       model: str,
                       prompt_length: int,
                       max_tokens: int,
                       temperature: float,
                       duration_ms: Optional[float] = None,
                       **kwargs):
        """Log específico para requests LLM."""
        performance_metrics = {
            "model": model,
            "prompt_length": prompt_length,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        if duration_ms:
            performance_metrics["duration_ms"] = duration_ms
        
        self._log_structured(
            LogSeverity.INFO,
            message,
            operation=OperationType.LLM_REQUEST,
            performance_metrics=performance_metrics,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def log_guardrail_check(self,
                           message: str,
                           rule_id: str,
                           action: str,
                           confidence: float,
                           duration_ms: Optional[float] = None,
                           **kwargs):
        """Log específico para verificações de guardrail."""
        performance_metrics = {
            "rule_id": rule_id,
            "action": action,
            "confidence": confidence
        }
        if duration_ms:
            performance_metrics["duration_ms"] = duration_ms
        
        self._log_structured(
            LogSeverity.INFO,
            message,
            operation=OperationType.GUARDRAIL_CHECK,
            performance_metrics=performance_metrics,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def log_error_with_context(self,
                              message: str,
                              error_code: str,
                              exception: Optional[Exception] = None,
                              **kwargs):
        """Log específico para erros com contexto rico."""
        error_details = {
            "error_code": error_code
        }
        if exception:
            error_details.update({
                "exception_type": type(exception).__name__,
                "exception_message": str(exception)
            })
        
        self._log_structured(
            LogSeverity.ERROR,
            message,
            operation=OperationType.ERROR_HANDLING,
            error_code=error_code,
            error_details=error_details,
            **kwargs
        )
    
    @contextmanager
    def operation_timer(self, 
                       operation: OperationType,
                       message: str,
                       **kwargs):
        """Context manager para medir duração de operações."""
        start_time = time.perf_counter()
        try:
            yield
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_structured(
                LogSeverity.INFO,
                f"{message} - concluída",
                operation=operation,
                duration_ms=duration_ms,
                **kwargs
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.log_error_with_context(
                f"{message} - falhou",
                error_code="OPERATION_FAILED",
                exception=e,
                operation=operation,
                duration_ms=duration_ms,
                **kwargs
            )
            raise
    
    def set_context(self,
                   request_id: Optional[str] = None,
                   user_id: Optional[str] = None,
                   project_id: Optional[str] = None):
        """Atualiza contexto padrão do logger."""
        if request_id is not None:
            self.default_request_id = request_id
        if user_id is not None:
            self.default_user_id = user_id
        if project_id is not None:
            self.default_project_id = project_id
    
    def bulk_log(self, entries: List[Dict[str, Any]], **common_context):
        """
        Log múltiplas entradas de uma vez com contexto comum.
        Útil para logging em lote com melhor performance.
        
        Args:
            entries: Lista de dicionários com dados de log
            **common_context: Contexto comum aplicado a todas as entradas
        """
        for entry in entries:
            # Mesclar contexto comum com dados específicos da entrada
            merged_kwargs = {**common_context, **entry}
            level = merged_kwargs.pop('level', LogSeverity.INFO)
            message = merged_kwargs.pop('message', 'Bulk log entry')
            
            self._log_structured(level, message, **merged_kwargs)


# Factory functions otimizadas para facilitar uso
def get_structured_logger(service_name: str, 
                         logger_name: str,
                         **context) -> StructuredLogger:
    """
    Cria logger estruturado com contexto e configuração otimizada.
    
    Args:
        service_name: Nome do serviço (ex: bradax.broker, bradax.sdk)
        logger_name: Nome específico do logger
        **context: Contexto padrão (request_id, user_id, project_id, etc.)
        
    Returns:
        StructuredLogger: Instância configurada do logger estruturado
    """
    logger = StructuredLogger(
        service_name, 
        logger_name,
        default_request_id=context.get('request_id'),
        default_user_id=context.get('user_id'),
        default_project_id=context.get('project_id')
    )
    
    # Log de inicialização para auditoria
    logger.info(f"StructuredLogger inicializado para {service_name}", 
               logger_name=logger_name, 
               operation=OperationType.SYSTEM_STARTUP)
    
    return logger

def get_broker_logger(logger_name: str, **context) -> StructuredLogger:
    """Cria logger estruturado otimizado para broker."""
    return get_structured_logger("bradax.broker", logger_name, **context)

def get_sdk_logger(logger_name: str, **context) -> StructuredLogger:
    """Cria logger estruturado otimizado para SDK."""
    return get_structured_logger("bradax.sdk", logger_name, **context)
