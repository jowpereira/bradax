"""
LLM Operations endpoints

Gerencia requisições para Large Language Models,
incluindo autenticação corporativa e invocação segura.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel
import json
import asyncio

from broker.services.openai_service import OpenAIService
from broker.auth.project_auth import project_auth

router = APIRouter()
security = HTTPBearer()


class LLMInvokeRequest(BaseModel):
    model: str
    messages: List[Dict[str, Any]]
    parameters: Optional[Dict[str, Any]] = None


class LLMStreamRequest(BaseModel):
    model: str
    messages: List[Dict[str, Any]]
    parameters: Optional[Dict[str, Any]] = None


# Instância global do serviço OpenAI
openai_service = None


def get_openai_service() -> OpenAIService:
    """Dependency para obter instância do OpenAI service"""
    global openai_service
    if openai_service is None:
        try:
            openai_service = OpenAIService()
        except ValueError as e:
            raise HTTPException(
                status_code=500,
                detail=f"OpenAI não configurado: {str(e)}"
            )
    return openai_service


async def validate_project_auth(token = Depends(security)) -> Dict[str, Any]:
    """Valida autenticação do projeto e retorna payload"""
    return await project_auth.validate_token(token.credentials)


@router.post("/invoke", summary="Invocar LLM (síncrono)")
async def invoke_llm(
    request: LLMInvokeRequest,
    service: OpenAIService = Depends(get_openai_service),
    auth_payload: Dict[str, Any] = Depends(validate_project_auth)
) -> Dict[str, Any]:
    """
    Invoca um LLM de forma síncrona com autenticação corporativa.
    
    Args:
        request: Dados da requisição (model, messages, parameters)
        service: Serviço OpenAI
        auth_payload: Dados de autenticação do projeto
        
    Returns:
        Resposta do LLM com usage tracking e auditoria
    """
    
    if not request.model or not request.messages:
        raise HTTPException(
            status_code=400,
            detail="model e messages são obrigatórios"
        )
    
    # Validar se modelo está permitido no projeto
    allowed_models = auth_payload.get("allowed_models", [])
    if request.model not in allowed_models:
        raise HTTPException(
            status_code=403,
            detail=f"Modelo {request.model} não permitido para este projeto. Modelos permitidos: {allowed_models}"
        )
    
    try:
        # Adicionar informações de auditoria
        audit_info = {
            "project_id": auth_payload.get("project_id"),
            "organization": auth_payload.get("organization"),
            "model_requested": request.model
        }
        
        # Usar serviço OpenAI real
        result = await service.invoke_llm(request.model, request.messages, request.parameters)
        
        # Adicionar informações de auditoria ao resultado
        result["audit"] = audit_info
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream", summary="Invocar LLM (streaming)")
async def stream_llm(
    request: LLMStreamRequest,
    service: OpenAIService = Depends(get_openai_service),
    auth_payload: Dict[str, Any] = Depends(validate_project_auth)
) -> StreamingResponse:
    """
    Invoca um LLM com streaming de resposta e autenticação corporativa.
    
    Args:
        request: Dados da requisição (model, messages, parameters)
        service: Serviço OpenAI
        auth_payload: Dados de autenticação do projeto
        
    Returns:
        Server-Sent Events com streaming da resposta
    """
    
    if not request.model or not request.messages:
        raise HTTPException(
            status_code=400,
            detail="model e messages são obrigatórios"
        )
    
    # Validar se modelo está permitido no projeto
    allowed_models = auth_payload.get("allowed_models", [])
    if request.model not in allowed_models:
        raise HTTPException(
            status_code=403,
            detail=f"Modelo {request.model} não permitido para este projeto"
        )

    async def generate_stream():
        try:
            async for chunk in service.stream_llm(request.model, request.messages, request.parameters):
                # Adicionar informações de auditoria no primeiro chunk
                if chunk.get("choices") and len(chunk["choices"]) > 0:
                    chunk["audit"] = {
                        "project_id": auth_payload.get("project_id"),
                        "organization": auth_payload.get("organization")
                    }
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            error_chunk = {"error": str(e), "finished": True}
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )


@router.get("/models", summary="Listar modelos disponíveis")
async def list_models(
    service: OpenAIService = Depends(get_openai_service),
    auth_payload: Dict[str, Any] = Depends(validate_project_auth)
) -> Dict[str, Any]:
    """
    Lista modelos LLM permitidos para o projeto autenticado.
    
    Args:
        service: Serviço OpenAI
        auth_payload: Dados de autenticação do projeto
        
    Returns:
        Lista de modelos permitidos com capacidades
    """
    
    all_models = service.get_available_models()
    allowed_models = auth_payload.get("allowed_models", [])
    
    # Filtrar apenas modelos permitidos para o projeto
    filtered_models = {
        model: details for model, details in all_models.items()
        if model in allowed_models
    }
    
    return {
        "models": filtered_models,
        "project_id": auth_payload.get("project_id"),
        "total_allowed": len(filtered_models)
    }
