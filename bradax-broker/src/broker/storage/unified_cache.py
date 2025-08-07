"""
Sistema de Cache Unificado - Bradax Storage Optimization
Consolidação dos 3 caches redundantes em um único sistema coordenado.
"""
import threading
import time
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, TypeVar, Generic
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from collections import defaultdict
from enum import Enum

from ..logging_config import get_logger
from ..constants import HubStorageConstants

logger = get_logger("bradax.storage.unified_cache")

# Type variables para generics
T = TypeVar('T')


class CacheType(Enum):
    """Tipos de dados no cache unificado."""
    PROJECT = "project"
    TELEMETRY = "telemetry" 
    GUARDRAIL = "guardrail"
    SYSTEM_INFO = "system_info"


class DataEvent(Enum):
    """Eventos de dados para observabilidade."""
    CREATED = "created"
    UPDATED = "updated" 
    DELETED = "deleted"
    ACCESSED = "accessed"


@dataclass
class CacheEntry(Generic[T]):
    """Entrada genérica no cache unificado."""
    key: str
    data: T
    cache_type: CacheType
    created_at: float
    last_accessed: float
    access_count: int = 0
    is_dirty: bool = False  # Precisa ser salvo
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def mark_accessed(self):
        """Marca entrada como acessada."""
        self.last_accessed = time.time()
        self.access_count += 1
    
    def mark_dirty(self):
        """Marca entrada como modificada."""
        self.is_dirty = True


@dataclass 
class UnifiedTelemetryData:
    """Dados de telemetria unificados (merge de TelemetryEvent + TelemetryData)."""
    # Campos obrigatórios
    event_id: str
    timestamp: str
    project_id: str
    event_type: str  # "request_start", "request_complete", "error", etc.
    
    # Request context
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    
    # Performance metrics
    status_code: Optional[int] = None
    duration_ms: Optional[float] = None
    request_size: Optional[int] = None
    response_size: Optional[int] = None
    
    # LLM specific
    model_used: Optional[str] = None
    tokens_consumed: Optional[int] = None
    cost_usd: Optional[float] = None
    
    # Error handling
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    # Client info
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    sdk_version: Optional[str] = None
    
    # Security
    guardrail_triggered: Optional[str] = None
    
    # System context (referência, não duplicação)
    system_info_ref: Optional[str] = None  # ID para SystemInfo compartilhado
    
    # Extensibilidade
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        # Auto-gerar request_id se não fornecido
        if not self.request_id and self.event_id:
            self.request_id = self.event_id
    
    def to_legacy_telemetry_data(self) -> Dict[str, Any]:
        """Converte para formato legado TelemetryData."""
        return {
            "telemetry_id": self.event_id,
            "project_id": self.project_id,
            "timestamp": self.timestamp,
            "request_id": self.request_id or self.event_id,
            "endpoint": self.endpoint or "",
            "method": self.method or "",
            "status_code": self.status_code or 200,
            "response_time_ms": self.duration_ms or 0.0,
            "model_used": self.model_used or "",
            "tokens_used": self.tokens_consumed or 0,
            "client_ip": self.ip_address or "",
            "user_agent": self.user_agent or "",
            "error_message": self.error_message or "",
            "user_id": self.user_id or "",
            "system_info": {}  # Não duplicar, usar referência
        }


class CacheObserver(ABC):
    """Interface para observar mudanças no cache."""
    
    @abstractmethod
    def on_data_event(self, cache_type: CacheType, event: DataEvent, 
                     key: str, data: Any) -> None:
        """Chamado quando dados são modificados."""
        pass


