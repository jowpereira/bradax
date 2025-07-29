"""
Repository Pattern Interfaces - Bradax Broker

Define contratos para acesso a dados seguindo padrões corporativos.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Generic, TypeVar
from dataclasses import dataclass

# Type variables para generics
T = TypeVar('T')


class IRepository(ABC, Generic[T]):
    """Interface base para todos os repositories"""
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """Cria nova entidade"""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Busca entidade por ID"""
        pass
    
    @abstractmethod
    async def get_all(self) -> List[T]:
        """Retorna todas as entidades"""
        pass
    
    @abstractmethod
    async def update(self, entity_id: str, updates: Dict[str, Any]) -> Optional[T]:
        """Atualiza entidade existente"""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Remove entidade"""
        pass
    
    @abstractmethod
    async def exists(self, entity_id: str) -> bool:
        """Verifica se entidade existe"""
        pass


class IProjectRepository(IRepository):
    """Interface específica para repositório de projetos"""
    
    @abstractmethod
    async def get_by_owner(self, owner: str) -> List[Any]:
        """Busca projetos por proprietário"""
        pass
    
    @abstractmethod
    async def get_by_status(self, status: str) -> List[Any]:
        """Busca projetos por status"""
        pass
    
    @abstractmethod
    async def search_by_tags(self, tags: List[str]) -> List[Any]:
        """Busca projetos por tags"""
        pass


class ITelemetryRepository(IRepository):
    """Interface específica para repositório de telemetria"""
    
    @abstractmethod
    async def get_by_project(self, project_id: str, limit: int = 100) -> List[Any]:
        """Busca telemetria por projeto"""
        pass
    
    @abstractmethod
    async def get_by_date_range(self, start_date: str, end_date: str) -> List[Any]:
        """Busca telemetria por período"""
        pass
    
    @abstractmethod
    async def get_metrics_summary(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Retorna resumo de métricas"""
        pass


class IGuardrailRepository(IRepository):
    """Interface específica para repositório de guardrails"""
    
    @abstractmethod
    async def get_by_project(self, project_id: str, limit: int = 100) -> List[Any]:
        """Busca eventos por projeto"""
        pass
    
    @abstractmethod
    async def get_by_action(self, action: str) -> List[Any]:
        """Busca eventos por ação"""
        pass
    
    @abstractmethod
    async def get_blocked_events(self, project_id: Optional[str] = None) -> List[Any]:
        """Busca eventos bloqueados"""
        pass


@dataclass
class RepositoryResult:
    """Resultado padronizado de operações do repository"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    message: Optional[str] = None
    
    @classmethod
    def success_result(cls, data: Any, message: str = "Operation successful"):
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def error_result(cls, error: str, message: str = "Operation failed"):
        return cls(success=False, error=error, message=message)
