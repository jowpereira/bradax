"""
Rotas de Gerenciamento de Projetos - Versão Simplificada

API REST básica para projetos usando controllers MVC.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from ...controllers.project_controller import ProjectController


# Instância do controller
project_controller = ProjectController()

# Criar router
router = APIRouter(prefix="/projects", tags=["Projects"])


# Modelos Pydantic básicos
class CreateProjectRequest(BaseModel):
    """Modelo para criação de projeto"""
    name: str = Field(..., min_length=3, max_length=100, description="Nome do projeto")
    description: Optional[str] = Field(None, max_length=500, description="Descrição do projeto")
    active: Optional[bool] = Field(True, description="Projeto ativo")


class UpdateProjectRequest(BaseModel):
    """Modelo para atualização de projeto"""
    name: Optional[str] = Field(None, min_length=3, max_length=100, description="Nome do projeto")
    description: Optional[str] = Field(None, max_length=500, description="Descrição do projeto")
    active: Optional[bool] = Field(None, description="Projeto ativo")


# ============================================================================
#                               ENDPOINTS BÁSICOS
# ============================================================================

@router.get("/", response_model=List[Dict[str, Any]])
async def list_projects():
    """
    Lista todos os projetos disponíveis
    
    Returns:
        List: Lista de projetos
    """
    try:
        response = project_controller.list_resources()
        if response.get("success"):
            return response.get("data", [])
        else:
            raise HTTPException(status_code=500, detail=response.get("error", "Erro desconhecido"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.post("/", response_model=Dict[str, Any])
async def create_project(project_data: CreateProjectRequest):
    """
    Cria um novo projeto
    
    Args:
        project_data: Dados do projeto
        
    Returns:
        Dict: Projeto criado
    """
    try:
        response = project_controller.create_resource(project_data.dict())
        if response.get("success"):
            return response.get("data")
        else:
            raise HTTPException(status_code=400, detail=response.get("error", "Erro na criação"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.get("/{project_id}", response_model=Dict[str, Any])
async def get_project(project_id: str):
    """
    Obtém detalhes de um projeto específico
    
    Args:
        project_id: ID do projeto
        
    Returns:
        Dict: Dados do projeto
    """
    try:
        response = project_controller.get_resource(project_id)
        if response.get("success"):
            return response.get("data")
        else:
            raise HTTPException(status_code=404, detail="Projeto não encontrado")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.put("/{project_id}", response_model=Dict[str, Any])
async def update_project(project_id: str, project_data: UpdateProjectRequest):
    """
    Atualiza um projeto existente
    
    Args:
        project_id: ID do projeto
        project_data: Novos dados do projeto
        
    Returns:
        Dict: Projeto atualizado
    """
    try:
        update_dict = {k: v for k, v in project_data.dict().items() if v is not None}
        if not update_dict:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
            
        response = project_controller.update_resource(project_id, update_dict)
        if response.get("success"):
            return response.get("data")
        else:
            raise HTTPException(status_code=404, detail="Projeto não encontrado")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """
    Remove um projeto
    
    Args:
        project_id: ID do projeto
        
    Returns:
        Dict: Confirmação de remoção
    """
    try:
        response = project_controller.delete_resource(project_id)
        if response.get("success"):
            return {"message": "Projeto removido com sucesso", "project_id": project_id}
        else:
            raise HTTPException(status_code=404, detail="Projeto não encontrado")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.get("/{project_id}/health")
async def project_health(project_id: str):
    """
    Verifica saúde/status de um projeto
    
    Args:
        project_id: ID do projeto
        
    Returns:
        Dict: Status de saúde do projeto
    """
    try:
        # O controller não tem método específico para health, 
        # vamos usar get_resource e adicionar informações de status
        response = project_controller.get_resource(project_id)
        if response.get("success"):
            project = response.get("data")
            return {
                "project_id": project_id,
                "status": "healthy" if project.get("active", False) else "inactive",
                "last_updated": project.get("updated_at"),
                "permissions_count": len(project.get("permissions", [])),
                "has_api_key": bool(project.get("api_key"))
            }
        else:
            raise HTTPException(status_code=404, detail="Projeto não encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
