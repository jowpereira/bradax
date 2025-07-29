"""
Project Controller - Padrão MVC

Controller dedicado para operações de gerenciamento de projetos.
"""

from typing import Dict, Any, Optional, List
from fastapi import HTTPException
import time
import uuid

from ..controllers import ResourceController, ControllerResponse
from ..storage.json_storage import JsonStorage
from ..auth.project_auth import ProjectAuth


class ProjectController(ResourceController):
    """
    Controller para gerenciamento de projetos
    
    Responsável por operações CRUD de projetos e
    configurações de acesso.
    """
    
    def __init__(self):
        super().__init__()
        self.storage = JsonStorage()
        self.auth = ProjectAuth()
    
    def list_resources(self, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Lista todos os projetos com filtros opcionais"""
        try:
            self._log_request("list_projects", {"filters": filters})
            
            # Carregar projetos do storage
            projects = self.storage.list_projects()
            
            # Converter ProjectData para dict
            projects_dict = []
            for project in projects:
                if hasattr(project, '__dict__'):
                    projects_dict.append(project.__dict__)
                else:
                    projects_dict.append(project)
            
            # Aplicar filtros
            if filters:
                projects_dict = self._apply_filters(projects_dict, filters)
            
            # Sanitizar dados sensíveis
            sanitized_projects = [
                self._sanitize_project_data(project) for project in projects_dict
            ]
            
            self._log_response("list_projects", True, {"count": len(sanitized_projects)})
            
            return ControllerResponse.success(
                data=sanitized_projects,
                message=f"Found {len(sanitized_projects)} projects"
            )
            
        except Exception as e:
            self._log_response("list_projects", False, {"error": str(e)})
            raise self._handle_error(e, "list_projects")
    
    def get_resource(self, resource_id: str) -> Dict[str, Any]:
        """Obtém projeto específico por ID"""
        try:
            self._log_request("get_project", {"project_id": resource_id})
            
            project_data = self.storage.get_project(resource_id)
            
            if not project_data:
                return ControllerResponse.error(
                    error_message=f"Project {resource_id} not found",
                    error_code="PROJECT_NOT_FOUND"
                )
            
            # Converter ProjectData para dict se necessário
            if hasattr(project_data, '__dict__'):
                project = project_data.__dict__
            else:
                project = project_data
            
            sanitized_project = self._sanitize_project_data(project)
            
            self._log_response("get_project", True, {"project_id": resource_id})
            
            return ControllerResponse.success(
                data=sanitized_project,
                message=f"Project {resource_id} retrieved successfully"
            )
            
        except Exception as e:
            self._log_response("get_project", False, {"error": str(e)})
            raise self._handle_error(e, "get_project")
    
    def create_resource(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Cria novo projeto"""
        try:
            self._log_request("create_project", {"name": data.get("name")})
            
            # Validar dados
            self._validate_project_data(data)
            
            # Gerar ID único
            project_id = str(uuid.uuid4())
            
            # Preparar dados do projeto
            project_data = {
                "id": project_id,
                "name": self._sanitize_input(data["name"]),
                "description": self._sanitize_input(data.get("description", "")),
                "created_at": time.time(),
                "updated_at": time.time(),
                "active": data.get("active", True),
                "settings": data.get("settings", {}),
                "api_key": self._generate_api_key(),
                "permissions": data.get("permissions", self._default_permissions())
            }
            
            # Salvar no storage
            projects_data = self.storage.load_projects()
            projects = projects_data.get("projects", [])
            projects.append(project_data)
            
            self.storage.save_projects({"projects": projects})
            
            # Retornar dados sanitizados
            sanitized_project = self._sanitize_project_data(project_data)
            
            self._log_response("create_project", True, {"project_id": project_id})
            
            return ControllerResponse.success(
                data=sanitized_project,
                message=f"Project {project_data['name']} created successfully"
            )
            
        except Exception as e:
            self._log_response("create_project", False, {"error": str(e)})
            raise self._handle_error(e, "create_project")
    
    def update_resource(self, resource_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza projeto existente"""
        try:
            self._log_request("update_project", {"project_id": resource_id})
            
            # Validar dados parciais
            self._validate_project_update_data(data)
            
            # Carregar projetos
            projects_data = self.storage.load_projects()
            projects = projects_data.get("projects", [])
            
            # Encontrar projeto
            project_index = next(
                (i for i, p in enumerate(projects) if p.get("id") == resource_id),
                None
            )
            
            if project_index is None:
                raise KeyError(f"Project {resource_id} not found")
            
            # Atualizar campos
            project = projects[project_index]
            updatable_fields = ["name", "description", "active", "settings", "permissions"]
            
            for field in updatable_fields:
                if field in data:
                    project[field] = self._sanitize_input(data[field])
            
            project["updated_at"] = time.time()
            
            # Salvar
            self.storage.save_projects({"projects": projects})
            
            sanitized_project = self._sanitize_project_data(project)
            
            self._log_response("update_project", True, {"project_id": resource_id})
            
            return ControllerResponse.success(
                data=sanitized_project,
                message=f"Project {resource_id} updated successfully"
            )
            
        except Exception as e:
            self._log_response("update_project", False, {"error": str(e)})
            raise self._handle_error(e, "update_project")
    
    def delete_resource(self, resource_id: str) -> Dict[str, Any]:
        """Remove projeto"""
        try:
            self._log_request("delete_project", {"project_id": resource_id})
            
            projects_data = self.storage.load_projects()
            projects = projects_data.get("projects", [])
            
            # Encontrar e remover projeto
            original_count = len(projects)
            projects = [p for p in projects if p.get("id") != resource_id]
            
            if len(projects) == original_count:
                raise KeyError(f"Project {resource_id} not found")
            
            # Salvar
            self.storage.save_projects({"projects": projects})
            
            self._log_response("delete_project", True, {"project_id": resource_id})
            
            return ControllerResponse.success(
                data={"deleted_project_id": resource_id},
                message=f"Project {resource_id} deleted successfully"
            )
            
        except Exception as e:
            self._log_response("delete_project", False, {"error": str(e)})
            raise self._handle_error(e, "delete_project")
    
    def verify_project_access(self, project_id: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Verifica acesso ao projeto"""
        try:
            self._log_request("verify_access", {"project_id": project_id})
            
            is_authorized = self.auth.verify_project_access(project_id, api_key)
            
            self._log_response("verify_access", is_authorized, {"project_id": project_id})
            
            return ControllerResponse.success(
                data={"authorized": is_authorized, "project_id": project_id},
                message="Access verification completed"
            )
            
        except Exception as e:
            self._log_response("verify_access", False, {"error": str(e)})
            raise self._handle_error(e, "verify_access")
    
    def _validate_project_data(self, data: Dict[str, Any]) -> None:
        """Valida dados completos de projeto"""
        required_fields = ["name"]
        self._validate_required_fields(data, required_fields)
        
        if not isinstance(data["name"], str) or len(data["name"].strip()) < 3:
            raise ValueError("Project name must be at least 3 characters")
        
        if len(data["name"]) > 100:
            raise ValueError("Project name must be less than 100 characters")
    
    def _validate_project_update_data(self, data: Dict[str, Any]) -> None:
        """Valida dados de atualização de projeto"""
        if "name" in data:
            if not isinstance(data["name"], str) or len(data["name"].strip()) < 3:
                raise ValueError("Project name must be at least 3 characters")
    
    def _sanitize_project_data(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """Remove dados sensíveis do projeto"""
        safe_project = project.copy()
        # Remover API key das respostas públicas
        safe_project.pop("api_key", None)
        return safe_project
    
    def _apply_filters(self, projects: List[Dict], filters: Dict) -> List[Dict]:
        """Aplica filtros à lista de projetos"""
        filtered = projects
        
        if "active" in filters:
            filtered = [p for p in filtered if p.get("active") == filters["active"]]
        
        if "name_contains" in filters:
            search_term = filters["name_contains"].lower()
            filtered = [p for p in filtered if search_term in p.get("name", "").lower()]
        
        return filtered
    
    def _generate_api_key(self) -> str:
        """Gera API key única para o projeto"""
        return f"bradax_{uuid.uuid4().hex[:16]}"
    
    def _default_permissions(self) -> Dict[str, Any]:
        """Retorna permissões padrão para novos projetos"""
        return {
            "llm_access": True,
            "max_requests_per_hour": 1000,
            "allowed_models": ["all"],
            "guardrails_level": "standard"
        }


# Instância singleton do controller
project_controller = ProjectController()
