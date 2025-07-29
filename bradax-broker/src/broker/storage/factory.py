"""
Repository Factory - Bradax Broker

Factory para criação e gerenciamento de repositories seguindo padrões corporativos.
"""

from typing import Dict, Any
from .interfaces import IProjectRepository, ITelemetryRepository, IGuardrailRepository
from .repositories import ProjectRepository, TelemetryRepository, GuardrailRepository


class RepositoryFactory:
    """Factory para criação de repositories"""
    
    _instances: Dict[str, Any] = {}
    
    @classmethod
    def get_project_repository(cls, file_path: str = "data/projects.json") -> IProjectRepository:
        """Retorna instância singleton do ProjectRepository"""
        key = f"project_{file_path}"
        if key not in cls._instances:
            cls._instances[key] = ProjectRepository(file_path)
        return cls._instances[key]
    
    @classmethod
    def get_telemetry_repository(cls, file_path: str = "data/telemetry.json") -> ITelemetryRepository:
        """Retorna instância singleton do TelemetryRepository"""
        key = f"telemetry_{file_path}"
        if key not in cls._instances:
            cls._instances[key] = TelemetryRepository(file_path)
        return cls._instances[key]
    
    @classmethod
    def get_guardrail_repository(cls, file_path: str = "data/guardrails.json") -> IGuardrailRepository:
        """Retorna instância singleton do GuardrailRepository"""
        key = f"guardrail_{file_path}"
        if key not in cls._instances:
            cls._instances[key] = GuardrailRepository(file_path)
        return cls._instances[key]
    
    @classmethod
    def clear_instances(cls):
        """Limpa todas as instâncias (útil para testes)"""
        cls._instances.clear()
    
    @classmethod
    def get_all_repositories(cls) -> Dict[str, Any]:
        """Retorna todos os repositories instanciados"""
        return {
            "projects": cls.get_project_repository(),
            "telemetry": cls.get_telemetry_repository(),
            "guardrails": cls.get_guardrail_repository()
        }


# Instância global para uso fácil
repository_factory = RepositoryFactory()
