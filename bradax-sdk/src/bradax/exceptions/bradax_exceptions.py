"""
Exceções customizadas do bradax SDK

Hierarquia profissional de exceções para diferentes cenários de erro.
"""

from typing import Optional, Dict, Any

# Usar constants internas do SDK
from ..constants import SDKValidationConstants


class BradaxException(Exception):
    """
    Exceção base para todas as exceções do bradax SDK.
    
    Fornece funcionalidade comum para tratamento de erros
    e logging estruturado.
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Inicializa a exceção bradax.
        
        Args:
            message: Mensagem de erro humana
            error_code: Código de erro para sistemas
            context: Contexto adicional para debug
            cause: Exceção original que causou este erro
        """
        # Truncar mensagem se muito longa
        max_length = SDKValidationConstants.MAX_RESPONSE_LENGTH
        if len(message) > max_length:
            message = message[:max_length] + "..."
            
        super().__init__(message)
        self.error_code = error_code or "BRADAX_GENERIC_ERROR"
        self.context = context or {}
        self.cause = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte a exceção para dicionário para logging/serialização."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": str(self),
            "context": self.context,
            "cause": str(self.cause) if self.cause else None
        }


class BradaxAuthenticationError(BradaxException):
    """
    Exceção para erros de autenticação.
    
    Levantada quando:
    - Credenciais inválidas
    - Token expirado
    - Permissões insuficientes
    """
    
    def __init__(
        self, 
        message: str = "Erro de autenticação", 
        error_code: str = "BRADAX_AUTH_ERROR",
        **kwargs
    ):
        super().__init__(message, error_code, **kwargs)


class BradaxValidationError(BradaxException):
    """
    Exceção para erros de validação de dados.
    
    Levantada quando:
    - Parâmetros inválidos
    - Formato de dados incorreto
    - Violação de regras de negócio
    """
    
    def __init__(
        self, 
        message: str = "Erro de validação", 
        error_code: str = "BRADAX_VALIDATION_ERROR",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if field:
            context['invalid_field'] = field
        if value is not None:
            context['invalid_value'] = str(value)
        kwargs['context'] = context
        
        super().__init__(message, error_code, **kwargs)


class BradaxNetworkError(BradaxException):
    """
    Exceção para erros de rede e comunicação.
    
    Levantada quando:
    - Timeout de conexão
    - Broker indisponível
    - Erros HTTP
    """
    
    def __init__(
        self, 
        message: str = "Erro de rede", 
        error_code: str = "BRADAX_NETWORK_ERROR",
        status_code: Optional[int] = None,
        url: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if status_code:
            context['http_status_code'] = status_code
        if url:
            context['target_url'] = url
        kwargs['context'] = context
        
        super().__init__(message, error_code, **kwargs)


class BradaxConfigurationError(BradaxException):
    """
    Exceção para erros de configuração.
    
    Levantada quando:
    - Configuração inválida
    - Variáveis de ambiente faltando
    - Parâmetros obrigatórios ausentes
    """
    
    def __init__(
        self, 
        message: str = "Erro de configuração", 
        error_code: str = "BRADAX_CONFIG_ERROR",
        **kwargs
    ):
        super().__init__(message, error_code, **kwargs)


class BradaxRateLimitError(BradaxException):
    """
    Exceção para erros de rate limiting.
    
    Levantada quando:
    - Limite de requisições excedido
    - Cota de tokens esgotada
    - Throttling ativo
    """
    
    def __init__(
        self, 
        message: str = "Rate limit excedido", 
        error_code: str = "BRADAX_RATE_LIMIT_ERROR",
        retry_after: Optional[int] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if retry_after:
            context['retry_after_seconds'] = retry_after
        kwargs['context'] = context
        
        super().__init__(message, error_code, **kwargs)


class BradaxComplianceError(BradaxException):
    """
    Exceção para violações de compliance.
    
    Levantada quando:
    - Conteúdo inadequado detectado
    - Violação de políticas
    - Falha em guardrails
    """
    
    def __init__(
        self, 
        message: str = "Violação de compliance", 
        error_code: str = "BRADAX_COMPLIANCE_ERROR",
        violation_type: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if violation_type:
            context['violation_type'] = violation_type
        kwargs['context'] = context
        
        super().__init__(message, error_code, **kwargs)


# Mapeamento de status HTTP para exceções
HTTP_STATUS_TO_EXCEPTION = {
    401: BradaxAuthenticationError,
    403: BradaxAuthenticationError,
    429: BradaxRateLimitError,
    400: BradaxValidationError,
    422: BradaxValidationError,
    500: BradaxNetworkError,
    502: BradaxNetworkError,
    503: BradaxNetworkError,
    504: BradaxNetworkError,
}


def create_exception_from_http_status(
    status_code: int,
    message: str,
    url: Optional[str] = None,
    response_body: Optional[str] = None
) -> BradaxException:
    """
    Cria exceção apropriada baseada no status HTTP.
    
    Args:
        status_code: Código de status HTTP
        message: Mensagem de erro
        url: URL que causou o erro
        response_body: Corpo da resposta de erro
        
    Returns:
        Exceção apropriada para o status code
    """
    exception_class = HTTP_STATUS_TO_EXCEPTION.get(status_code, BradaxNetworkError)
    
    context = {
        'http_status_code': status_code,
        'response_body': response_body[:SDKValidationConstants.MAX_RESPONSE_LENGTH] if response_body else None
    }
    
    if url:
        context['target_url'] = url
    
    return exception_class(
        message=message,
        context=context
    )


# Aliases para compatibilidade com código legado
BradaxError = BradaxException  # Alias principal
BradaxAPIError = BradaxException  # Alias adicional


# Exportações públicas
__all__ = [
    'BradaxException',
    'BradaxError',  # Alias
    'BradaxAPIError',  # Alias  
    'BradaxAuthenticationError',
    'BradaxValidationError',
    'BradaxNetworkError',
    'BradaxConfigurationError',
    'BradaxRateLimitError',
    'BradaxComplianceError',
    'create_from_http_error'
]
