"""
Authentication endpoints

Gerencia autenticação JWT corporativa, emissão de tokens e validação
de credenciais para projetos bradax.

Utiliza sistema de constantes centralizado para eliminar hard-code.
"""

import os
import sys
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel

# Adicionar o path para bradax-constants se não estiver instalado
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'bradax-constants', 'src'))

try:
    from bradax_constants import (
        SecurityConstants,
        LLMConstants,
        OrganizationConstants
    )
except ImportError:
    # Fallback para desenvolvimento
    class SecurityConstants:
        JWT_EXPIRATION_MINUTES = 15
        DEFAULT_REQUESTS_PER_MINUTE = 60
        DEFAULT_REQUESTS_PER_HOUR = 1000
        DEFAULT_MAX_CONCURRENT = 5

    class LLMConstants:
        DEFAULT_MAX_TOKENS_PER_REQUEST = 8192

    class OrganizationConstants:
        ORGANIZATION_NAME = "Bradax AI Solutions"

from ...auth.project_auth import project_auth

router = APIRouter()
security = HTTPBearer()


class TokenRequest(BaseModel):
    """Request para obtenção de token"""
    project_id: str
    api_key: str
    scopes: Optional[List[str]] = None


class TokenResponse(BaseModel):
    """Response com tokens de acesso"""
    access_token: str
    token_type: str
    expires_in: int
    project_id: str
    organization: str
    scopes: List[str]


@router.post("/token", response_model=TokenResponse, summary="Autenticação Corporativa")
async def authenticate(request: TokenRequest) -> TokenResponse:
    """
    Autentica um projeto corporativo e retorna token JWT.

    Args:
        request: Dados de autenticação do projeto

    Returns:
        Token JWT com informações corporativas
    """

    # Autenticar projeto
    project = await project_auth.authenticate_project_async(
        project_id=request.project_id,
        api_key=request.api_key
    )

    # Gerar token de acesso
    access_token = await project_auth.generate_access_token(
        project=project,
        scopes=request.scopes
    )

    return TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=SecurityConstants.JWT_EXPIRATION_MINUTES * 60,  # Converter para segundos
        project_id=project.project_id,
        organization=project.organization_id,
        scopes=request.scopes or ["llm:read", "llm:write", "vector:read", "vector:write", "graph:execute"]
    )


@router.post("/validate", summary="Validar Token")
async def validate_token(token: str = Depends(security)) -> Dict[str, Any]:
    """
    Valida um token JWT e retorna informações do projeto.

    Args:
        token: Token JWT para validar

    Returns:
        Informações do projeto autenticado
    """

    # Extrair token do header Authorization
    token_value = token.credentials

    # Validar token
    payload = await project_auth.validate_token(token_value)

    return {
        "valid": True,
        "project_id": payload.get("project_id"),
        "organization": payload.get("organization"),
        "department": payload.get("department"),
        "scopes": payload.get("scopes"),
        "expires_at": payload.get("exp")
    }


@router.get("/projects/{project_id}/info", summary="Informações do Projeto")
async def get_project_info(
    project_id: str,
    token: str = Depends(security)
) -> Dict[str, Any]:
    """
    Retorna informações detalhadas do projeto autenticado.

    Utiliza constantes centralizadas para limites e configurações.

    Args:
        project_id: ID do projeto
        token: Token JWT de autenticação

    Returns:
        Informações detalhadas do projeto com configurações baseadas em constantes
    """

    # Validar token
    payload = await project_auth.validate_token(token.credentials)

    # Verificar se token é do projeto solicitado
    if payload.get("project_id") != project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token não autorizado para este projeto"
        )

    return {
        "project_id": project_id,
        "organization": payload.get("organization"),
        "department": payload.get("department"),
        "budget_limit": payload.get("budget_limit"),
        "allowed_models": payload.get("allowed_models"),
        "scopes": payload.get("scopes"),
        "status": "active",
        "max_tokens_per_request": LLMConstants.DEFAULT_MAX_TOKENS_PER_REQUEST,
        "max_requests_per_minute": SecurityConstants.DEFAULT_REQUESTS_PER_MINUTE,
        "max_requests_per_hour": SecurityConstants.DEFAULT_REQUESTS_PER_HOUR,
        "max_concurrent_requests": SecurityConstants.DEFAULT_MAX_CONCURRENT
    }
