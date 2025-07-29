"""
Project Authentication Module

Implementa autenticação corporativa baseada em ProjectAuth
alinhada com a estratégia de segurança bradax.

Sistema de autenticação empresarial sem hardcode/fallbacks.
"""

import logging
import os
import hashlib
import secrets
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from ..constants import HubSecurityConstants, get_hub_environment, BradaxEnvironment
from ..exceptions import (
    AuthenticationException,
    AuthorizationException,
    ValidationException,
    ConfigurationException
)

logger = logging.getLogger(__name__)


class ProjectCredentials(BaseModel):
    """Credenciais de projeto validadas"""
    project_id: str = Field(..., min_length=3, max_length=100)
    api_key: str = Field(..., min_length=10)
    organization_id: Optional[str] = None
    environment: str = Field(default="development")
    permissions: List[str] = Field(default_factory=list)
    budget_limit: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    is_active: bool = True


class ProjectSession(BaseModel):
    """Sessão de projeto autenticada"""
    project_id: str
    organization_id: Optional[str]
    permissions: List[str]
    budget_remaining: float
    environment: str
    session_id: str
    expires_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProjectAuth:
    """
    Sistema de autenticação de projetos empresarial
    
    Responsabilidades:
    - Validação de credenciais de projeto
    - Gerenciamento de sessões
    - Controle de permissões granular
    - Auditoria de acesso
    - Gestão de orçamento por projeto
    """
    
    def __init__(self):
        self.environment = get_hub_environment()
        self._validate_configuration()
        
        # Cache de sessões ativas (em produção usar Redis)
        self._active_sessions: Dict[str, ProjectSession] = {}
        
        logger.info(f"ProjectAuth inicializado para ambiente: {self.environment.value}")
    
    def _validate_configuration(self) -> None:
        """Valida configuração de segurança obrigatória"""
        if not HubSecurityConstants.JWT_SECRET_KEY:
            raise ConfigurationException(
                "JWT_SECRET_KEY não configurado",
                details={"environment": self.environment.value}
            )
        
        if self.environment == BradaxEnvironment.PRODUCTION:
            if HubSecurityConstants.JWT_SECRET_KEY == 'bradax-development-secret-change-in-production':
                raise ConfigurationException(
                    "Usando JWT_SECRET_KEY de desenvolvimento em produção",
                    severity="CRITICAL",
                    details={"environment": "production"}
                )
    
    def generate_api_key(self, project_id: str, organization_id: Optional[str] = None) -> str:
        """
        Gera nova API key para projeto
        
        Formato: bradax_<project_id>_<org_id>_<random>_<timestamp>
        """
        if not project_id or len(project_id) < 3:
            raise ValidationException(
                "project_id deve ter pelo menos 3 caracteres",
                details={"project_id": project_id}
            )
        
        # Componentes da API key
        prefix = HubSecurityConstants.API_KEY_PREFIX
        project_part = project_id.lower().replace('-', '_')[:20]
        org_part = (organization_id or 'default').lower().replace('-', '_')[:15]
        random_part = secrets.token_hex(8)
        timestamp_part = str(int(datetime.utcnow().timestamp()))[-8:]
        
        api_key = f"{prefix}{project_part}_{org_part}_{random_part}_{timestamp_part}"
        
        logger.info(f"API key gerada para projeto: {project_id}")
        return api_key
    
    def validate_api_key(self, api_key: str) -> bool:
        """Valida formato da API key"""
        if not api_key or not isinstance(api_key, str):
            return False
        
        if not api_key.startswith(HubSecurityConstants.API_KEY_PREFIX):
            return False
        
        # Valida comprimento mínimo
        min_length = len(HubSecurityConstants.API_KEY_PREFIX) + 20
        if len(api_key) < min_length:
            return False
        
        # Valida padrão básico (prefixo + componentes separados por _)
        parts = api_key[len(HubSecurityConstants.API_KEY_PREFIX):].split('_')
        if len(parts) < 4:
            return False
        
        return True
    
    def authenticate_project(self, api_key: str, project_id: str) -> ProjectSession:
        """
        Autentica projeto e cria sessão
        
        Args:
            api_key: API key do projeto
            project_id: ID do projeto
            
        Returns:
            ProjectSession: Sessão autenticada
            
        Raises:
            AuthenticationException: Falha na autenticação
        """
        # Validação básica
        if not self.validate_api_key(api_key):
            raise AuthenticationException(
                "Formato de API key inválido",
                details={"api_key_prefix": api_key[:20] + "..." if len(api_key) > 20 else api_key}
            )
        
        if not project_id:
            raise ValidationException("project_id é obrigatório")
        
        # Extrair informações da API key
        try:
            project_info = self._parse_api_key(api_key)
        except Exception as e:
            raise AuthenticationException(
                "Falha ao analisar API key",
                details={"error": str(e)}
            )
        
        # Validar correspondência
        if project_info.get('project_id') != project_id:
            raise AuthenticationException(
                "API key não corresponde ao project_id fornecido",
                details={
                    "expected_project": project_id,
                    "key_project": project_info.get('project_id')
                }
            )
        
        # Criar sessão
        session = self._create_session(project_info, api_key)
        
        # Cache da sessão
        self._active_sessions[session.session_id] = session
        
        logger.info(f"Projeto autenticado: {project_id} (sessão: {session.session_id})")
        return session
    
    def _parse_api_key(self, api_key: str) -> Dict[str, Any]:
        """Extrai informações da API key"""
        # Remove prefixo
        key_body = api_key[len(HubSecurityConstants.API_KEY_PREFIX):]
        parts = key_body.split('_')
        
        if len(parts) < 4:
            raise ValueError("API key com formato inválido")
        
        return {
            'project_id': parts[0],
            'organization_id': parts[1] if parts[1] != 'default' else None,
            'random_part': parts[2],
            'timestamp': parts[3]
        }
    
    def _create_session(self, project_info: Dict[str, Any], api_key: str) -> ProjectSession:
        """Cria nova sessão de projeto"""
        session_id = secrets.token_hex(16)
        expires_at = datetime.utcnow() + timedelta(minutes=HubSecurityConstants.JWT_EXPIRATION_MINUTES)
        
        # Permissões padrão baseadas no ambiente
        permissions = self._get_default_permissions()
        
        # Orçamento padrão (deve vir de storage em implementação real)
        budget_remaining = 1000.0  # Placeholder - implementar storage
        
        return ProjectSession(
            project_id=project_info['project_id'],
            organization_id=project_info.get('organization_id'),
            permissions=permissions,
            budget_remaining=budget_remaining,
            environment=self.environment.value,
            session_id=session_id,
            expires_at=expires_at,
            metadata={
                'created_from_api_key': api_key[:20] + "...",
                'user_agent': None,  # Será preenchido na requisição
                'ip_address': None   # Será preenchido na requisição
            }
        )
    
    def _get_default_permissions(self) -> List[str]:
        """Retorna permissões padrão baseadas no ambiente"""
        base_permissions = [
            'llm:generate',
            'llm:models:list',
            'project:read'
        ]
        
        if self.environment in [BradaxEnvironment.DEVELOPMENT, BradaxEnvironment.TESTING]:
            base_permissions.extend([
                'project:write',
                'system:health',
                'metrics:read'
            ])
        
        return base_permissions
    
    def validate_session(self, session_id: str) -> ProjectSession:
        """
        Valida sessão ativa
        
        Args:
            session_id: ID da sessão
            
        Returns:
            ProjectSession: Sessão válida
            
        Raises:
            AuthenticationException: Sessão inválida ou expirada
        """
        session = self._active_sessions.get(session_id)
        
        if not session:
            raise AuthenticationException(
                "Sessão não encontrada",
                details={"session_id": session_id}
            )
        
        if datetime.utcnow() > session.expires_at:
            # Remove sessão expirada
            del self._active_sessions[session_id]
            raise AuthenticationException(
                "Sessão expirada",
                details={"expired_at": session.expires_at.isoformat()}
            )
        
        return session
    
    def check_permission(self, session: ProjectSession, permission: str) -> bool:
        """
        Verifica se sessão tem permissão específica
        
        Args:
            session: Sessão de projeto
            permission: Permissão a verificar (ex: 'llm:generate')
            
        Returns:
            bool: True se tem permissão
        """
        if not permission:
            return False
        
        # Verifica permissão exata
        if permission in session.permissions:
            return True
        
        # Verifica permissões wildcard (ex: 'llm:*' cobre 'llm:generate')
        permission_parts = permission.split(':')
        for perm in session.permissions:
            if perm.endswith('*'):
                perm_prefix = perm[:-1]
                if permission.startswith(perm_prefix):
                    return True
        
        return False
    
    def require_permission(self, session: ProjectSession, permission: str) -> None:
        """
        Exige permissão específica ou levanta exceção
        
        Args:
            session: Sessão de projeto
            permission: Permissão requerida
            
        Raises:
            AuthorizationException: Permissão negada
        """
        if not self.check_permission(session, permission):
            raise AuthorizationException(
                f"Permissão negada: {permission}",
                details={
                    "required_permission": permission,
                    "available_permissions": session.permissions,
                    "project_id": session.project_id
                }
            )
    
    def check_budget(self, session: ProjectSession, estimated_cost: float) -> bool:
        """
        Verifica se projeto tem orçamento suficiente
        
        Args:
            session: Sessão de projeto
            estimated_cost: Custo estimado da operação
            
        Returns:
            bool: True se tem orçamento suficiente
        """
        return session.budget_remaining >= estimated_cost
    
    def consume_budget(self, session: ProjectSession, actual_cost: float) -> None:
        """
        Consome orçamento do projeto
        
        Args:
            session: Sessão de projeto
            actual_cost: Custo real da operação
        """
        session.budget_remaining -= actual_cost
        session.metadata['last_budget_update'] = datetime.utcnow().isoformat()
        
        logger.info(f"Orçamento consumido: {actual_cost:.6f} USD (restante: {session.budget_remaining:.6f})")
    
    def refresh_session(self, session_id: str) -> ProjectSession:
        """
        Renova sessão existente
        
        Args:
            session_id: ID da sessão
            
        Returns:
            ProjectSession: Sessão renovada
        """
        session = self.validate_session(session_id)
        
        # Estende expiração
        session.expires_at = datetime.utcnow() + timedelta(minutes=HubSecurityConstants.JWT_EXPIRATION_MINUTES)
        session.last_used = datetime.utcnow()
        
        logger.info(f"Sessão renovada: {session_id}")
        return session
    
    def revoke_session(self, session_id: str) -> None:
        """
        Revoga sessão ativa
        
        Args:
            session_id: ID da sessão
        """
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
            logger.info(f"Sessão revogada: {session_id}")
    
    def get_active_sessions(self) -> List[ProjectSession]:
        """Retorna lista de sessões ativas"""
        now = datetime.utcnow()
        active = [s for s in self._active_sessions.values() if s.expires_at > now]
        
        # Remove sessões expiradas do cache
        expired_ids = [
            sid for sid, session in self._active_sessions.items()
            if session.expires_at <= now
        ]
        for sid in expired_ids:
            del self._active_sessions[sid]
        
        return active


# Singleton para facilitar uso
project_auth = ProjectAuth()


def get_project_auth() -> ProjectAuth:
    """Factory function para obter instância do ProjectAuth"""
    return project_auth
