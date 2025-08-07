"""
Sistema de Telemetria Centralizada - Bradax Hub

Coleta, processa e armazena telemetria de TODOS os projetos/requisições.
Não pode ser desabilitado pelo SDK - controle total do hub.
"""

import logging
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path

from ..constants import HubStorageConstants, get_hub_environment
from ..exceptions import DataAccessException, ConfigurationException

logger = logging.getLogger(__name__)


@dataclass
class TelemetryEvent:
    """Evento de telemetria padronizado"""
    event_id: str
    timestamp: str
    project_id: str
    user_id: Optional[str]
    event_type: str  # request, response, error, auth, guardrail_block, etc.
    endpoint: Optional[str]
    method: Optional[str]
    request_size: Optional[int]
    response_size: Optional[int]
    duration_ms: Optional[float]
    status_code: Optional[int]
    model_used: Optional[str]
    tokens_consumed: Optional[int]
    cost_usd: Optional[float]
    error_type: Optional[str]
    error_message: Optional[str]
    user_agent: Optional[str]
    ip_address: Optional[str]
    sdk_version: Optional[str]
    guardrail_triggered: Optional[str]
    metadata: Dict[str, Any]


@dataclass 
class ProjectMetrics:
    """Métricas agregadas por projeto"""
    project_id: str
    total_requests: int
    total_errors: int
    total_tokens: int
    total_cost_usd: float
    avg_response_time_ms: float
    last_activity: str
    guardrails_triggered: int
    models_used: List[str]
    error_rate: float


