"""
JSON Repository Implementations - Bradax Broker

Implementações concretas do padrão Repository para dados JSON.
"""

import json
import asyncio
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
import uuid

from .interfaces import IProjectRepository, ITelemetryRepository, IGuardrailRepository, RepositoryResult
from .json_storage import ProjectData, TelemetryData, GuardrailEvent


class BaseJsonRepository:
    """Classe base para repositories JSON com operações comuns"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.lock = threading.RLock()
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Garante que o arquivo JSON existe"""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write_json([])
    
    def _read_json(self) -> List[Dict[str, Any]]:
        """Lê dados do arquivo JSON com tratamento de erro"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _write_json(self, data: List[Dict[str, Any]]) -> bool:
        """Escreve dados no arquivo JSON com tratamento de erro"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Erro ao escrever arquivo {self.file_path}: {e}")
            return False
    
    async def _safe_operation(self, operation):
        """Executa operação de forma thread-safe"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, operation)


class ProjectRepository(BaseJsonRepository, IProjectRepository):
    """Repository para gerenciamento de projetos"""
    
    def __init__(self, file_path: str = "data/projects.json"):
        super().__init__(file_path)
    
    async def create(self, project: ProjectData) -> RepositoryResult:
        """Cria novo projeto"""
        def _create():
            with self.lock:
                projects = self._read_json()
                
                # Verificar se já existe
                if any(p.get('project_id') == project.project_id for p in projects):
                    return RepositoryResult.error_result(
                        f"Projeto '{project.project_id}' já existe"
                    )
                
                # Adicionar timestamps
                now = datetime.now(timezone.utc).isoformat()
                project.created_at = now
                project.updated_at = now
                
                # Adicionar à lista
                projects.append(project.__dict__)
                
                if self._write_json(projects):
                    return RepositoryResult.success_result(
                        project, f"Projeto '{project.project_id}' criado com sucesso"
                    )
                else:
                    return RepositoryResult.error_result("Erro ao salvar projeto")
        
        return await self._safe_operation(_create)
    
    async def get_by_id(self, project_id: str) -> Optional[ProjectData]:
        """Busca projeto por ID"""
        def _get():
            with self.lock:
                projects = self._read_json()
                for project_dict in projects:
                    if project_dict.get('project_id') == project_id:
                        return ProjectData(**project_dict)
                return None
        
        return await self._safe_operation(_get)
    
    async def get_all(self) -> List[ProjectData]:
        """Retorna todos os projetos"""
        def _get_all():
            with self.lock:
                projects = self._read_json()
                return [ProjectData(**p) for p in projects]
        
        return await self._safe_operation(_get_all)
    
    async def update(self, project_id: str, updates: Dict[str, Any]) -> RepositoryResult:
        """Atualiza projeto existente"""
        def _update():
            with self.lock:
                projects = self._read_json()
                
                for i, project in enumerate(projects):
                    if project.get('project_id') == project_id:
                        # Aplicar atualizações
                        project.update(updates)
                        project['updated_at'] = datetime.now(timezone.utc).isoformat()
                        
                        if self._write_json(projects):
                            return RepositoryResult.success_result(
                                ProjectData(**project), 
                                f"Projeto '{project_id}' atualizado com sucesso"
                            )
                        else:
                            return RepositoryResult.error_result("Erro ao salvar atualizações")
                
                return RepositoryResult.error_result(f"Projeto '{project_id}' não encontrado")
        
        return await self._safe_operation(_update)
    
    async def delete(self, project_id: str) -> bool:
        """Remove projeto"""
        def _delete():
            with self.lock:
                projects = self._read_json()
                original_length = len(projects)
                projects = [p for p in projects if p.get('project_id') != project_id]
                
                if len(projects) < original_length:
                    return self._write_json(projects)
                return False
        
        return await self._safe_operation(_delete)
    
    async def exists(self, project_id: str) -> bool:
        """Verifica se projeto existe"""
        project = await self.get_by_id(project_id)
        return project is not None
    
    async def get_by_owner(self, owner: str) -> List[ProjectData]:
        """Busca projetos por proprietário"""
        def _get_by_owner():
            with self.lock:
                projects = self._read_json()
                return [
                    ProjectData(**p) for p in projects 
                    if p.get('owner') == owner
                ]
        
        return await self._safe_operation(_get_by_owner)
    
    async def get_by_status(self, status: str) -> List[ProjectData]:
        """Busca projetos por status"""
        def _get_by_status():
            with self.lock:
                projects = self._read_json()
                return [
                    ProjectData(**p) for p in projects 
                    if p.get('status') == status
                ]
        
        return await self._safe_operation(_get_by_status)
    
    async def search_by_tags(self, tags: List[str]) -> List[ProjectData]:
        """Busca projetos por tags"""
        def _search_by_tags():
            with self.lock:
                projects = self._read_json()
                results = []
                for project_dict in projects:
                    project_tags = project_dict.get('tags', [])
                    if any(tag in project_tags for tag in tags):
                        results.append(ProjectData(**project_dict))
                return results
        
        return await self._safe_operation(_search_by_tags)


class TelemetryRepository(BaseJsonRepository, ITelemetryRepository):
    """Repository para telemetria"""
    
    def __init__(self, file_path: str = "data/telemetry.json"):
        super().__init__(file_path)
    
    async def create(self, telemetry: TelemetryData) -> RepositoryResult:
        """Registra nova entrada de telemetria"""
        def _create():
            with self.lock:
                entries = self._read_json()
                
                # Garantir ID único
                if not telemetry.telemetry_id:
                    telemetry.telemetry_id = str(uuid.uuid4())
                
                # Garantir timestamp
                if not telemetry.timestamp:
                    telemetry.timestamp = datetime.now(timezone.utc).isoformat()
                
                entries.append(telemetry.__dict__)
                
                if self._write_json(entries):
                    return RepositoryResult.success_result(
                        telemetry, "Telemetria registrada com sucesso"
                    )
                else:
                    return RepositoryResult.error_result("Erro ao salvar telemetria")
        
        return await self._safe_operation(_create)
    
    async def get_by_id(self, telemetry_id: str) -> Optional[TelemetryData]:
        """Busca entrada de telemetria por ID"""
        def _get():
            with self.lock:
                entries = self._read_json()
                for entry in entries:
                    if entry.get('telemetry_id') == telemetry_id:
                        return TelemetryData(**entry)
                return None
        
        return await self._safe_operation(_get)
    
    async def get_all(self) -> List[TelemetryData]:
        """Retorna todas as entradas de telemetria"""
        def _get_all():
            with self.lock:
                entries = self._read_json()
                return [TelemetryData(**e) for e in entries]
        
        return await self._safe_operation(_get_all)
    
    async def update(self, telemetry_id: str, updates: Dict[str, Any]) -> RepositoryResult:
        """Atualiza entrada de telemetria (uso limitado)"""
        def _update():
            with self.lock:
                entries = self._read_json()
                
                for i, entry in enumerate(entries):
                    if entry.get('telemetry_id') == telemetry_id:
                        entry.update(updates)
                        
                        if self._write_json(entries):
                            return RepositoryResult.success_result(
                                TelemetryData(**entry), 
                                "Telemetria atualizada com sucesso"
                            )
                        else:
                            return RepositoryResult.error_result("Erro ao salvar atualizações")
                
                return RepositoryResult.error_result("Entrada de telemetria não encontrada")
        
        return await self._safe_operation(_update)
    
    async def delete(self, telemetry_id: str) -> bool:
        """Remove entrada de telemetria"""
        def _delete():
            with self.lock:
                entries = self._read_json()
                original_length = len(entries)
                entries = [e for e in entries if e.get('telemetry_id') != telemetry_id]
                
                if len(entries) < original_length:
                    return self._write_json(entries)
                return False
        
        return await self._safe_operation(_delete)
    
    async def exists(self, telemetry_id: str) -> bool:
        """Verifica se entrada existe"""
        entry = await self.get_by_id(telemetry_id)
        return entry is not None
    
    async def get_by_project(self, project_id: str, limit: int = 100) -> List[TelemetryData]:
        """Busca telemetria por projeto"""
        def _get_by_project():
            with self.lock:
                entries = self._read_json()
                project_entries = [
                    TelemetryData(**e) for e in entries 
                    if e.get('project_id') == project_id
                ]
                # Ordenar por timestamp (mais recente primeiro) e limitar
                project_entries.sort(key=lambda x: x.timestamp, reverse=True)
                return project_entries[:limit]
        
        return await self._safe_operation(_get_by_project)
    
    async def get_by_date_range(self, start_date: str, end_date: str) -> List[TelemetryData]:
        """Busca telemetria por período"""
        def _get_by_date_range():
            with self.lock:
                entries = self._read_json()
                return [
                    TelemetryData(**e) for e in entries 
                    if start_date <= e.get('timestamp', '') <= end_date
                ]
        
        return await self._safe_operation(_get_by_date_range)
    
    async def get_metrics_summary(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Retorna resumo de métricas"""
        def _get_metrics():
            with self.lock:
                entries = self._read_json()
                
                if project_id:
                    entries = [e for e in entries if e.get('project_id') == project_id]
                
                total_requests = len(entries)
                
                if total_requests == 0:
                    return {
                        "total_requests": 0,
                        "avg_response_time": 0,
                        "total_tokens": 0,
                        "error_rate": 0
                    }
                
                total_response_time = sum(e.get('response_time_ms', 0) for e in entries)
                total_tokens = sum(e.get('tokens_used', 0) for e in entries)
                errors = len([e for e in entries if e.get('status_code', 200) >= 400])
                
                return {
                    "total_requests": total_requests,
                    "avg_response_time": total_response_time / total_requests,
                    "total_tokens": total_tokens,
                    "error_rate": (errors / total_requests) * 100
                }
        
        return await self._safe_operation(_get_metrics)


