"""
📋 Bradax Project Client
Cliente para operações específicas de projeto.
"""
from typing import Optional, Dict, Any
from ..config.sdk_config import ProjectConfig
from ..exceptions.bradax_exceptions import BradaxError


class BradaxProjectClient:
    """Cliente para operações de projeto."""
    
    def __init__(self, project_config: Optional[ProjectConfig] = None):
        """Inicializa cliente de projeto.
        
        Args:
            project_config: Configuração do projeto
        """
        self.config = project_config or ProjectConfig()
        self._initialized = False
    
    def initialize(self, project_id: str, name: str) -> bool:
        """Inicializa projeto.
        
        Args:
            project_id: ID do projeto
            name: Nome do projeto
            
        Returns:
            True se inicialização bem-sucedida
        """
        try:
            self.config.project_id = project_id
            self.config.name = name
            self._initialized = True
            return True
        except Exception as e:
            raise BradaxError(f"Erro ao inicializar projeto: {e}")
    
    def get_info(self) -> Dict[str, Any]:
        """Retorna informações do projeto.
        
        Returns:
            Dicionário com informações do projeto
        """
        if not self._initialized:
            raise BradaxError("Projeto não inicializado")
        
        return {
            "project_id": self.config.project_id,
            "name": self.config.name,
            "status": "active" if self._initialized else "inactive"
        }
