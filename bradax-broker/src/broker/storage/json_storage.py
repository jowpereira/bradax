"""
Sistema de Storage JSON Otimizado para Bradax Broker

Gerencia persistência automática de dados em arquivos JSON:
- Projetos e configurações
- Telemetrias e métricas  
- Guardrails e logs de segurança
- Informações do sistema
"""

import json
import os
import platform
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import uuid

# Importação condicional do psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


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
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}
        if self.tags is None:
            self.tags = []


@dataclass
class TelemetryData:
    """Estrutura de dados de telemetria"""
    telemetry_id: str
    project_id: str
    timestamp: str
    request_id: str
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    model_used: str = ""
    tokens_used: int = 0
    client_ip: str = ""
    user_agent: str = ""
    error_message: str = ""
    system_info: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.system_info is None:
            self.system_info = {}


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
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Arquivos de dados
        self.projects_file = self.data_dir / "projects.json"
        self.telemetry_file = self.data_dir / "telemetry.json"
        self.guardrails_file = self.data_dir / "guardrails.json"
        self.system_file = self.data_dir / "system_info.json"
        
        # Lock para thread safety
        self._lock = threading.Lock()
        
        # Cache em memória
        self._projects_cache: Dict[str, ProjectData] = {}
        self._telemetry_cache: List[TelemetryData] = []
        self._guardrails_cache: List[GuardrailEvent] = []
        self._system_info: Optional[SystemInfo] = None
        
        # Auto-save periódico
        self._auto_save_interval = 30  # segundos
        self._last_save = time.time()
        self._auto_save_enabled = True
        
        # Inicializar
        self._load_all_data()
        self._collect_system_info()
        self._start_auto_save_thread()
    
    def _get_timestamp(self) -> str:
        """Gera timestamp ISO 8601 UTC"""
        return datetime.now(timezone.utc).isoformat()
    
    def _load_json_file(self, file_path: Path, default_value=None):
        """Carrega arquivo JSON com fallback"""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Erro ao carregar {file_path}: {e}")
        
        return default_value or {}
    
    def _save_json_file(self, file_path: Path, data: Any):
        """Salva dados em arquivo JSON"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Erro ao salvar {file_path}: {e}")
    
    def _load_all_data(self):
        """Carrega todos os dados na inicialização"""
        with self._lock:
            # Carregar projetos
            projects_data = self._load_json_file(self.projects_file, {})
            self._projects_cache = {
                pid: ProjectData(**data) 
                for pid, data in projects_data.items()
            }
            
            # Carregar telemetrias (últimas 1000)
            telemetry_data = self._load_json_file(self.telemetry_file, [])
            if isinstance(telemetry_data, list):
                self._telemetry_cache = [
                    TelemetryData(**item) 
                    for item in telemetry_data[-1000:]  # Manter apenas os últimos 1000
                ]
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
            print(f"Erro ao coletar informações do sistema: {e}")
    
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
    
    def delete_project(self, project_id: str) -> bool:
        """Remove um projeto"""
        with self._lock:
            if project_id in self._projects_cache:
                del self._projects_cache[project_id]
                self._save_projects()
                return True
            return False
    
    def _save_projects(self):
        """Salva projetos em disco"""
        projects_dict = {
            pid: asdict(project) 
            for pid, project in self._projects_cache.items()
        }
        self._save_json_file(self.projects_file, projects_dict)
    
    # === OPERAÇÕES DE TELEMETRIA ===
    
    def add_telemetry(self, telemetry: TelemetryData):
        """Adiciona entrada de telemetria com auto-save otimizado"""
        with self._lock:
            # Adicionar informações do sistema atual
            if self._system_info:
                telemetry.system_info = {
                    "hostname": self._system_info.hostname,
                    "platform": self._system_info.platform,
                    "cpu_count": self._system_info.cpu_count,
                    "memory_gb": self._system_info.memory_total_gb
                }
            
            self._telemetry_cache.append(telemetry)
            
            # Manter apenas últimas 1000 entradas em memória
            if len(self._telemetry_cache) > 1000:
                self._telemetry_cache = self._telemetry_cache[-1000:]
            
            # Save otimizado: apenas se muitas entradas ou tempo decorrido
            if len(self._telemetry_cache) % 10 == 0 or time.time() - self._last_save > 60:
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
        """Salva telemetrias em disco"""
        telemetry_list = [asdict(t) for t in self._telemetry_cache]
        self._save_json_file(self.telemetry_file, telemetry_list)
    
    # === OPERAÇÕES DE GUARDRAILS ===
    
    def add_guardrail_event(self, event: GuardrailEvent):
        """Adiciona evento de guardrail com auto-save otimizado"""
        with self._lock:
            self._guardrails_cache.append(event)
            
            # Manter apenas últimos 1000 eventos em memória
            if len(self._guardrails_cache) > 1000:
                self._guardrails_cache = self._guardrails_cache[-1000:]
            
            # Save otimizado: apenas se muitos eventos ou tempo decorrido
            if len(self._guardrails_cache) % 5 == 0 or time.time() - self._last_save > 60:
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
    
    def _save_guardrails(self):
        """Salva eventos de guardrails em disco"""
        events_list = [asdict(e) for e in self._guardrails_cache]
        self._save_json_file(self.guardrails_file, events_list)
    
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
    
    def _start_auto_save_thread(self):
        """Inicia thread de auto-save periódico"""
        def auto_save_worker():
            while self._auto_save_enabled:
                try:
                    time.sleep(self._auto_save_interval)
                    self._periodic_save()
                except Exception as e:
                    print(f"Erro no auto-save: {e}")
        
        auto_save_thread = threading.Thread(target=auto_save_worker, daemon=True)
        auto_save_thread.start()
    
    def _periodic_save(self):
        """Salva dados periodicamente se houver mudanças"""
        if time.time() - self._last_save > self._auto_save_interval:
            with self._lock:
                self._save_projects()
                self._save_telemetry()
                self._save_guardrails()
                self._last_save = time.time()
                print(f"🔄 Auto-save executado em {self._get_timestamp()}")
    
    def force_save_all(self):
        """Força salvamento imediato de todos os dados"""
        with self._lock:
            self._save_projects()
            self._save_telemetry()
            self._save_guardrails()
            self._last_save = time.time()
            print(f"💾 Save forçado executado em {self._get_timestamp()}")
    
    def shutdown(self):
        """Encerra o storage salvando todos os dados"""
        self._auto_save_enabled = False
        self.force_save_all()
        print("🛑 Storage encerrado com dados salvos")


# Instância global do storage com persistência automática
# storage = JsonStorage()
