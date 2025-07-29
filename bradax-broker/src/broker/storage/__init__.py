"""
Storage Module - Bradax Broker

Módulo de persistência implementando padrão Repository.
"""

# Importações das interfaces
from .interfaces import (
    IRepository,
    IProjectRepository,
    ITelemetryRepository,
    IGuardrailRepository,
    RepositoryResult
)

# Importações das implementações
from .repositories import (
    ProjectRepository,
    TelemetryRepository,
    GuardrailRepository
)

# Factory e dados legacy
from .factory import RepositoryFactory, repository_factory
from .json_storage import ProjectData, TelemetryData, GuardrailEvent, SystemInfo

# Instâncias globais para compatibilidade
project_repo = repository_factory.get_project_repository()
telemetry_repo = repository_factory.get_telemetry_repository()
guardrail_repo = repository_factory.get_guardrail_repository()

__all__ = [
    # Interfaces
    "IRepository",
    "IProjectRepository", 
    "ITelemetryRepository",
    "IGuardrailRepository",
    "RepositoryResult",
    
    # Implementações
    "ProjectRepository",
    "TelemetryRepository", 
    "GuardrailRepository",
    
    # Factory
    "RepositoryFactory",
    "repository_factory",
    
    # Data models
    "ProjectData",
    "TelemetryData",
    "GuardrailEvent", 
    "SystemInfo",
    
    # Instâncias globais
    "project_repo",
    "telemetry_repo",
    "guardrail_repo"
]