class TelemetryCollector:
    """
    Coletor centralizado de telemetria
    
    CARACTERÍSTICAS:
    - Não pode ser desabilitado pelo SDK
    - Coleta TUDO automaticamente
    - Armazena localmente e processa
    - Gera métricas por projeto
    - Auditoria completa
    """
    
    def __init__(self):
        self.environment = get_hub_environment()
        self.storage_path = Path(HubStorageConstants.DATA_DIR())
        self.telemetry_file = self.storage_path / HubStorageConstants.TELEMETRY_FILE
        
        # Garantir diretório existe
        self.storage_path.mkdir(exist_ok=True)
        
        # Cache em memória para performance
        self._events_cache: List[TelemetryEvent] = []
        self._cache_size_limit = 100
        
        logger.info(f"TelemetryCollector iniciado - ambiente: {self.environment.value}")
    
    def record_request_start(
        self,
        project_id: str,
        endpoint: str,
        method: str,
        user_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        sdk_version: Optional[str] = None,
        request_size: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Registra início de requisição
        
        Returns:
            str: ID do evento para correlação
        """
        event_id = str(uuid.uuid4())
        
        event = TelemetryEvent(
            event_id=event_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            project_id=project_id,
            user_id=user_id,
            event_type="request_start",
            endpoint=endpoint,
            method=method,
            request_size=request_size,
            response_size=None,
            duration_ms=None,
            status_code=None,
            model_used=None,
            tokens_consumed=None,
            cost_usd=None,
            error_type=None,
            error_message=None,
            user_agent=user_agent,
            ip_address=ip_address,
            sdk_version=sdk_version,
            guardrail_triggered=None,
            metadata=metadata or {}
        )
        
        self._add_event(event)
        logger.debug(f"Request iniciada: {project_id} -> {endpoint} ({event_id})")
        return event_id
    
    def record_request_complete(
        self,
        event_id: str,
        status_code: int,
        response_size: Optional[int] = None,
        duration_ms: Optional[float] = None,
        model_used: Optional[str] = None,
        tokens_consumed: Optional[int] = None,
        cost_usd: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Registra conclusão de requisição"""
        
        event = TelemetryEvent(
            event_id=f"{event_id}_complete",
            timestamp=datetime.now(timezone.utc).isoformat(),
            project_id="",  # Será preenchido via correlação
            user_id=None,
            event_type="request_complete",
            endpoint=None,
            method=None,
            request_size=None,
            response_size=response_size,
            duration_ms=duration_ms,
            status_code=status_code,
            model_used=model_used,
            tokens_consumed=tokens_consumed,
            cost_usd=cost_usd,
            error_type=None,
            error_message=None,
            user_agent=None,
            ip_address=None,
            sdk_version=None,
            guardrail_triggered=None,
            metadata=metadata or {}
        )
        
        self._add_event(event)
        logger.debug(f"Request concluída: {event_id} -> {status_code}")
    
    def record_error(
        self,
        project_id: str,
        error_type: str,
        error_message: str,
        endpoint: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Registra erro ocorrido"""
        
        event = TelemetryEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            project_id=project_id,
            user_id=None,
            event_type="error",
            endpoint=endpoint,
            method=None,
            request_size=None,
            response_size=None,
            duration_ms=None,
            status_code=None,
            model_used=None,
            tokens_consumed=None,
            cost_usd=None,
            error_type=error_type,
            error_message=error_message,
            user_agent=None,
            ip_address=None,
            sdk_version=None,
            guardrail_triggered=None,
            metadata=metadata or {}
        )
        
        self._add_event(event)
        logger.warning(f"Erro registrado: {project_id} -> {error_type}: {error_message}")
    
    def record_guardrail_trigger(
        self,
        project_id: str,
        guardrail_name: str,
        blocked_content: str,
        endpoint: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Registra ativação de guardrail (bloqueio)"""
        
        event = TelemetryEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            project_id=project_id,
            user_id=None,
            event_type="guardrail_triggered",
            endpoint=endpoint,
            method=None,
            request_size=None,
            response_size=None,
            duration_ms=None,
            status_code=403,  # Forbidden
            model_used=None,
            tokens_consumed=None,
            cost_usd=None,
            error_type="guardrail_block",
            error_message=f"Conteúdo bloqueado por {guardrail_name}",
            user_agent=None,
            ip_address=None,
            sdk_version=None,
            guardrail_triggered=guardrail_name,
            metadata={
                "blocked_content": blocked_content[:500],  # Limitar tamanho
                **(metadata or {})
            }
        )
        
        self._add_event(event)
        logger.warning(f"Guardrail ativado: {project_id} -> {guardrail_name}")
    
    def record_authentication(
        self,
        project_id: str,
        success: bool,
        method: str = "api_key",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Registra tentativa de autenticação"""
        
        event = TelemetryEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            project_id=project_id,
            user_id=None,
            event_type="authentication",
            endpoint="/auth",
            method=method,
            request_size=None,
            response_size=None,
            duration_ms=None,
            status_code=200 if success else 401,
            model_used=None,
            tokens_consumed=None,
            cost_usd=None,
            error_type=None if success else "auth_failed",
            error_message=None if success else "Falha na autenticação",
            user_agent=None,
            ip_address=None,
            sdk_version=None,
            guardrail_triggered=None,
            metadata={
                "auth_method": method,
                "success": success,
                **(metadata or {})
            }
        )
        
        self._add_event(event)
        logger.info(f"Auth registrada: {project_id} -> {'SUCCESS' if success else 'FAILED'}")
    
    def _add_event(self, event: TelemetryEvent) -> None:
        """Adiciona evento ao cache e persiste se necessário"""
        self._events_cache.append(event)
        
        # Flush cache se atingiu limite
        if len(self._events_cache) >= self._cache_size_limit:
            self._flush_cache()
    
    def _flush_cache(self) -> None:
        """Persiste cache de eventos em disco"""
        if not self._events_cache:
            return
        
        try:
            # Carregar eventos existentes
            existing_events = []
            if self.telemetry_file.exists():
                with open(self.telemetry_file, 'r', encoding='utf-8') as f:
                    existing_events = json.load(f)
            
            # Adicionar novos eventos
            for event in self._events_cache:
                existing_events.append(asdict(event))
            
            # Salvar tudo
            with open(self.telemetry_file, 'w', encoding='utf-8') as f:
                json.dump(existing_events, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Telemetria persistida: {len(self._events_cache)} eventos")
            self._events_cache.clear()
            
        except Exception as e:
            logger.error(f"Erro ao persistir telemetria: {e}")
            raise DataAccessException(
                "Falha ao salvar telemetria",
                details={"error": str(e), "file": str(self.telemetry_file)}
            )
    
    def get_project_metrics(self, project_id: str) -> ProjectMetrics:
        """Calcula métricas agregadas para um projeto"""
        self._flush_cache()  # Garantir dados atualizados
        
        try:
            events = []
            if self.telemetry_file.exists():
                with open(self.telemetry_file, 'r', encoding='utf-8') as f:
                    all_events = json.load(f)
                    events = [e for e in all_events if e.get('project_id') == project_id]
            
            if not events:
                return ProjectMetrics(
                    project_id=project_id,
                    total_requests=0,
                    total_errors=0,
                    total_tokens=0,
                    total_cost_usd=0.0,
                    avg_response_time_ms=0.0,
                    last_activity="never",
                    guardrails_triggered=0,
                    models_used=[],
                    error_rate=0.0
                )
            
            # Calcular métricas
            total_requests = len([e for e in events if e.get('event_type') == 'request_start'])
            total_errors = len([e for e in events if e.get('event_type') == 'error'])
            total_tokens = sum(e.get('tokens_consumed', 0) for e in events if e.get('tokens_consumed'))
            total_cost = sum(e.get('cost_usd', 0.0) for e in events if e.get('cost_usd'))
            
            response_times = [e.get('duration_ms', 0) for e in events if e.get('duration_ms')]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
            
            last_activity = max(e.get('timestamp', '') for e in events) if events else 'never'
            
            guardrails_triggered = len([e for e in events if e.get('event_type') == 'guardrail_triggered'])
            
            models_used = list(set(e.get('model_used') for e in events if e.get('model_used')))
            
            error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0.0
            
            return ProjectMetrics(
                project_id=project_id,
                total_requests=total_requests,
                total_errors=total_errors,
                total_tokens=total_tokens,
                total_cost_usd=total_cost,
                avg_response_time_ms=avg_response_time,
                last_activity=last_activity,
                guardrails_triggered=guardrails_triggered,
                models_used=models_used,
                error_rate=error_rate
            )
            
        except Exception as e:
            logger.error(f"Erro ao calcular métricas: {e}")
            raise DataAccessException(
                "Falha ao calcular métricas do projeto",
                details={"project_id": project_id, "error": str(e)}
            )
    
    def get_all_events(self, project_id: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """Retorna eventos de telemetria (para debug/auditoria)"""
        self._flush_cache()
        
        try:
            if not self.telemetry_file.exists():
                return []
            
            with open(self.telemetry_file, 'r', encoding='utf-8') as f:
                all_events = json.load(f)
            
            if project_id:
                events = [e for e in all_events if e.get('project_id') == project_id]
            else:
                events = all_events
            
            # Retornar os mais recentes primeiro
            events.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return events[:limit]
            
        except Exception as e:
            logger.error(f"Erro ao buscar eventos: {e}")
            return []
    
    def cleanup_old_events(self, days_to_keep: int = 30) -> int:
        """Remove eventos antigos para gerenciar tamanho do arquivo"""
        try:
            if not self.telemetry_file.exists():
                return 0
            
            cutoff_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_to_keep)
            cutoff_str = cutoff_date.isoformat()
            
            with open(self.telemetry_file, 'r', encoding='utf-8') as f:
                all_events = json.load(f)
            
            old_count = len(all_events)
            recent_events = [e for e in all_events if e.get('timestamp', '') >= cutoff_str]
            
            with open(self.telemetry_file, 'w', encoding='utf-8') as f:
                json.dump(recent_events, f, indent=2, ensure_ascii=False)
            
            removed_count = old_count - len(recent_events)
            logger.info(f"Limpeza telemetria: {removed_count} eventos removidos (>{days_to_keep} dias)")
            return removed_count
            
        except Exception as e:
            logger.error(f"Erro na limpeza de telemetria: {e}")
            return 0


# Singleton global
telemetry_collector = TelemetryCollector()


def get_telemetry_collector() -> TelemetryCollector:
    """Factory function para obter coletor de telemetria"""
    return telemetry_collector
