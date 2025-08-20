"""
Project Authentication Module

Implementa autenticação corporativa baseada em ProjectAuth
alinhada com a estratégia de segurança bradax.

Sistema de autenticação empresarial sem hardcode/fallbacks.
"""

import logging
import os
import hmac
import hashlib
import base64
import secrets
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone
import jwt  # PyJWT
from pydantic import BaseModel, Field

from ..constants import HubSecurityConstants, get_hub_environment, BradaxEnvironment
from ..exceptions import (
    AuthenticationException,  # alias para BradaxAuthenticationException
    AuthorizationException,
    ValidationException,
    ConfigurationException
)
from .project_storage import get_project_storage

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

        # Storage real de projetos - SEM CACHE LOCAL
        self.storage = get_project_storage()

        # Cache de sessões ativas (em produção usar Redis)
        self._active_sessions: Dict[str, ProjectSession] = {}

        logger.info(f"ProjectAuth inicializado para ambiente: {self.environment.value}")
        logger.info(f"Storage de projetos: {len(self.storage.list_active_projects())} projetos ativos")

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
        """
        Valida formato da API key - FALHA EXPLICITAMENTE

        Raises:
            ValidationException: API key inválida ou mal formada
        """
        if not api_key or not isinstance(api_key, str):
            raise ValidationException(
                "API key deve ser string não vazia",
                details={"provided_type": type(api_key).__name__}
            )

        if not api_key.startswith(HubSecurityConstants.API_KEY_PREFIX):
            raise ValidationException(
                f"API key deve começar com '{HubSecurityConstants.API_KEY_PREFIX}'",
                details={"provided_prefix": api_key[:20] + "..." if len(api_key) > 20 else api_key}
            )

        # Valida comprimento mínimo
        min_length = len(HubSecurityConstants.API_KEY_PREFIX) + 20
        if len(api_key) < min_length:
            raise ValidationException(
                f"API key muito curta (mínimo: {min_length} caracteres)",
                details={"provided_length": len(api_key), "minimum_required": min_length}
            )

        # Valida padrão obrigatório (prefixo + componentes separados por _)
        parts = api_key[len(HubSecurityConstants.API_KEY_PREFIX):].split('_')
        if len(parts) < 4:
            raise ValidationException(
                "API key deve ter 4 componentes separados por underscore",
                details={"found_components": len(parts), "required_components": 4}
            )

        return True

    # ----------------------------------------------------------------------------------
    # Autenticação (versão síncrona interna)
    # ----------------------------------------------------------------------------------
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
        # Validação rigorosa - SEM FALLBACKS SILENCIOSOS
        try:
            self.validate_api_key(api_key)
        except ValidationException as e:
            raise AuthenticationException(
                f"API key inválida: {e.message}",
                auth_method="api_key",
                details=e.details
            )

        if not project_id:
            raise ValidationException(
                "project_id é obrigatório",
                field_name="project_id",
                invalid_value=project_id,
                validation_rule="required"
            )

        # Extrair informações da API key
        try:
            project_info = self._parse_api_key(api_key, expected_project_id=project_id)
        except Exception as e:
            raise AuthenticationException(
                "Falha ao analisar API key",
                auth_method="api_key",
                details={"error": str(e)}
            )

        # Validar correspondência de projeto
        if project_info.get('project_id') != project_id:
            raise AuthenticationException(
                "API key não corresponde ao project_id fornecido",
                auth_method="api_key",
                details={
                    "expected_project": project_id,
                    "key_project": project_info.get('project_id')
                }
            )

        # VALIDAÇÃO REAL: Verificar se projeto existe e está ativo no storage
        try:
            project_data = self.storage.get_project(project_id)
        except ValidationException as e:
            raise AuthenticationException(
                f"Projeto não encontrado ou inativo: {e.message}",
                auth_method="api_key",
                details=e.details
            )

        # VALIDAÇÃO REAL: Verificar hash da API key
        if not self.storage.verify_api_key_hash(project_id, api_key):
            raise AuthenticationException(
                "API key não corresponde ao hash armazenado",
                auth_method="api_key",
                details={"project_id": project_id}
            )

        # Criar sessão com dados reais do storage
        session = self._create_session(project_info, api_key, project_data)

        # Cache da sessão
        self._active_sessions[session.session_id] = session

        logger.info(f"Projeto autenticado: {project_id} (sessão: {session.session_id})")
        return session

    # ----------------------------------------------------------------------------------
    # Facades assíncronas para compatibilidade com rotas FastAPI (rotas usam 'await')
    # ----------------------------------------------------------------------------------
    async def authenticate_project_async(self, project_id: str, api_key: str) -> ProjectSession:
        """Wrapper assíncrono para manter compatibilidade com rotas que usam await."""
        return self.authenticate_project(api_key=api_key, project_id=project_id)

    # ----------------------------------------------------------------------------------
    # JWT Access Tokens
    # ----------------------------------------------------------------------------------
    async def generate_access_token(self, project: ProjectSession, scopes: Optional[List[str]] = None) -> str:
        """Gera JWT corporativo derivando segredo por projeto (SEM FALLBACK)."""
        if not HubSecurityConstants.JWT_SECRET_KEY:
            raise ConfigurationException(
                "JWT_SECRET_KEY não configurado",
                config_key="BRADAX_JWT_SECRET"
            )

        now = datetime.now(timezone.utc)
        exp = now + timedelta(minutes=HubSecurityConstants.JWT_EXPIRATION_MINUTES)
        payload = {
            "sub": project.project_id,
            "project_id": project.project_id,
            "organization": project.organization_id,
            "scopes": scopes or project.permissions,
            "env": project.environment,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        # Deriva segredo específico do projeto (versão v1)
        derived_secret, kid = self._derive_project_secret(project.project_id, version="v1")
        headers = {"kid": kid}
        try:
            token = jwt.encode(
                payload,
                derived_secret,
                algorithm=HubSecurityConstants.JWT_ALGORITHM,
                headers=headers
            )
        except Exception as e:
            raise AuthenticationException(
                "Falha ao gerar token JWT",
                auth_method="jwt_issue",
                project_id=project.project_id,
                details={"error": str(e)}
            )
        logger.info(
            "jwt_issue",
            extra={
                "event": "jwt_issue",
                "project_id": project.project_id,
                "kid": kid,
                "signing_strategy": "derived_v1",
                "scopes_count": len(payload.get("scopes", []))
            }
        )
        return token

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Valida JWT derivado por projeto (sem fallback)."""
        if not HubSecurityConstants.JWT_SECRET_KEY:
            raise ConfigurationException(
                "JWT_SECRET_KEY não configurado",
                config_key="BRADAX_JWT_SECRET"
            )
        if not token or not isinstance(token, str):
            raise ValidationException(
                "Token JWT inválido (tipo ou vazio)",
                field_name="jwt_token",
                invalid_value=token,
                validation_rule="required_non_empty_string"
            )
        try:
            unverified_header = jwt.get_unverified_header(token)
        except Exception as e:
            raise AuthenticationException(
                "Header JWT inválido",
                auth_method="jwt_header",
                details={"error": str(e)}
            )
        kid = unverified_header.get("kid")
        if not kid:
            raise AuthenticationException(
                "kid ausente no header JWT",
                auth_method="jwt_header",
                details={"header_keys": list(unverified_header.keys())}
            )
        # Formato esperado: p:<project_id>:v1
        if not kid.startswith("p:") or kid.count(":") != 2:
            raise AuthenticationException(
                "Formato de kid inválido",
                auth_method="jwt_header",
                details={"kid": kid, "expected_pattern": "p:<project_id>:v1"}
            )
        _, project_id, version = kid.split(":", 2)
        if version != "v1":
            raise AuthenticationException(
                "Versão de token não suportada",
                auth_method="jwt_header",
                project_id=project_id,
                details={"version": version}
            )
        derived_secret, _ = self._derive_project_secret(project_id, version=version)
        try:
            payload = jwt.decode(
                token,
                derived_secret,
                algorithms=[HubSecurityConstants.JWT_ALGORITHM],
                options={"require": ["exp", "sub", "project_id"], "verify_exp": True},
            )
        except jwt.ExpiredSignatureError as e:
            raise AuthenticationException(
                "Token expirado",
                auth_method="jwt_validation",
                project_id=project_id,
                details={"error": str(e)}
            )
        except jwt.InvalidTokenError as e:
            raise AuthenticationException(
                "Token inválido",
                auth_method="jwt_validation",
                project_id=project_id,
                details={"error": str(e)}
            )
        # Consistência payload vs header
        if payload.get("project_id") != project_id:
            raise AuthenticationException(
                "project_id do payload diverge do header",
                auth_method="jwt_validation",
                project_id=project_id,
                details={"payload_project_id": payload.get("project_id")}
            )
        # Verifica se projeto existe e está ativo
        try:
            self.storage.get_project(project_id)
        except ValidationException as e:
            raise AuthenticationException(
                "Projeto inexistente ou inativo para token",
                auth_method="jwt_validation",
                project_id=project_id,
                details=e.details
            )
        logger.info(
            "jwt_validate",
            extra={
                "event": "jwt_validate",
                "project_id": project_id,
                "kid": kid,
                "signing_strategy": "derived_v1"
            }
        )
        return payload

    # ------------------------------------------------------------------
    # Segredo derivado por projeto (v1)
    # ------------------------------------------------------------------
    def _derive_project_secret(self, project_id: str, version: str = "v1") -> Tuple[str, str]:
        """Deriva segredo específico do projeto usando HMAC(master, namespace+project_id)."""
        if not project_id or len(project_id) < 3:
            raise ValidationException(
                "project_id inválido para derivação",
                field_name="project_id",
                invalid_value=project_id,
                validation_rule="min_length_3"
            )
        if not HubSecurityConstants.JWT_SECRET_KEY:
            raise ConfigurationException(
                "JWT_SECRET_KEY não configurado",
                config_key="BRADAX_JWT_SECRET"
            )
        namespace = f"bradax-jwt-{version}::".encode()
        key_bytes = HubSecurityConstants.JWT_SECRET_KEY.encode()
        msg = namespace + project_id.lower().encode()
        digest = hmac.new(key_bytes, msg, hashlib.sha256).digest()
        # urlsafe base64 sem padding para reduzir tamanho
        b64 = base64.urlsafe_b64encode(digest).decode().rstrip('=')
        kid = f"p:{project_id}:" + version
        return b64, kid

    def _parse_api_key(self, api_key: str, expected_project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Extrai informações da API key - FALHA EXPLICITAMENTE

        Raises:
            ValidationException: API key mal formada
        """
        # Remove prefixo e divide componentes crus
        key_body = api_key[len(HubSecurityConstants.API_KEY_PREFIX):]
        parts = key_body.split('_')

    # Estrutura (restrita para robustez):
    # bradax_<project_id_com_underscores>_<organization_id_sem_underscore>_<random_part_pode_ter_underscores>_<timestamp>
    # Motivo: Ambiguidade quando org_id possui underscore; simplificamos exigindo org_id sem '_'.
    # Regras:
    #  - timestamp = último token numérico
    #  - organization_id = token único (sem underscore), não 'default'
    #  - project_id = junção dos tokens iniciais até antes de organization_id
    #  - random_part = tokens entre organization_id e timestamp, unidos por '_'
    #  - Quando expected_project_id fornecido, ele guia o recorte exato.
        if len(parts) < 4:
            raise ValidationException(
                "API key com estrutura inválida",
                details={"found_parts": len(parts), "required_parts": 4}
            )

        timestamp_token = parts[-1]
        if not timestamp_token.isdigit():
            raise ValidationException(
                "Timestamp final inválido na API key",
                details={"timestamp": timestamp_token}
            )

        # Se expected_project_id fornecido, tentar correspondência direta
        if expected_project_id:
            expected_tokens = expected_project_id.split('_')
            if parts[:len(expected_tokens)] == expected_tokens and len(parts) > len(expected_tokens)+2:
                org_token = parts[len(expected_tokens)]
                if 'default' == org_token:
                    raise ValidationException(
                        "organization_id 'default' não é permitido",
                        details={"invalid_org_id": org_token}
                    )
                if '_' in org_token:
                    raise ValidationException(
                        "organization_id não deve conter underscore (formato estrito)",
                        details={"organization_id": org_token}
                    )
                random_tokens = parts[len(expected_tokens)+1:-1]
                if not random_tokens:
                    raise ValidationException(
                        "random_part ausente",
                        details={"parts": parts}
                    )
                return {
                    'project_id': expected_project_id,
                    'organization_id': org_token,
                    'random_part': '_'.join(random_tokens),
                    'timestamp': timestamp_token
                }

        # Fallback heurístico (sem expected) mantendo restrição org sem underscore
        for org_index in range(1, len(parts) - 2):
            project_tokens = parts[:org_index]
            org_token = parts[org_index]
            random_tokens = parts[org_index + 1:-1]
            if not project_tokens or not random_tokens:
                continue
            if org_token == 'default' or '_' in org_token:
                continue
            project_id_candidate = '_'.join(project_tokens)
            if len(project_id_candidate) < 3:
                continue
            return {
                'project_id': project_id_candidate,
                'organization_id': org_token,
                'random_part': '_'.join(random_tokens),
                'timestamp': timestamp_token
            }

        raise ValidationException(
            "Falha ao decompor API key (heurística)",
            field_name="api_key_parsing",
            invalid_value=None,
            validation_rule="api_key_decomposition_failed"
        )

    def _create_session(self, project_info: Dict[str, Any], api_key: str, project_data: Dict[str, Any]) -> ProjectSession:
        """
        Cria nova sessão de projeto com dados REAIS do storage

        Args:
            project_info: Dados extraídos da API key
            api_key: API key original
            project_data: Dados completos do projeto do storage

        Returns:
            ProjectSession: Sessão com dados reais

        Raises:
            ValidationException: Dados de projeto inválidos
        """
        session_id = secrets.token_hex(16)
        expires_at = datetime.utcnow() + timedelta(minutes=HubSecurityConstants.JWT_EXPIRATION_MINUTES)

        # Permissões REAIS baseadas no projeto
        permissions = self.storage.get_project_permissions(project_info['project_id'])

        # BUDGET REAL do storage - SEM FALLBACKS
        try:
            budget_remaining = self.storage.get_project_budget(project_info['project_id'])
        except ValidationException as e:
            raise ValidationException(
                f"Projeto sem orçamento válido configurado: {e.message}",
                field_name="project_budget",
                invalid_value=None,
                validation_rule="budget_required"
            )

        return ProjectSession(
            project_id=project_info['project_id'],
            organization_id=project_info['organization_id'],  # Já validado como não-'default'
            permissions=permissions,
            budget_remaining=budget_remaining,
            environment=self.environment.value,
            session_id=session_id,
            expires_at=expires_at,
            metadata={
                'created_from_api_key': api_key[:20] + "...",
                'project_name': project_data.get('name', 'UNKNOWN'),
                'project_owner': project_data.get('owner', 'UNKNOWN'),
                'guardrails_level': project_data.get('config', {}).get('guardrails', {}).get('level', 'NONE'),
                'created_at': datetime.utcnow().isoformat()
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
                auth_method="session",
                details={"session_id": session_id}
            )

        if datetime.utcnow() > session.expires_at:
            # Remove sessão expirada
            del self._active_sessions[session_id]
            raise AuthenticationException(
                "Sessão expirada",
                auth_method="session",
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
