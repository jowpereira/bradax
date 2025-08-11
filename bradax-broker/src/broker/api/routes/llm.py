"""
Rotas da API LLM - Usando Controllers MVC

Endpoints para operações de LLM com controllers dedicados.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from ...controllers.llm_controller import llm_controller


# Criar router
router = APIRouter(tags=["LLM"])


# Modelos Pydantic para validação
class GenerateRequest(BaseModel):
    """Modelo para requisição de geração"""
    model: str = Field(..., description="ID do modelo LLM")
    prompt: str = Field(..., description="Prompt para o modelo")
    system_prompt: Optional[str] = Field(None, description="Prompt de sistema")
    max_tokens: Optional[int] = Field(1000, ge=1, le=32000, description="Máximo de tokens")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Temperatura")
    stream: Optional[bool] = Field(False, description="Streaming de resposta")
    project_id: Optional[str] = Field(None, description="ID do projeto")


class InvokeRequest(BaseModel):
    """Modelo para requisição de invoke"""
    operation: str = Field(..., description="Tipo de operação (chat, completion, batch, stream)")
    model: str = Field(..., description="ID do modelo LLM")
    payload: Dict[str, Any] = Field(..., description="Payload completo da requisição")
    project_id: Optional[str] = Field(None, description="ID do projeto")
    request_id: Optional[str] = Field(None, description="ID da requisição")
    custom_guardrails: Optional[Dict[str, Any]] = Field({}, description="Guardrails customizados do SDK")


@router.get("/models")
async def get_available_models(project_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Lista modelos LLM disponíveis
    
    Args:
        project_id: ID do projeto para filtros específicos
        
    Returns:
        Lista de modelos disponíveis
    """
    try:
        result = llm_controller.get_available_models(project_id=project_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")


@router.post("/invoke")
async def invoke(request: InvokeRequest, raw: Request) -> Dict[str, Any]:
    """
    Invocação central para wrapper LangChain
    
    Ponto de entrada único para diferentes tipos de operações LLM.
    Suporta: chat, completion, batch, stream, etc.
    
    Args:
        request: Dados da requisição
        
    Returns:
        Resultado da operação + metadados
    """
    try:
        # Executar invoke via controller
        # Se project_id ausente no payload, tentar extrair de Authorization: Bearer <token>
        project_id = request.project_id
        if not project_id:
            auth_header = raw.headers.get('authorization') or raw.headers.get('Authorization')
            if auth_header and auth_header.lower().startswith('bearer '):
                bearer_token = auth_header.split(' ', 1)[1].strip()
                # Heurística simples: tokens do formato proj_* usados diretamente
                if bearer_token.startswith('proj_'):
                    project_id = bearer_token
        try:
            logging.getLogger("bradax.api.invoke").info(
                "invoke_route_project_resolution",
                extra={"resolved_project_id": project_id, "has_auth": bool(raw.headers.get('authorization'))}
            )
        except Exception:
            pass
        result = await llm_controller.invoke(
            operation=request.operation,
            model_id=request.model,
            payload=request.payload,
            project_id=project_id,
            request_id=request.request_id,
            custom_guardrails=request.custom_guardrails  # CORREÇÃO: Passar guardrails customizados
        )
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")


@router.post("/generate")
async def generate_response(request: GenerateRequest) -> Dict[str, Any]:
    """
    Gera resposta usando LLM
    
    Args:
        request: Dados da requisição LLM
        
    Returns:
        Resposta do modelo
    """
    try:
        # Converter Pydantic model para dict
        request_data = request.dict()
        
        # Executar geração via controller
        result = await llm_controller.generate_response(request_data)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")


@router.get("/status")
async def get_service_status() -> Dict[str, Any]:
    """
    Obtém status do serviço LLM
    
    Returns:
        Status de providers e estatísticas
    """
    try:
        result = llm_controller.get_service_status()
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")


@router.post("/reload")
async def reload_service() -> Dict[str, Any]:
    """
    Recarrega configuração do serviço
    
    Returns:
        Resultado do reload
    """
    try:
        result = llm_controller.reload_service()
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")


@router.get("/models/{model_id}/info")
async def get_model_info(model_id: str) -> Dict[str, Any]:
    """
    Obtém informações detalhadas de um modelo específico
    
    Args:
        model_id: ID do modelo
        
    Returns:
        Informações do modelo
    """
    try:
        # Via controller será implementado no próximo commit
        # Por enquanto usando serviço diretamente
        from ...services.llm.service import LLMService
        
        service = LLMService()
        model_info = service.get_model_info(model_id)
        
        if not model_info:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
        
        model_data = {
            "model_id": model_info.model_id,
            "name": model_info.name,
            "provider": model_info.provider.value,
            "provider_model_name": model_info.provider_model_name,
            "max_tokens": model_info.max_tokens,
            "cost_per_1k_input": model_info.cost_per_1k_input,
            "cost_per_1k_output": model_info.cost_per_1k_output,
            "capabilities": [cap.value for cap in model_info.capabilities],
            "enabled": model_info.enabled
        }
        
        return {
            "success": True,
            "message": f"Model {model_id} information retrieved",
            "data": model_data,
            "error": None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")