"""
Sistema de Exceções Bradax Broker - Enterprise Grade

Sistema hierárquico de exceções customizadas para o Bradax Broker,
eliminando hardcode e oferecendo tratamento robusto de erros.

Arquitetura:
- BradaxException: Base para todas as exceções
- BradaxBusinessException: Regras de negócio
- BradaxTechnicalException: Problemas técnicos
- BradaxSecurityException: Problemas de segurança
- BradaxValidationException: Problemas de validação
"""

import traceback
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime
import uuid


class ErrorSeverity(Enum):
    """Níveis de severidade de erro"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categorias de erro"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    BUSINESS_RULE = "business_rule"
    TECHNICAL = "technical"
    EXTERNAL_API = "external_api"
    CONFIGURATION = "configuration"
    DATA_ACCESS = "data_access"
    NETWORK = "network"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"


class BradaxException(Exception):
    """
    Exceção base para todas as exceções do Bradax Broker
    
    Fornece estrutura padronizada para tratamento de erros
    com contexto rico e rastreabilidade completa.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
        user_message: Optional[str] = None,
        resolution_steps: Optional[List[str]] = None
    ):
        self.error_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat()
        self.message = message
        self.error_code = error_code
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.original_exception = original_exception
        self.user_message = user_message or self._generate_user_message()
        self.resolution_steps = resolution_steps or []
        self.stack_trace = traceback.format_exc() if original_exception else None
        
        super().__init__(self.message)
    
    def _generate_user_message(self) -> str:
        """Gera mensagem amigável para o usuário"""
        category_messages = {
            ErrorCategory.AUTHENTICATION: "Erro de autenticação. Verifique suas credenciais.",
            ErrorCategory.AUTHORIZATION: "Acesso negado. Você não tem permissão para esta operação.",
            ErrorCategory.VALIDATION: "Dados inválidos fornecidos.",
            ErrorCategory.BUSINESS_RULE: "Operação violou regra de negócio.",
            ErrorCategory.TECHNICAL: "Erro técnico interno.",
            ErrorCategory.EXTERNAL_API: "Falha na comunicação com serviço externo.",
            ErrorCategory.CONFIGURATION: "Erro de configuração do sistema.",
            ErrorCategory.DATA_ACCESS: "Erro no acesso aos dados.",
            ErrorCategory.NETWORK: "Erro de conectividade de rede.",
            ErrorCategory.TIMEOUT: "Operação expirou. Tente novamente.",
            ErrorCategory.RATE_LIMIT: "Limite de requisições excedido."
        }
        return category_messages.get(self.category, "Erro interno do sistema.")
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte exceção para dicionário estruturado"""
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp,
            "error_code": self.error_code,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "user_message": self.user_message,
            "details": self.details,
            "resolution_steps": self.resolution_steps,
            "stack_trace": self.stack_trace
        }
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.category.value.upper()}: {self.message}"


class BradaxBusinessException(BradaxException):
    """Exceções relacionadas a regras de negócio"""
    
    def __init__(
        self,
        message: str,
        business_rule: str,
        violated_constraint: str,
        current_value: Any = None,
        expected_value: Any = None,
        **kwargs
    ):
        error_code = f"BIZ_{business_rule.upper()}"
        details = {
            "business_rule": business_rule,
            "violated_constraint": violated_constraint,
            "current_value": current_value,
            "expected_value": expected_value
        }
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.BUSINESS_RULE,
            details=details,
            **kwargs
        )


class BradaxValidationException(BradaxException):
    """Exceções relacionadas a validação de dados"""
    
    def __init__(
        self,
        message: str,
        field_name: str,
        invalid_value: Any = None,
        validation_rule: str = None,
        field_errors: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        error_code = f"VAL_{field_name.upper()}"
        details = {
            "field_name": field_name,
            "invalid_value": invalid_value,
            "validation_rule": validation_rule,
            "field_errors": field_errors or {}
        }
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.VALIDATION,
            details=details,
            **kwargs
        )


class BradaxAuthenticationException(BradaxException):
    """Exceções relacionadas a autenticação"""
    
    def __init__(
        self,
        message: str,
        auth_method: str,
        project_id: Optional[str] = None,
        **kwargs
    ):
        error_code = f"AUTH_{auth_method.upper()}"
        details = {
            "auth_method": auth_method,
            "project_id": project_id
        }
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            details=details,
            **kwargs
        )


class BradaxAuthorizationException(BradaxException):
    """Exceções relacionadas a autorização"""
    
    def __init__(
        self,
        message: str,
        required_permission: str,
        resource: str,
        project_id: Optional[str] = None,
        **kwargs
    ):
        error_code = f"AUTHZ_{required_permission.upper()}"
        details = {
            "required_permission": required_permission,
            "resource": resource,
            "project_id": project_id
        }
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.HIGH,
            details=details,
            **kwargs
        )


class BradaxTechnicalException(BradaxException):
    """Exceções relacionadas a problemas técnicos"""
    
    def __init__(
        self,
        message: str,
        component: str,
        operation: str,
        **kwargs
    ):
        error_code = f"TECH_{component.upper()}_{operation.upper()}"
        details = {
            "component": component,
            "operation": operation
        }
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.TECHNICAL,
            details=details,
            **kwargs
        )


class BradaxExternalAPIException(BradaxException):
    """Exceções relacionadas a APIs externas"""
    
    def __init__(
        self,
        message: str,
        api_name: str,
        endpoint: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        **kwargs
    ):
        error_code = f"EXT_{api_name.upper()}"
        details = {
            "api_name": api_name,
            "endpoint": endpoint,
            "status_code": status_code,
            "response_body": response_body
        }
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.EXTERNAL_API,
            details=details,
            **kwargs
        )


class BradaxConfigurationException(BradaxException):
    """Exceções relacionadas a configuração"""
    
    def __init__(
        self,
        message: str,
        config_key: str,
        config_section: str = None,
        **kwargs
    ):
        error_code = f"CONFIG_{config_key.upper()}"
        details = {
            "config_key": config_key,
            "config_section": config_section
        }
        resolution_steps = [
            f"Verificar se a variável de ambiente {config_key} está definida",
            "Verificar se o valor está no formato correto",
            "Consultar documentação para valores válidos"
        ]
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.CONFIGURATION,
            details=details,
            resolution_steps=resolution_steps,
            **kwargs
        )


class BradaxDataAccessException(BradaxException):
    """Exceções relacionadas a acesso de dados"""
    
    def __init__(
        self,
        message: str,
        storage_type: str,
        operation: str,
        resource_id: Optional[str] = None,
        **kwargs
    ):
        error_code = f"DATA_{storage_type.upper()}_{operation.upper()}"
        details = {
            "storage_type": storage_type,
            "operation": operation,
            "resource_id": resource_id
        }
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.DATA_ACCESS,
            details=details,
            **kwargs
        )


class BradaxNetworkException(BradaxException):
    """Exceções relacionadas a problemas de rede"""
    
    def __init__(
        self,
        message: str,
        host: str,
        port: Optional[int] = None,
        protocol: str = "HTTP",
        **kwargs
    ):
        error_code = f"NET_{protocol.upper()}"
        details = {
            "host": host,
            "port": port,
            "protocol": protocol
        }
        resolution_steps = [
            "Verificar conectividade de rede",
            "Validar se o serviço está disponível",
            "Verificar configurações de firewall",
            "Tentar novamente após alguns minutos"
        ]
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.NETWORK,
            details=details,
            resolution_steps=resolution_steps,
            **kwargs
        )


class BradaxTimeoutException(BradaxException):
    """Exceções relacionadas a timeout"""
    
    def __init__(
        self,
        message: str,
        operation: str,
        timeout_seconds: int,
        elapsed_seconds: Optional[float] = None,
        **kwargs
    ):
        error_code = f"TIMEOUT_{operation.upper()}"
        details = {
            "operation": operation,
            "timeout_seconds": timeout_seconds,
            "elapsed_seconds": elapsed_seconds
        }
        resolution_steps = [
            "Tentar novamente",
            "Verificar se há problemas de conectividade",
            "Considerar aumentar o timeout se necessário"
        ]
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.TIMEOUT,
            details=details,
            resolution_steps=resolution_steps,
            **kwargs
        )


class BradaxRateLimitException(BradaxException):
    """Exceções relacionadas a limite de taxa"""
    
    def __init__(
        self,
        message: str,
        limit_type: str,
        current_count: int,
        limit_count: int,
        reset_time: Optional[datetime] = None,
        **kwargs
    ):
        error_code = f"RATE_{limit_type.upper()}"
        details = {
            "limit_type": limit_type,
            "current_count": current_count,
            "limit_count": limit_count,
            "reset_time": reset_time.isoformat() if reset_time else None
        }
        resolution_steps = [
            "Reduzir frequência de requisições",
            f"Aguardar até {reset_time.isoformat() if reset_time else 'próximo período'}",
            "Implementar exponential backoff"
        ]
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.LOW,
            details=details,
            resolution_steps=resolution_steps,
            **kwargs
        )


# Factory functions para facilitar uso
def create_validation_error(field_name: str, value: Any, rule: str) -> BradaxValidationException:
    """Cria exceção de validação padronizada"""
    return BradaxValidationException(
        message=f"Campo '{field_name}' com valor '{value}' violou regra: {rule}",
        field_name=field_name,
        invalid_value=value,
        validation_rule=rule
    )


def create_auth_error(project_id: str, reason: str = "Invalid credentials") -> BradaxAuthenticationException:
    """Cria exceção de autenticação padronizada"""
    return BradaxAuthenticationException(
        message=f"Authentication failed for project {project_id}: {reason}",
        auth_method="project_token",
        project_id=project_id
    )


def create_business_error(rule: str, constraint: str, current: Any, expected: Any) -> BradaxBusinessException:
    """Cria exceção de regra de negócio padronizada"""
    return BradaxBusinessException(
        message=f"Business rule '{rule}' violated: {constraint}",
        business_rule=rule,
        violated_constraint=constraint,
        current_value=current,
        expected_value=expected
    )


def create_external_api_error(api_name: str, endpoint: str, status_code: int, error_msg: str) -> BradaxExternalAPIException:
    """Cria exceção de API externa padronizada"""
    return BradaxExternalAPIException(
        message=f"External API {api_name} error: {error_msg}",
        api_name=api_name,
        endpoint=endpoint,
        status_code=status_code,
        response_body=error_msg
    )


# Utilitários para análise de exceções
def is_retryable_error(exception: BradaxException) -> bool:
    """Verifica se a exceção permite retry"""
    retryable_categories = {
        ErrorCategory.NETWORK,
        ErrorCategory.TIMEOUT,
        ErrorCategory.EXTERNAL_API
    }
    return exception.category in retryable_categories


def get_http_status_code(exception: BradaxException) -> int:
    """Mapeia exceção para código HTTP apropriado"""
    status_map = {
        ErrorCategory.AUTHENTICATION: 401,
        ErrorCategory.AUTHORIZATION: 403,
        ErrorCategory.VALIDATION: 400,
        ErrorCategory.BUSINESS_RULE: 409,
        ErrorCategory.RATE_LIMIT: 429,
        ErrorCategory.EXTERNAL_API: 502,
        ErrorCategory.TIMEOUT: 504,
        ErrorCategory.CONFIGURATION: 500,
        ErrorCategory.DATA_ACCESS: 500,
        ErrorCategory.TECHNICAL: 500,
        ErrorCategory.NETWORK: 503
    }
    return status_map.get(exception.category, 500)


# ============================================================================
#                            ALIASES PARA COMPATIBILIDADE
# ============================================================================

# Aliases para manter compatibilidade com código existente
AuthenticationException = BradaxAuthenticationException
AuthorizationException = BradaxAuthorizationException
ValidationException = BradaxValidationException
BusinessException = BradaxBusinessException
TechnicalException = BradaxTechnicalException
ExternalAPIException = BradaxExternalAPIException
ConfigurationException = BradaxConfigurationException
DataAccessException = BradaxDataAccessException
NetworkException = BradaxNetworkException
TimeoutException = BradaxTimeoutException
RateLimitException = BradaxRateLimitException


# ============================================================================
#                                EXPORTS
# ============================================================================

__all__ = [
    # Classes base
    'BradaxException',
    'ErrorSeverity',
    'ErrorCategory',
    
    # Exceções específicas
    'BradaxBusinessException',
    'BradaxValidationException', 
    'BradaxAuthenticationException',
    'BradaxAuthorizationException',
    'BradaxTechnicalException',
    'BradaxExternalAPIException',
    'BradaxConfigurationException',
    'BradaxDataAccessException',
    'BradaxNetworkException',
    'BradaxTimeoutException',
    'BradaxRateLimitException',
    
    # Aliases para compatibilidade
    'AuthenticationException',
    'AuthorizationException',
    'ValidationException',
    'BusinessException',
    'TechnicalException',
    'ExternalAPIException',
    'ConfigurationException',
    'DataAccessException',
    'NetworkException',
    'TimeoutException',
    'RateLimitException',
    
    # Funções utilitárias
    'create_authentication_error',
    'create_authorization_error',
    'create_validation_error',
    'create_business_error',
    'create_technical_error',
    'create_external_api_error',
    'create_configuration_error',
    'create_data_access_error',
    'create_network_error',
    'create_timeout_error',
    'create_rate_limit_error',
    'is_retryable_error',
    'get_http_status_code'
]