class AutoSaveObserver(CacheObserver):
    """Observer que dispara auto-save baseado em políticas."""
    
    def __init__(self, cache_manager: 'UnifiedCacheManager'):
        self.cache_manager = cache_manager
        self.dirty_counts = defaultdict(int)
        self.last_save_times = defaultdict(float)
        
        # Políticas de auto-save por tipo - CORRIGIDO: Save imediato para telemetria/guardrails
        self.save_policies = {
            CacheType.PROJECT: {"dirty_threshold": 1, "time_threshold": 10},
            CacheType.TELEMETRY: {"dirty_threshold": 1, "time_threshold": 1},  # Imediato
            CacheType.GUARDRAIL: {"dirty_threshold": 1, "time_threshold": 1},  # Imediato  
            CacheType.SYSTEM_INFO: {"dirty_threshold": 1, "time_threshold": 300}
        }
    
    def on_data_event(self, cache_type: CacheType, event: DataEvent, 
                     key: str, data: Any) -> None:
        """Dispara auto-save se necessário."""
        if event in [DataEvent.CREATED, DataEvent.UPDATED, DataEvent.DELETED]:
            self.dirty_counts[cache_type] += 1
            
            policy = self.save_policies.get(cache_type, {"dirty_threshold": 5, "time_threshold": 60})
            current_time = time.time()
            last_save = self.last_save_times.get(cache_type, 0)
            
            should_save = (
                self.dirty_counts[cache_type] >= policy["dirty_threshold"] or
                (current_time - last_save) >= policy["time_threshold"]
            )
            
            if should_save:
                try:
                    self.cache_manager.flush_cache_type(cache_type)
                    self.dirty_counts[cache_type] = 0
                    self.last_save_times[cache_type] = current_time
                    logger.debug(f"Auto-save disparado para {cache_type.value}")
                except Exception as e:
                    logger.error(f"Erro no auto-save {cache_type.value}: {e}")


