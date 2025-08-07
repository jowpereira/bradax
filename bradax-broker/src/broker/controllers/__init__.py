"""
Controllers Base - Padrão MVC

Define classes base e interfaces para controllers do sistema.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from fastapi import HTTPException
import logging

from broker.services.llm.service import GuardrailViolationError


class BaseController(ABC):
    """
    Classe base para todos os controllers
    
    Implementa padrões comuns de logging, tratamento de erros
    e validação de entrada.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _log_request(self, action: str, data: Optional[Dict] = None) -> None:
        """Registra entrada de requisição"""
        self.logger.info(f"Request: {action}", extra={
            "action": action,
            "data": data or {},
            "controller": self.__class__.__name__
        })
    
    def _log_response(self, action: str, success: bool, data: Optional[Dict] = None) -> None:
        """Registra saída de resposta"""
        level = logging.INFO if success else logging.ERROR
        self.logger.log(level, f"Response: {action} - {'Success' if success else 'Error'}", extra={
            "action": action,
            "success": success,
            "data": data or {},
            "controller": self.__class__.__name__
        })
    
    def _handle_error(self, error: Exception, context: str) -> HTTPException:
        """Trata erros de forma padronizada"""
        self.logger.error(f"Error in {context}: {str(error)}", extra={
            "context": context,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "controller": self.__class__.__name__
        })
        
        # Mapear tipos de erro para códigos HTTP
        if isinstance(error, GuardrailViolationError):
            return HTTPException(status_code=403, detail=str(error))
        elif isinstance(error, ValueError):
            return HTTPException(status_code=400, detail=str(error))
        elif isinstance(error, KeyError):
            return HTTPException(status_code=404, detail=f"Resource not found: {str(error)}")
        elif isinstance(error, PermissionError):
            return HTTPException(status_code=403, detail="Access denied")
        else:
            return HTTPException(status_code=500, detail="Internal server error")
    
    def _validate_required_fields(self, data: Dict, required_fields: list) -> None:
        """Valida campos obrigatórios"""
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    
    def _sanitize_input(self, data: Any) -> Any:
        """Sanitiza entrada de dados"""
        if isinstance(data, str):
            return data.strip()
        elif isinstance(data, dict):
            return {k: self._sanitize_input(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_input(item) for item in data]
        return data


class ResourceController(BaseController):
    """
    Controller base para recursos (CRUD operations)
    
    Implementa operações padrão de Create, Read, Update, Delete.
    """
    
    @abstractmethod
    def list_resources(self, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Lista recursos com filtros opcionais"""
        pass
    
    @abstractmethod
    def get_resource(self, resource_id: str) -> Dict[str, Any]:
        """Obtém recurso específico por ID"""
        pass
    
    @abstractmethod
    def create_resource(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Cria novo recurso"""
        pass
    
    @abstractmethod
    def update_resource(self, resource_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza recurso existente"""
        pass
    
    @abstractmethod
    def delete_resource(self, resource_id: str) -> Dict[str, Any]:
        """Remove recurso"""
        pass


class ServiceController(BaseController):
    """
    Controller base para serviços (operações não-CRUD)
    
    Para controllers que lidam com operações de negócio,
    integrações e processamento.
    """
    
    def __init__(self, service=None):
        super().__init__()
        self.service = service
    
    def _validate_service(self) -> None:
        """Valida se serviço está disponível"""
        if self.service is None:
            raise RuntimeError("Service not initialized")
    
    def _execute_service_operation(self, operation_name: str, *args, **kwargs) -> Any:
        """Executa operação do serviço com tratamento de erro"""
        self._validate_service()
        
        try:
            self._log_request(operation_name, {"args": args, "kwargs": kwargs})
            
            # Executar operação
            operation = getattr(self.service, operation_name)
            result = operation(*args, **kwargs)
            
            self._log_response(operation_name, True, {"result_type": type(result).__name__})
            return result
            
        except Exception as e:
            self._log_response(operation_name, False, {"error": str(e)})
            raise self._handle_error(e, f"service.{operation_name}")


class ControllerResponse:
    """
    Classe para padronizar respostas dos controllers
    """
    
    @staticmethod
    def success(data: Any = None, message: str = "Operation completed successfully") -> Dict[str, Any]:
        """Resposta de sucesso padronizada"""
        return {
            "success": True,
            "message": message,
            "data": data,
            "error": None
        }
    
    @staticmethod
    def error(error_message: str, error_code: str = "GENERIC_ERROR", data: Any = None) -> Dict[str, Any]:
        """Resposta de erro padronizada"""
        return {
            "success": False,
            "message": "Operation failed",
            "data": data,
            "error": {
                "code": error_code,
                "message": error_message
            }
        }
    
    @staticmethod
    def validation_error(field_errors: Dict[str, str]) -> Dict[str, Any]:
        """Resposta de erro de validação"""
        return {
            "success": False,
            "message": "Validation failed",
            "data": None,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input data",
                "field_errors": field_errors
            }
        }


# Decorators úteis para controllers
def require_auth(func):
    """Decorator para exigir autenticação"""
    def wrapper(*args, **kwargs):
        # Implementar lógica de autenticação
        return func(*args, **kwargs)
    return wrapper


def validate_input(schema):
    """Decorator para validar entrada com schema"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Implementar validação com schema
            return func(*args, **kwargs)
        return wrapper
    return decorator
