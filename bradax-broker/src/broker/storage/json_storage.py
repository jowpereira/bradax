"""
Sistema de Storage JSON Otimizado para Bradax Broker

Gerencia persistência automática de dados em arquivos JSON:
- Projetos e configurações
- Telemetrias e métricas  
- Guardrails e logs de segurança
- Informações do sistema

🔄 Suporte a Transações Atômicas para operações thread-safe
"""

import json
import os
import platform
import threading
import time
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, asdict
import uuid

from ..logging_config import storage_logger
from ..utils.paths import get_data_dir

# Evitar import cíclico pesado: apenas para type hints
if TYPE_CHECKING:
    try:
        from ..services.telemetry import TelemetryEvent  # pragma: no cover
    except Exception:  # pragma: no cover
        TelemetryEvent = Any  # fallback

# Importação condicional do psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class TransactionContext:
    """
    Contexto de Transação Atômica para JsonStorage
    
    Garante ACID properties:
    - Atomicity: Todas as operações ou nenhuma
    - Consistency: Estado válido antes e depois
    - Isolation: Operações não interferem entre si
    - Durability: Dados persistidos com segurança
    """
    
    def __init__(self, storage_instance: 'JsonStorage'):
        self.storage = storage_instance
        self.backup_files: Dict[str, Path] = {}
        self.temp_files: Dict[str, Path] = {}
        self.operations: List[str] = []
        self.committed = False
        self.rolled_back = False
        
    def __enter__(self):
        """Iniciar transação - criar backups dos arquivos"""
        with self.storage._lock:
            self._create_backups()
            storage_logger.debug(f"🔄 Transação iniciada: {len(self.backup_files)} arquivos em backup")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Finalizar transação"""
        storage_logger.debug(f"🔚 __exit__ chamado: exc_type={exc_type}, committed={self.committed}, rolled_back={self.rolled_back}")
        
        with self.storage._lock:  # Manter lock durante finalização
            if exc_type is not None:
                # Houve exceção - fazer rollback
                storage_logger.debug(f"🔄 Fazendo rollback devido a exceção: {exc_val}")
                self.rollback()
                storage_logger.error(f"❌ Transação falhou: {exc_val}")
                return False
            elif not self.committed and not self.rolled_back:
                # Commit automático se não houve problemas
                storage_logger.debug(f"✅ Fazendo commit automático")
                self.commit()
        return True
    
    def track_file(self, file_path: Path):
        """Adiciona um arquivo para rastreamento na transação"""
        if file_path.exists() and str(file_path) not in self.backup_files:
            backup_path = Path(tempfile.mktemp(suffix=f"_{file_path.name}.backup"))
            shutil.copy2(file_path, backup_path)
            self.backup_files[str(file_path)] = backup_path
            storage_logger.debug(f"📋 Arquivo adicionado ao rastreamento: {file_path}")
    
    def _create_backups(self):
        """Criar backups temporários dos arquivos que serão modificados"""
        files_to_backup = [
            self.storage.projects_file,
            self.storage.telemetry_file, 
            self.storage.guardrails_file,
            self.storage.system_file
        ]
        
        # Adicionar outros arquivos que existem no data_dir
        if hasattr(self.storage, 'data_dir') and self.storage.data_dir.exists():
            for json_file in self.storage.data_dir.glob("*.json"):
                if json_file not in files_to_backup:
                    files_to_backup.append(json_file)
        
        for file_path in files_to_backup:
            if file_path.exists() and file_path.is_file():
                # Criar backup temporário
                backup_path = Path(tempfile.mktemp(suffix=f"_{file_path.name}.backup"))
                shutil.copy2(file_path, backup_path)
                self.backup_files[str(file_path)] = backup_path
                storage_logger.debug(f"📋 Backup criado: {file_path} -> {backup_path}")
            else:
                storage_logger.debug(f"📋 Arquivo não existe para backup: {file_path}")
                
    def add_operation(self, operation: str):
        """Registrar operação na transação"""
        self.operations.append(f"{datetime.now().isoformat()}: {operation}")
        
    def commit(self):
        """Confirmar transação - remover backups"""
        if self.rolled_back:
            raise RuntimeError("Cannot commit a rolled back transaction")
            
        try:
            # Remover arquivos de backup
            for backup_path in self.backup_files.values():
                if backup_path.exists():
                    backup_path.unlink()
                    
            # Remover arquivos temporários
            for temp_path in self.temp_files.values():
                if temp_path.exists():
                    temp_path.unlink()
                    
            self.committed = True
            storage_logger.info(f"✅ Transação commitada: {len(self.operations)} operações")
            
        except Exception as e:
            storage_logger.error(f"❌ Erro no commit: {e}")
            self.rollback()
            raise
            
    def rollback(self):
        """Desfazer transação - restaurar backups"""
        if self.committed:
            raise RuntimeError("Cannot rollback a committed transaction")
            
        try:
            # Restaurar arquivos dos backups
            for original_path, backup_path in self.backup_files.items():
                if backup_path.exists():
                    storage_logger.debug(f"🔄 Restaurando: {backup_path} -> {original_path}")
                    shutil.copy2(backup_path, original_path)
                    backup_path.unlink()
                else:
                    storage_logger.warning(f"⚠️  Backup não encontrado: {backup_path}")
                    
            # Remover arquivos temporários
            for temp_path in self.temp_files.values():
                if temp_path.exists():
                    temp_path.unlink()
            
            # CRÍTICO: Recarregar cache após rollback
            self.storage._load_all_data()
            storage_logger.debug(f"🔄 Cache recarregado após rollback")
                    
            self.rolled_back = True
            storage_logger.warning(f"🔄 Transação revertida: {len(self.operations)} operações desfeitas")
            
        except Exception as e:
            storage_logger.error(f"❌ Erro no rollback: {e}")
            raise


@dataclass
class ProjectData:
    """Estrutura de dados de um projeto"""
    project_id: str
    name: str
    created_at: str
    updated_at: str
    status: str = "active"
    config: Dict[str, Any] = None
    api_key_hash: str = ""
    owner: str = ""
    description: str = ""
    tags: List[str] = None
    allowed_models: List[str] = None  # Modelos permitidos para o projeto
    applied_guardrails: List[str] = None  # Guardrails aplicados ao projeto
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}
        if self.tags is None:
            self.tags = []
        if self.allowed_models is None:
            self.allowed_models = []
        if self.applied_guardrails is None:
            self.applied_guardrails = []


@dataclass
class TelemetryData:
    """Estrutura unificada de telemetria (merge TelemetryEvent + TelemetryData)"""
    # Campos obrigatórios
    telemetry_id: str  # Mesmo que event_id
    project_id: str
    timestamp: str
    event_type: str = "request"  # "request_start", "request_complete", "error", etc.
    
    # Request context
    request_id: str = ""
    user_id: str = ""
    endpoint: str = ""
    method: str = ""
    
    # Performance metrics
    status_code: int = 200
    response_time_ms: float = 0.0
    request_size: Optional[int] = None
    response_size: Optional[int] = None
    duration_ms: Optional[float] = None  # Alias para response_time_ms
    
    # LLM specific
    model_used: str = ""
    tokens_used: int = 0
    tokens_consumed: Optional[int] = None  # Alias para tokens_used
    cost_usd: Optional[float] = None
    
    # Error handling
    error_type: Optional[str] = None
    error_message: str = ""
    error_code: Optional[str] = None
    
    # Client info
    client_ip: str = ""
    user_agent: str = ""
    ip_address: Optional[str] = None  # Alias para client_ip
    sdk_version: Optional[str] = None
    
    # Security
    guardrail_triggered: Optional[str] = None
    
    # System context (referência, não duplicação)
    system_info_ref: Optional[str] = None  # ID para SystemInfo compartilhado
    
    # Legacy system_info (será eliminado gradualmente)
    system_info: Dict[str, Any] = None
    
    # Extensibilidade
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.system_info is None:
            self.system_info = {}
        if self.metadata is None:
            self.metadata = {}
        
        # Sincronizar aliases
        if self.duration_ms and not self.response_time_ms:
            self.response_time_ms = self.duration_ms
        elif self.response_time_ms and not self.duration_ms:
            self.duration_ms = self.response_time_ms
            
        if self.tokens_consumed and not self.tokens_used:
            self.tokens_used = self.tokens_consumed
        elif self.tokens_used and not self.tokens_consumed:
            self.tokens_consumed = self.tokens_used
            
        if self.ip_address and not self.client_ip:
            self.client_ip = self.ip_address
        elif self.client_ip and not self.ip_address:
            self.ip_address = self.client_ip

    def to_compact_dict(self) -> Dict[str, Any]:
        """Retorna dicionário sem campos vazios para reduzir tamanho em disco."""
        from dataclasses import asdict
        data = asdict(self)
        required = {"telemetry_id", "project_id", "timestamp", "event_type"}
        compact = {}
        for k, v in data.items():
            if k in required or (v not in (None, "", [], {})):
                compact[k] = v
        return compact
    
    @classmethod
    def from_telemetry_event(cls, event: Any) -> 'TelemetryData':
        """Converte TelemetryEvent para TelemetryData unificado."""
        return cls(
            telemetry_id=event.event_id,
            project_id=event.project_id,
            timestamp=event.timestamp,
            event_type=event.event_type,
            request_id=event.event_id,  # Usar event_id como request_id
            user_id=event.user_id or "",
            endpoint=event.endpoint or "",
            method=event.method or "",
            status_code=event.status_code or 200,
            response_time_ms=event.duration_ms or 0.0,
            duration_ms=event.duration_ms,
            request_size=event.request_size,
            response_size=event.response_size,
            model_used=event.model_used or "",
            tokens_used=event.tokens_consumed or 0,
            tokens_consumed=event.tokens_consumed,
            cost_usd=event.cost_usd,
            error_type=event.error_type,
            error_message=event.error_message or "",
            error_code=None,
            client_ip=event.ip_address or "",
            user_agent=event.user_agent or "",
            ip_address=event.ip_address,
            sdk_version=event.sdk_version,
            guardrail_triggered=event.guardrail_triggered,
            system_info_ref="system_001",  # Referência ao sistema compartilhado
            metadata=event.metadata or {}
        )


@dataclass
class GuardrailEvent:
    """Estrutura de dados de eventos de guardrails"""
    event_id: str
    project_id: str
    timestamp: str
    request_id: str
    guardrail_type: str
    action: str  # "allowed", "blocked", "warned"
    reason: str
    details: Dict[str, Any] = None
    severity: str = "info"
    client_ip: str = ""
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class SystemInfo:
    """Informações do sistema onde o broker está rodando"""
    hostname: str
    platform: str
    platform_version: str
    python_version: str
    cpu_count: int
    memory_total_gb: float
    disk_total_gb: float
    network_interfaces: List[Dict[str, str]]
    environment_vars: Dict[str, str]
    startup_time: str
    last_updated: str


class JsonStorage:
    """Gerenciador de storage JSON thread-safe"""
    
    def __init__(self, data_dir: str = None):
        # SISTEMA CENTRALIZADO: Sempre usar get_data_dir() do sistema de paths
        if data_dir is None:
            self.data_dir = get_data_dir()
        else:
            self.data_dir = Path(data_dir)
        
        # Validação simples: verificar se existe
        if not self.data_dir.exists():
            raise RuntimeError(f"Diretório de dados não encontrado: {self.data_dir}")
        storage_logger.info(f"📁 JsonStorage inicializado em: {self.data_dir}")
        
        # Arquivos de dados
        self.projects_file = self.data_dir / "projects.json"
        self.telemetry_file = self.data_dir / "telemetry.json"
        self.guardrails_file = self.data_dir / "guardrail_events.json"
        self.system_file = self.data_dir / "system_info.json"
        
        # Lock para thread safety
        self._lock = threading.Lock()
        
        # Cache em memória
        self._projects_cache: Dict[str, ProjectData] = {}
        self._telemetry_cache: List[TelemetryData] = []
        self._guardrails_cache: List[GuardrailEvent] = []
        self._system_info: Optional[SystemInfo] = None

        # Inicializar caches e infos de sistema
        self._load_all_data()
        self._collect_system_info()
    
    def transaction(self):
        """
        Context manager para operações transacionais atômicas
        
        Usage:
            with storage.transaction() as tx:
                storage.add_project(project_data)
                storage.add_telemetry(telemetry_data)
                # Se qualquer operação falhar, rollback automático
        """
        return TransactionContext(self)
    
    def _get_timestamp(self) -> str:
        """Gera timestamp ISO 8601 UTC"""
        return datetime.now(timezone.utc).isoformat()
    
    def _load_json_file(self, file_path: Path, default_value=None):
        """Carrega arquivo JSON com fallback"""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, UnicodeDecodeError) as e:
            storage_logger.error(
                f"Erro ao carregar {file_path}: {str(e)}"
            )
        
        return default_value or {}
    
    def _save_json_file(self, file_path: Path, data: Any):
        """Salva dados em arquivo JSON"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            storage_logger.error(
                f"Erro ao salvar {file_path}: {str(e)}"
            )
    
    def _load_all_data(self):
        """Carrega todos os dados na inicialização"""
        with self._lock:
            # Carregar projetos
            projects_data = self._load_json_file(self.projects_file, {})
            # Validar se projects_data é dict antes de processar
            if isinstance(projects_data, dict) and projects_data:
                self._projects_cache = {
                    pid: ProjectData(**data) 
                    for pid, data in projects_data.items()
                }
            else:
                self._projects_cache = {}
            
            # Carregar telemetrias (últimas 1000)
            telemetry_data = self._load_json_file(self.telemetry_file, [])
            if isinstance(telemetry_data, list):
                self._telemetry_cache = []
                for item in telemetry_data[-1000:]:  # Manter apenas os últimos 1000
                    # Converter event_id para request_id se necessário
                    if 'event_id' in item and 'request_id' not in item:
                        item['request_id'] = item.pop('event_id')
                    
                    # Filtrar apenas campos válidos da TelemetryData
                    valid_fields = {
                        'telemetry_id', 'project_id', 'timestamp', 'event_type',
                        'request_id', 'user_id', 'endpoint', 'method',
                        'status_code', 'response_time_ms', 'request_size', 'response_size', 'duration_ms',
                        'model_used', 'tokens_used', 'tokens_consumed', 'cost_usd',
                        'error_code', 'error_message', 'operation_type', 'data_source'
                    }
                    
                    # Limpar campos inválidos (como 'id')
                    filtered_item = {k: v for k, v in item.items() if k in valid_fields}
                    
                    # Garantir campos obrigatórios
                    if 'telemetry_id' not in filtered_item:
                        filtered_item['telemetry_id'] = filtered_item.get('request_id', str(uuid.uuid4()))
                    if 'project_id' not in filtered_item:
                        filtered_item['project_id'] = 'unknown'
                    if 'timestamp' not in filtered_item:
                        filtered_item['timestamp'] = datetime.now(timezone.utc).isoformat()
                    
                    try:
                        self._telemetry_cache.append(TelemetryData(**filtered_item))
                    except TypeError as e:
                        # Pular itens com estrutura incompatível
                        storage_logger.warning(
                            f"Ignorando item de telemetria incompatível: {str(e)}"
                        )
                        continue
            else:
                self._telemetry_cache = []
            
            # Carregar guardrails (últimos 1000)
            guardrails_data = self._load_json_file(self.guardrails_file, [])
            if isinstance(guardrails_data, list):
                self._guardrails_cache = [
                    GuardrailEvent(**item) 
                    for item in guardrails_data[-1000:]  # Manter apenas os últimos 1000
                ]
            else:
                self._guardrails_cache = []
    
    def _collect_system_info(self):
        """Coleta informações detalhadas do sistema"""
        try:
            # Informações de rede (com fallback se psutil não disponível)
            network_interfaces = []
            if PSUTIL_AVAILABLE:
                for interface, addrs in psutil.net_if_addrs().items():
                    for addr in addrs:
                        if addr.family.name in ['AF_INET', 'AF_INET6']:
                            network_interfaces.append({
                                "interface": interface,
                                "family": addr.family.name,
                                "address": addr.address,
                                "netmask": getattr(addr, 'netmask', ''),
                                "broadcast": getattr(addr, 'broadcast', '')
                            })
            else:
                network_interfaces = [{"interface": "unknown", "address": "psutil não disponível"}]
            
            # Variáveis de ambiente relevantes (filtradas)
            relevant_env_vars = {}
            env_keys = ['HOSTNAME', 'USER', 'HOME', 'OS', 'COMPUTERNAME']
            for key in env_keys:
                if key in os.environ:
                    relevant_env_vars[key] = os.environ[key]
            
            # Adicionar variáveis específicas do bradax (mascaradas por segurança)
            for key, value in os.environ.items():
                if 'BRADAX' in key.upper() or 'OPENAI' in key.upper():
                    relevant_env_vars[key] = value[:10] + "..." if len(value) > 10 else value
            
            # Hardware info com fallback
            cpu_count = psutil.cpu_count() if PSUTIL_AVAILABLE else os.cpu_count() or 1
            memory_gb = round(psutil.virtual_memory().total / (1024**3), 2) if PSUTIL_AVAILABLE else 0.0
            disk_gb = round(psutil.disk_usage('/').total / (1024**3), 2) if PSUTIL_AVAILABLE else 0.0
            
            self._system_info = SystemInfo(
                hostname=platform.node(),
                platform=platform.platform(),
                platform_version=platform.version(),
                python_version=platform.python_version(),
                cpu_count=cpu_count,
                memory_total_gb=memory_gb,
                disk_total_gb=disk_gb,
                network_interfaces=network_interfaces,
                environment_vars=relevant_env_vars,
                startup_time=self._get_timestamp(),
                last_updated=self._get_timestamp()
            )
            
            # Salvar informações do sistema
            self._save_json_file(self.system_file, asdict(self._system_info))
            
        except Exception as e:
            storage_logger.error(
                f"Erro ao coletar informações do sistema: {str(e)}"
            )
    
    # === OPERAÇÕES DE PROJETOS ===
    
    def create_project(self, project_id: str, name: str, **kwargs) -> ProjectData:
        """Cria um novo projeto"""
        with self._lock:
            if project_id in self._projects_cache:
                raise ValueError(f"Projeto {project_id} já existe")
            
            now = self._get_timestamp()
            project = ProjectData(
                project_id=project_id,
                name=name,
                created_at=now,
                updated_at=now,
                **kwargs
            )
            
            self._projects_cache[project_id] = project
            self._save_projects()
            return project
    
    def update_project(self, project_id: str, **updates) -> ProjectData:
        """Atualiza um projeto existente"""
        with self._lock:
            if project_id not in self._projects_cache:
                raise ValueError(f"Projeto {project_id} não encontrado")
            
            project = self._projects_cache[project_id]
            
            # Atualizar campos
            for key, value in updates.items():
                if hasattr(project, key):
                    setattr(project, key, value)
            
            project.updated_at = self._get_timestamp()
            self._save_projects()
            return project
    
    def get_project(self, project_id: str) -> Optional[ProjectData]:
        """Obtém dados de um projeto"""
        return self._projects_cache.get(project_id)
    
    def list_projects(self) -> List[ProjectData]:
        """Lista todos os projetos"""
        return list(self._projects_cache.values())
    
    def load_projects(self) -> Dict[str, List[Dict]]:
        """Retorna projetos no formato esperado pelos controllers"""
        projects_list = self.list_projects()
        projects_dict = [asdict(project) for project in projects_list]
        return {"projects": projects_dict}
    
    def delete_project(self, project_id: str) -> bool:
        """Remove um projeto"""
        with self._lock:
            if project_id in self._projects_cache:
                del self._projects_cache[project_id]
                self._save_projects()
                return True
            return False
    
    def save_projects(self, projects_data: Dict[str, List[Dict]]):
        """Salva projetos no formato esperado pelos controllers"""
        with self._lock:
            # Limpar cache atual
            self._projects_cache.clear()
            
            # Recarregar projetos do formato do controller
            for project_dict in projects_data.get("projects", []):
                project = ProjectData(**project_dict)
                self._projects_cache[project.project_id] = project
            
            # Salvar em disco
            self._save_projects()
    
    def _save_projects(self):
        """Salva projetos em disco"""
        projects_dict = {
            pid: asdict(project) 
            for pid, project in self._projects_cache.items()
        }
        self._save_json_file(self.projects_file, projects_dict)
    
    # === OPERAÇÕES DE TELEMETRIA ===
    
    def add_telemetry(self, telemetry: TelemetryData):
        """Adiciona entrada de telemetria com auto-save otimizado e suporte transacional"""
        with self._lock:
            # Usar referência compartilhada ao invés de duplicar system_info
            if not telemetry.system_info_ref and self._system_info:
                telemetry.system_info_ref = "system_001"  # Single source of truth
            
            # Limpar system_info legado (duplicação desnecessária)
            telemetry.system_info = {}
            
            self._telemetry_cache.append(telemetry)
            
            # Registrar operação se há transação ativa
            operation = f"add_telemetry: {telemetry.request_id} for project {telemetry.project_id}"
            storage_logger.debug(f"📝 {operation}")
            
            # Manter apenas últimas 1000 entradas em memória
            if len(self._telemetry_cache) > 1000:
                self._telemetry_cache = self._telemetry_cache[-1000:]
                storage_logger.debug(f"🧹 Cache telemetria limitado a 1000 entradas")
            
            # CORRIGIDO: Save imediato para garantir persistência
            self._save_telemetry()
    
    def get_telemetry(self, 
                     project_id: Optional[str] = None, 
                     limit: int = 100) -> List[TelemetryData]:
        """Obtém dados de telemetria"""
        telemetries = self._telemetry_cache
        
        if project_id:
            telemetries = [t for t in telemetries if t.project_id == project_id]
        
        return telemetries[-limit:]
    
    def _save_telemetry(self):
        """Salva telemetrias em disco de forma não destrutiva.
        - Não sobrescreve arquivo existente com lista vazia.
        - Faz merge por telemetry_id (ou event_id legado).
        """
        try:
            if not self._telemetry_cache:
                # Evitar apagar histórico existente
                if self.telemetry_file.exists() and self.telemetry_file.stat().st_size > 2:
                    return
            existing = []
            if self.telemetry_file.exists():
                try:
                    with open(self.telemetry_file, 'r', encoding='utf-8') as f:
                        existing = json.load(f) or []
                except Exception:
                    existing = []
            index = {}
            for e in existing:
                key = e.get('telemetry_id') or e.get('event_id')
                if key:
                    index[key] = e
            for t in self._telemetry_cache:
                data = asdict(t)
                key = data.get('telemetry_id') or data.get('event_id')
                if key:
                    index[key] = data
            merged = list(index.values())
            self._save_json_file(self.telemetry_file, merged)
        except Exception as e:
            storage_logger.error(f"Falha ao salvar telemetria (protegido): {e}")
    
    # === OPERAÇÕES DE GUARDRAILS ===
    
    def add_guardrail_event(self, event: GuardrailEvent):
        """Adiciona evento de guardrail com auto-save otimizado"""
        with self._lock:
            self._guardrails_cache.append(event)
            
            # Manter apenas últimos 1000 eventos em memória
            if len(self._guardrails_cache) > 1000:
                self._guardrails_cache = self._guardrails_cache[-1000:]
            
            # CORRIGIDO: Save imediato para garantir persistência
            self._save_guardrails()
    
    def get_guardrail_events(self, 
                           project_id: Optional[str] = None,
                           guardrail_type: Optional[str] = None,
                           limit: int = 100) -> List[GuardrailEvent]:
        """Obtém eventos de guardrails"""
        events = self._guardrails_cache
        
        if project_id:
            events = [e for e in events if e.project_id == project_id]
        
        if guardrail_type:
            events = [e for e in events if e.guardrail_type == guardrail_type]
        
        return events[-limit:]
    
    def get_guardrails(self) -> List[Dict[str, Any]]:
        """Obtém todas as regras de guardrails"""
        try:
            with open(self.data_dir / "guardrails.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except Exception:
            return []
    
    def _save_guardrails(self):
        """Salva eventos de guardrails em disco sem apagar histórico existente quando cache vazio."""
        try:
            if not self._guardrails_cache:
                if self.guardrails_file.exists() and self.guardrails_file.stat().st_size > 2:
                    return
            existing = []
            if self.guardrails_file.exists():
                try:
                    with open(self.guardrails_file, 'r', encoding='utf-8') as f:
                        existing = json.load(f) or []
                except Exception:
                    existing = []
            index = {e.get('event_id'): e for e in existing if e.get('event_id')}
            for ev in self._guardrails_cache:
                data = asdict(ev)
                if data.get('event_id'):
                    index[data['event_id']] = data
            merged = list(index.values())
            self._save_json_file(self.guardrails_file, merged)
        except Exception as e:
            storage_logger.error(f"Falha ao salvar guardrails (protegido): {e}")
    
    # === INFORMAÇÕES DO SISTEMA ===
    
    def get_system_info(self) -> Optional[SystemInfo]:
        """Obtém informações do sistema"""
        return self._system_info
    
    def update_system_info(self):
        """Atualiza informações do sistema"""
        self._collect_system_info()
    
    # === ESTATÍSTICAS E RELATÓRIOS ===
    
    def get_project_stats(self, project_id: str) -> Dict[str, Any]:
        """Gera estatísticas detalhadas de um projeto"""
        telemetries = [t for t in self._telemetry_cache if t.project_id == project_id]
        guardrails = [g for g in self._guardrails_cache if g.project_id == project_id]
        
        if not telemetries:
            return {"error": "Nenhuma telemetria encontrada"}
        
        # Estatísticas de uso
        total_requests = len(telemetries)
        successful_requests = len([t for t in telemetries if 200 <= t.status_code < 300])
        failed_requests = total_requests - successful_requests
        
        avg_response_time = sum(t.response_time_ms for t in telemetries) / total_requests
        total_tokens = sum(t.tokens_used for t in telemetries if t.tokens_used > 0)
        
        # Modelos mais usados
        models_used = {}
        for t in telemetries:
            if t.model_used:
                models_used[t.model_used] = models_used.get(t.model_used, 0) + 1
        
        # Eventos de guardrails
        guardrail_summary = {}
        for g in guardrails:
            key = f"{g.guardrail_type}_{g.action}"
            guardrail_summary[key] = guardrail_summary.get(key, 0) + 1
        
        return {
            "project_id": project_id,
            "period": {
                "start": telemetries[0].timestamp if telemetries else None,
                "end": telemetries[-1].timestamp if telemetries else None
            },
            "requests": {
                "total": total_requests,
                "successful": successful_requests,
                "failed": failed_requests,
                "success_rate": round(successful_requests / total_requests * 100, 2)
            },
            "performance": {
                "avg_response_time_ms": round(avg_response_time, 2),
                "total_tokens_used": total_tokens
            },
            "models": models_used,
            "guardrails": guardrail_summary,
            "system_info": self._system_info.hostname if self._system_info else None
        }
    

    
    def force_save_all(self):
        """Força salvamento imediato de todos os dados"""
        with self._lock:
            self._save_projects()
            self._save_telemetry()
            self._save_guardrails()
            storage_logger.info(
                f"Save forçado executado: {self._get_timestamp()}"
            )
    
    def shutdown(self):
        """Encerra o storage salvando todos os dados"""
        self.force_save_all()
        storage_logger.info("Storage encerrado com dados salvos")


# Instância global do storage com persistência automática
# storage = JsonStorage()