class GuardrailRepository(BaseJsonRepository, IGuardrailRepository):
    """Repository para eventos de guardrails"""
    
    def __init__(self, file_path: str = "data/guardrails.json"):
        super().__init__(file_path)
    
    async def create(self, event: GuardrailEvent) -> RepositoryResult:
        """Registra novo evento de guardrail"""
        def _create():
            with self.lock:
                events = self._read_json()
                
                # Garantir ID único
                if not event.event_id:
                    event.event_id = str(uuid.uuid4())
                
                # Garantir timestamp
                if not event.timestamp:
                    event.timestamp = datetime.now(timezone.utc).isoformat()
                
                events.append(event.__dict__)
                
                if self._write_json(events):
                    return RepositoryResult.success_result(
                        event, "Evento de guardrail registrado com sucesso"
                    )
                else:
                    return RepositoryResult.error_result("Erro ao salvar evento")
        
        return await self._safe_operation(_create)
    
    async def get_by_id(self, event_id: str) -> Optional[GuardrailEvent]:
        """Busca evento por ID"""
        def _get():
            with self.lock:
                events = self._read_json()
                for event in events:
                    if event.get('event_id') == event_id:
                        return GuardrailEvent(**event)
                return None
        
        return await self._safe_operation(_get)
    
    async def get_all(self) -> List[GuardrailEvent]:
        """Retorna todos os eventos"""
        def _get_all():
            with self.lock:
                events = self._read_json()
                return [GuardrailEvent(**e) for e in events]
        
        return await self._safe_operation(_get_all)
    
    async def update(self, event_id: str, updates: Dict[str, Any]) -> RepositoryResult:
        """Atualiza evento (uso limitado)"""
        def _update():
            with self.lock:
                events = self._read_json()
                
                for i, event in enumerate(events):
                    if event.get('event_id') == event_id:
                        event.update(updates)
                        
                        if self._write_json(events):
                            return RepositoryResult.success_result(
                                GuardrailEvent(**event), 
                                "Evento atualizado com sucesso"
                            )
                        else:
                            return RepositoryResult.error_result("Erro ao salvar atualizações")
                
                return RepositoryResult.error_result("Evento não encontrado")
        
        return await self._safe_operation(_update)
    
    async def delete(self, event_id: str) -> bool:
        """Remove evento"""
        def _delete():
            with self.lock:
                events = self._read_json()
                original_length = len(events)
                events = [e for e in events if e.get('event_id') != event_id]
                
                if len(events) < original_length:
                    return self._write_json(events)
                return False
        
        return await self._safe_operation(_delete)
    
    async def exists(self, event_id: str) -> bool:
        """Verifica se evento existe"""
        event = await self.get_by_id(event_id)
        return event is not None
    
    async def get_by_project(self, project_id: str, limit: int = 100) -> List[GuardrailEvent]:
        """Busca eventos por projeto"""
        def _get_by_project():
            with self.lock:
                events = self._read_json()
                project_events = [
                    GuardrailEvent(**e) for e in events 
                    if e.get('project_id') == project_id
                ]
                # Ordenar por timestamp (mais recente primeiro) e limitar
                project_events.sort(key=lambda x: x.timestamp, reverse=True)
                return project_events[:limit]
        
        return await self._safe_operation(_get_by_project)
    
    async def get_by_action(self, action: str) -> List[GuardrailEvent]:
        """Busca eventos por ação"""
        def _get_by_action():
            with self.lock:
                events = self._read_json()
                return [
                    GuardrailEvent(**e) for e in events 
                    if e.get('action') == action
                ]
        
        return await self._safe_operation(_get_by_action)
    
    async def get_blocked_events(self, project_id: Optional[str] = None) -> List[GuardrailEvent]:
        """Busca eventos bloqueados"""
        def _get_blocked():
            with self.lock:
                events = self._read_json()
                blocked_events = [
                    GuardrailEvent(**e) for e in events 
                    if e.get('action') == 'blocked'
                ]
                
                if project_id:
                    blocked_events = [
                        e for e in blocked_events 
                        if e.project_id == project_id
                    ]
                
                return blocked_events
        
        return await self._safe_operation(_get_blocked)
