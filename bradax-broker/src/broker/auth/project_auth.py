"""
Project Authentication Module

Implementa autenticação corporativa baseada em ProjectAuth
alinhada com a estratégia de segurança bradax.

Utiliza sistema de constantes centralizado e nomenclatura unificada.
"""

import logging
import os
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import jwt
from pydantic import BaseModel
from fastapi import HTTPException, status

# Adicionar o path para bradax-constants se não estiver instalado
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'bradax-constants', 'src'))

try:
    from bradax_constants import (
        SecurityConstants,
        OrganizationConstants,
        BudgetConstants,
        TestingConstants
    )
except ImportError:
    # Fallback para desenvolvimento
    class SecurityConstants:
        API_KEY_PREFIX = "bradax_"
        JWT_ALGORITHM = "HS256"
        
    class OrganizationConstants:
        ORGANIZATION_NAME = "Bradax AI Solutions"
        ORGANIZATION_DEPARTMENT = "AI Research & Development"
        
    class BudgetConstants:
        DEFAULT_BUDGET_DEVELOPMENT = 100.0
        DEFAULT_BUDGET_TESTING = 50.0
        
    class TestingConstants:
        TEST_PROJECT_PREFIX = "proj_test_"
        TEST_API_KEY_PREFIX = "bradax_test_"

from broker.config import settings

logger = logging.getLogger(__name__)


class ProjectCredentials(BaseModel):
    """Credenciais do projeto"""
    project_id: str
    api_key: str
    organization: str
    department: str
    budget_limit: float
    allowed_models: List[str]


class ProjectAuthManager:
    """Gerenciador de autenticação de projetos corporativos bradax"""
    
    def __init__(self):
        self.projects_cache: Dict[str, ProjectCredentials] = {}
        self._load_default_projects()
    
    def _load_default_projects(self):
        """Carrega projetos padrão para desenvolvimento usando constantes"""
        # Projeto de teste - mesmo ID usado no SDK corporativo
        test_project = ProjectCredentials(
            project_id="proj_test_test_test_2025_a1b2c3d4",
            api_key="bradax_test_api_key_12345",  # Novo prefixo bradax_
            organization=OrganizationConstants.ORGANIZATION_NAME,
            department="TI - Desenvolvimento",
            budget_limit=BudgetConstants.DEFAULT_BUDGET_DEVELOPMENT,
            allowed_models=["gpt-4.1-nano", "gpt-4.1-mini"]
        )
        self.projects_cache[test_project.project_id] = test_project
        
        # Projeto de teste funcional - novo para validação completa
        functional_test_project = ProjectCredentials(
            project_id="proj_bradax_teste_funcional_2025_xyz123",
            api_key="bradax_teste_funcional_api_key_67890",  # Novo prefixo bradax_
            organization=OrganizationConstants.ORGANIZATION_NAME,
            department="TI - Platform Testing",
            budget_limit=BudgetConstants.DEFAULT_BUDGET_TESTING,
            allowed_models=["gpt-4.1-nano", "gpt-4.1-mini"]
        )
        self.projects_cache[functional_test_project.project_id] = functional_test_project
        
        logger.info(f"✅ Projeto corporativo carregado: {test_project.project_id}")
        logger.info(f"✅ Projeto teste funcional carregado: {functional_test_project.project_id}")
    
    async def authenticate_project(
        self, 
        project_id: str, 
        api_key: str
    ) -> ProjectCredentials:
        """
        Autentica um projeto corporativo
        
        Args:
            project_id: ID do projeto
            api_key: Chave de API do projeto
            
        Returns:
            Credenciais validadas do projeto
            
        Raises:
            HTTPException: Se autenticação falhar
        """
        
        # Validar formato do project_id (padrão corporativo)
        if not project_id.startswith("proj_"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Project ID deve seguir padrão corporativo (proj_*)"
            )
        
        # Validar formato da API key - usar constante do novo sistema
        if not api_key.startswith(SecurityConstants.API_KEY_PREFIX):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"API Key deve seguir padrão corporativo ({SecurityConstants.API_KEY_PREFIX}*)"
            )
        
        # Buscar projeto no cache/banco
        project = self.projects_cache.get(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Projeto não encontrado: {project_id}"
            )
        
        # Validar API key
        if project.api_key != api_key:
            logger.warning(f"🚫 Tentativa de acesso inválida para projeto: {project_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key inválida"
            )
        
        logger.info(f"✅ Projeto autenticado com sucesso: {project_id}")
        return project
    
    async def generate_access_token(
        self, 
        project: ProjectCredentials,
        scopes: Optional[List[str]] = None
    ) -> str:
        """
        Gera token de acesso JWT para o projeto
        
        Args:
            project: Credenciais do projeto
            scopes: Escopos solicitados
            
        Returns:
            Token JWT assinado
        """
        
        # Validar escopos solicitados
        allowed_scopes = ["llm:read", "llm:write", "vector:read", "vector:write", "graph:execute"]
        if scopes:
            invalid_scopes = set(scopes) - set(allowed_scopes)
            if invalid_scopes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Escopos inválidos: {invalid_scopes}"
                )
        else:
            scopes = allowed_scopes
        
        # Payload do token
        now = datetime.utcnow()
        payload = {
            "sub": project.project_id,
            "iss": "bradax-broker",
            "aud": "bradax-services",
            "iat": now,
            "exp": now + timedelta(minutes=settings.BRADAX_BROKER_JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            "project_id": project.project_id,
            "organization": project.organization,
            "department": project.department,
            "budget_limit": project.budget_limit,
            "allowed_models": project.allowed_models,
            "scopes": scopes
        }
        
        # Assinar token - usar constante para algoritmo
        token = jwt.encode(
            payload,
            settings.BRADAX_BROKER_JWT_SECRET_KEY,
            algorithm=SecurityConstants.JWT_ALGORITHM
        )
        
        logger.info(f"🔑 Token gerado para projeto: {project.project_id}")
        return token
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Valida e decodifica token JWT
        
        Args:
            token: Token JWT para validar
            
        Returns:
            Payload decodificado do token
            
        Raises:
            HTTPException: Se token for inválido
        """
        
        try:
            payload = jwt.decode(
                token,
                settings.BRADAX_BROKER_JWT_SECRET_KEY,
                algorithms=[SecurityConstants.JWT_ALGORITHM],
                audience="bradax-services"
            )
            
            # Validar se projeto ainda existe
            project_id = payload.get("project_id")
            if project_id not in self.projects_cache:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Projeto não encontrado"
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expirado"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )


# Instância global do gerenciador
project_auth = ProjectAuthManager()
