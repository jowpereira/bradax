"""
Repository Factory - Bradax Broker

Factory para criação e gerenciamento de repositories seguindo padrões corporativos.
"""

from typing import Dict, Any
from .interfaces import IProjectRepository, ITelemetryRepository, IGuardrailRepository
from .repositories import ProjectRepository, TelemetryRepository, GuardrailRepository
from ..logging_config import storage_logger


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


def create_storage_repositories() -> Dict[str, Any]:
    """
    Cria e retorna repositories usando caminhos absolutos para data/ da raiz.
    
    IMPORTANTE: Sempre usa pasta data/ da raiz do projeto, sem fallbacks.
    """
    from pathlib import Path
    import os
    
    # Encontrar raiz do projeto (pasta bradax)
    current_dir = Path(__file__).resolve()
    project_root = None
    
    for parent in current_dir.parents:
        if parent.name == "bradax":
            project_root = parent
            break
    
    if not project_root:
        raise RuntimeError("Pasta raiz 'bradax' não encontrada - estrutura de projeto incorreta")
    
    from ..utils.paths import get_data_dir
    data_dir = get_data_dir()
    
    # Garantir que diretório data/ existe
    if not data_dir.exists():
        raise RuntimeError(f"Diretório obrigatório não encontrado: {data_dir}")
    
    # Criar repositories com caminhos absolutos
    factory = RepositoryFactory()
    
    repositories = {
        "project": factory.get_project_repository(str(data_dir / "projects.json")),
        "telemetry": factory.get_telemetry_repository(str(data_dir / "telemetry.json")),
        "guardrail": factory.get_guardrail_repository(str(data_dir / "guardrail_events.json"))
    }
    
    storage_logger.info(
        f"Repositories criados em {str(data_dir)}: {list(repositories.keys())}"
    )
    return repositories


# Instância global para uso fácil
repository_factory = RepositoryFactory()