class UnifiedCacheManager:
    """
    Gerenciador de cache unificado thread-safe.
    
    Consolida JsonStorage, TelemetryCollector e TelemetryRepository
    em um único sistema coordenado.
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Inicializa cache manager unificado.
        
        Args:
            data_dir: Diretório de dados (usa padrão se None)
        """
        # Configuração de diretórios
        if data_dir is None:
            data_dir = HubStorageConstants.DATA_DIR()
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise RuntimeError(f"Diretório de dados não encontrado: {self.data_dir}")
        
        # Cache unificado thread-safe
        self._cache: Dict[str, CacheEntry] = {}
        self._cache_by_type: Dict[CacheType, Dict[str, CacheEntry]] = {
            cache_type: {} for cache_type in CacheType
        }
        self._lock = threading.RLock()  # Reentrant lock
        
        # Observers para eventos
        self._observers: List[CacheObserver] = []
        
        # Auto-save observer
        self.auto_save_observer = AutoSaveObserver(self)
        self.add_observer(self.auto_save_observer)
        
        # Métricas
        self._metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "total_entries": 0,
            "memory_usage_mb": 0.0,
            "last_cleanup": time.time()
        }
        
        # System info compartilhado (single source of truth)
        self._shared_system_info: Optional[Dict[str, Any]] = None
        self._system_info_id = "system_001"
        
        logger.info(f"UnifiedCacheManager inicializado - dir: {self.data_dir}")
    
    def add_observer(self, observer: CacheObserver):
        """Adiciona observer para eventos de dados."""
        self._observers.append(observer)
    
    def _notify_observers(self, cache_type: CacheType, event: DataEvent, 
                         key: str, data: Any):
        """Notifica observers sobre eventos."""
        for observer in self._observers:
            try:
                observer.on_data_event(cache_type, event, key, data)
            except Exception as e:
                logger.error(f"Erro no observer {type(observer).__name__}: {e}")
    
    def _generate_key(self, cache_type: CacheType, identifier: str) -> str:
        """Gera chave única para cache."""
        return f"{cache_type.value}:{identifier}"
    
    def put(self, cache_type: CacheType, identifier: str, data: Any, 
           metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Adiciona/atualiza entrada no cache.
        
        Args:
            cache_type: Tipo de dados
            identifier: Identificador único
            data: Dados a serem cached
            metadata: Metadados opcionais
            
        Returns:
            Chave da entrada no cache
        """
        key = self._generate_key(cache_type, identifier)
        current_time = time.time()
        
        with self._lock:
            existing = self._cache.get(key)
            is_update = existing is not None
            
            entry = CacheEntry(
                key=key,
                data=data,
                cache_type=cache_type,
                created_at=existing.created_at if existing else current_time,
                last_accessed=current_time,
                access_count=existing.access_count if existing else 0,
                is_dirty=True,
                metadata=metadata or {}
            )
            
            # Atualizar caches
            self._cache[key] = entry
            self._cache_by_type[cache_type][identifier] = entry
            
            # Notificar observers
            event = DataEvent.UPDATED if is_update else DataEvent.CREATED
            self._notify_observers(cache_type, event, key, data)
            
            # Atualizar métricas
            if not is_update:
                self._metrics["total_entries"] += 1
            
            logger.debug(f"Cache {event.value}: {key}")
            return key
    
    def get(self, cache_type: CacheType, identifier: str) -> Optional[Any]:
        """
        Obtém entrada do cache.
        
        Args:
            cache_type: Tipo de dados
            identifier: Identificador único
            
        Returns:
            Dados ou None se não encontrado
        """
        key = self._generate_key(cache_type, identifier)
        
        with self._lock:
            entry = self._cache.get(key)
            
            if entry:
                entry.mark_accessed()
                self._metrics["cache_hits"] += 1
                self._notify_observers(cache_type, DataEvent.ACCESSED, key, entry.data)
                return entry.data
            else:
                self._metrics["cache_misses"] += 1
                return None
    
    def get_all(self, cache_type: CacheType) -> List[Any]:
        """Retorna todas as entradas de um tipo."""
        with self._lock:
            entries = self._cache_by_type[cache_type].values()
            return [entry.data for entry in entries]
    
    def delete(self, cache_type: CacheType, identifier: str) -> bool:
        """
        Remove entrada do cache.
        
        Args:
            cache_type: Tipo de dados
            identifier: Identificador único
            
        Returns:
            True se removido, False se não encontrado
        """
        key = self._generate_key(cache_type, identifier)
        
        with self._lock:
            entry = self._cache.pop(key, None)
            if entry:
                self._cache_by_type[cache_type].pop(identifier, None)
                self._notify_observers(cache_type, DataEvent.DELETED, key, entry.data)
                self._metrics["total_entries"] -= 1
                logger.debug(f"Cache deleted: {key}")
                return True
            return False
    
    def flush_cache_type(self, cache_type: CacheType):
        """Força persistência de um tipo de cache."""
        with self._lock:
            entries = [e for e in self._cache_by_type[cache_type].values() if e.is_dirty]
            
            if not entries:
                return
            
            file_path = self._get_file_path(cache_type)
            data_list = []
            
            for entry in entries:
                if cache_type == CacheType.TELEMETRY:
                    # Converter UnifiedTelemetryData para formato legado se necessário
                    if isinstance(entry.data, UnifiedTelemetryData):
                        data_list.append(asdict(entry.data))
                    else:
                        data_list.append(entry.data)
                else:
                    if hasattr(entry.data, '__dict__'):
                        data_list.append(asdict(entry.data) if hasattr(entry.data, '__dataclass_fields__') else entry.data.__dict__)
                    else:
                        data_list.append(entry.data)
                
                entry.is_dirty = False
            
            # Salvar arquivo
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data_list, f, indent=2, ensure_ascii=False, default=str)
                logger.debug(f"Cache flushed: {cache_type.value} ({len(data_list)} entries)")
            except Exception as e:
                logger.error(f"Erro ao salvar cache {cache_type.value}: {e}")
                # Re-marcar como dirty
                for entry in entries:
                    entry.is_dirty = True
                raise
    
    def _get_file_path(self, cache_type: CacheType) -> Path:
        """Retorna caminho do arquivo para tipo de cache."""
        file_mapping = {
            CacheType.PROJECT: "projects.json",
            CacheType.TELEMETRY: "telemetry_unified.json",  # Novo arquivo consolidado
            CacheType.GUARDRAIL: "guardrail_events.json",
            CacheType.SYSTEM_INFO: "system_info.json"
        }
        return self.data_dir / file_mapping[cache_type]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do cache."""
        with self._lock:
            # Calcular uso de memória aproximado
            import sys
            total_size = sum(sys.getsizeof(entry) for entry in self._cache.values())
            self._metrics["memory_usage_mb"] = total_size / (1024 * 1024)
            
            return self._metrics.copy()
    
    def set_shared_system_info(self, system_info: Dict[str, Any]):
        """Define informações do sistema compartilhadas (single source of truth)."""
        with self._lock:
            self._shared_system_info = system_info
            self.put(CacheType.SYSTEM_INFO, self._system_info_id, system_info)
    
    def get_shared_system_info(self) -> Optional[Dict[str, Any]]:
        """Retorna informações do sistema compartilhadas."""
        if self._shared_system_info is None:
            self._shared_system_info = self.get(CacheType.SYSTEM_INFO, self._system_info_id)
        return self._shared_system_info


# Instância global (singleton)
_unified_cache: Optional[UnifiedCacheManager] = None

def get_unified_cache() -> UnifiedCacheManager:
    """Retorna instância global do cache unificado."""
    global _unified_cache
    if _unified_cache is None:
        _unified_cache = UnifiedCacheManager()
    return _unified_cache
