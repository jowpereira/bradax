"""
LLM Controller - Padrão MVC

Controller dedicado para operações de LLM seguindo padrão MVC.
Centraliza a lógica de negócio e validação para endpoints LLM.
"""

from typing import Dict, Any, Optional, List
from fastapi import HTTPException
import time
import uuid

from ..controllers import ServiceController, ControllerResponse
from ..services.llm.service import LLMService
from ..services.llm.interfaces import LLMRequest
from ..auth.project_auth import ProjectAuth


class LLMController(ServiceController):
    """
    Controller para operações de LLM
    
    Responsável por:
    - Validação de requisições
    - Orquestração de serviços
    - Aplicação de políticas de governança
    - Formatação de respostas
    """
    
    def __init__(self):
        self.llm_service = LLMService()
        self.project_auth = ProjectAuth()
        super().__init__(service=self.llm_service)
    
    def get_available_models(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtém lista de modelos disponíveis
        
        Args:
            project_id: ID do projeto (para filtros futuros)
            
        Returns:
            Resposta padronizada com lista de modelos
        """
        try:
            self._log_request("get_available_models", {"project_id": project_id})
            
            # Obter modelos do serviço
            models = self.llm_service.get_available_models()
            
            # Aplicar filtros por projeto (se necessário)
            if project_id:
                models = self._filter_models_by_project(models, project_id)
            
            # Formatar resposta
            models_data = [
                {
                    "model_id": model.model_id,
                    "name": model.name,
                    "provider": model.provider.value,
                    "max_tokens": model.max_tokens,
                    "capabilities": [cap.value for cap in model.capabilities],
                    "enabled": model.enabled
                }
                for model in models
            ]
            
            self._log_response("get_available_models", True, {"count": len(models_data)})
            
            return ControllerResponse.success(
                data={"models": models_data},
                message=f"Found {len(models_data)} available models"
            )
            
        except Exception as e:
            self._log_response("get_available_models", False, {"error": str(e)})
            raise self._handle_error(e, "get_available_models")
    
    async def invoke_generic(
        self,
        operation: str,
        model_id: str,
        payload: Dict[str, Any],
        project_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executa invocação genérica para wrapper LangChain
        
        Args:
            operation: Tipo de operação
            model_id: ID do modelo
            payload: Payload da requisição
            project_id: ID do projeto
            request_id: ID da requisição
            
        Returns:
            Resultado da operação
        """
        try:
            self._log_request("invoke_generic", {
                "operation": operation, 
                "model_id": model_id,
                "project_id": project_id,
                "request_id": request_id
            })
            
            # Validações básicas
            if not operation or not model_id:
                return self._error_response(
                    "Parâmetros 'operation' e 'model_id' são obrigatórios",
                    400
                ).dict()
            
            # Validar operação suportada
            supported_operations = ["chat", "completion", "batch", "stream", "embedding"]
            if operation not in supported_operations:
                return self._error_response(
                    f"Operação '{operation}' não suportada. Suportadas: {supported_operations}",
                    400
                ).dict()
            
            # Executar via serviço
            result = await self.llm_service.invoke_generic(
                operation=operation,
                model_id=model_id,
                payload=payload,
                project_id=project_id,
                request_id=request_id
            )
            
            return result
            
        except Exception as e:
            self._log_error("invoke_generic", str(e))
            return self._error_response(f"Erro interno: {str(e)}", 500).dict()

    async def generate_response(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera resposta usando LLM
        
        Args:
            request_data: Dados da requisição LLM
            
        Returns:
            Resposta do modelo ou erro
        """
        try:
            # Validar dados de entrada
            self._validate_generate_request(request_data)
            
            # Gerar ID único para requisição
            request_id = str(uuid.uuid4())
            
            self._log_request("generate_response", {
                "request_id": request_id,
                "model": request_data.get("model"),
                "project_id": request_data.get("project_id")
            })
            
            # Verificar autenticação do projeto
            if request_data.get("project_id"):
                is_authorized = await self.project_auth.verify_project_access(
                    request_data["project_id"]
                )
                if not is_authorized:
                    raise PermissionError("Project access denied")
            
            # Criar objeto de requisição
            llm_request = LLMRequest(
                request_id=request_id,
                model=request_data["model"],
                prompt=request_data["prompt"],
                system_prompt=request_data.get("system_prompt"),
                max_tokens=request_data.get("max_tokens", 1000),
                temperature=request_data.get("temperature", 0.7),
                stream=request_data.get("stream", False),
                project_id=request_data.get("project_id")
            )
            
            # Executar geração
            start_time = time.time()
            response = await self.llm_service.generate_response(
                model_id=llm_request.model,
                prompt=llm_request.prompt,
                system_prompt=llm_request.system_prompt,
                project_id=llm_request.project_id,
                max_tokens=llm_request.max_tokens,
                temperature=llm_request.temperature,
                stream=llm_request.stream
            )
            end_time = time.time()
            
            # Formatar resposta
            response_data = {
                "request_id": response.request_id,
                "model": response.model,
                "response_text": response.response_text,
                "finish_reason": response.finish_reason,
                "usage": response.usage,
                "response_time_ms": response.response_time_ms,
                "provider": response.provider.value if response.provider else None,
                "error": response.error,
                "total_request_time_ms": round((end_time - start_time) * 1000, 2)
            }
            
            success = response.finish_reason != "error"
            self._log_response("generate_response", success, {
                "request_id": request_id,
                "finish_reason": response.finish_reason,
                "tokens": response.usage.get("total_tokens", 0) if response.usage else 0
            })
            
            return ControllerResponse.success(
                data=response_data,
                message="Response generated successfully" if success else "Response completed with error"
            )
            
        except Exception as e:
            self._log_response("generate_response", False, {"error": str(e)})
            raise self._handle_error(e, "generate_response")
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Obtém status do serviço LLM
        
        Returns:
            Status de todos os providers
        """
        try:
            self._log_request("get_service_status")
            
            # Obter status dos providers
            provider_status = self.llm_service.get_provider_status()
            
            # Estatísticas adicionais
            available_models = self.llm_service.get_available_models()
            total_models = len(available_models)
            enabled_models = len([m for m in available_models if m.enabled])
            
            status_data = {
                "providers": provider_status,
                "models": {
                    "total": total_models,
                    "enabled": enabled_models,
                    "disabled": total_models - enabled_models
                },
                "timestamp": time.time(),
                "service_healthy": any(provider_status.values())
            }
            
            self._log_response("get_service_status", True, status_data)
            
            return ControllerResponse.success(
                data=status_data,
                message="Service status retrieved successfully"
            )
            
        except Exception as e:
            self._log_response("get_service_status", False, {"error": str(e)})
            raise self._handle_error(e, "get_service_status")
    
    def reload_service(self) -> Dict[str, Any]:
        """
        Recarrega configuração do serviço
        
        Returns:
            Resultado do reload
        """
        try:
            self._log_request("reload_service")
            
            # Recarregar providers
            self.llm_service.reload_providers()
            
            # Verificar novo status
            new_status = self.llm_service.get_provider_status()
            
            self._log_response("reload_service", True, {"new_status": new_status})
            
            return ControllerResponse.success(
                data={"status": new_status},
                message="Service reloaded successfully"
            )
            
        except Exception as e:
            self._log_response("reload_service", False, {"error": str(e)})
            raise self._handle_error(e, "reload_service")
    
    async def invoke(
        self,
        operation: str,
        model_id: str,
        payload: Dict[str, Any],
        project_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Invocação central para wrapper LangChain
        
        Args:
            operation: Tipo de operação
            model_id: ID do modelo
            payload: Payload da requisição
            project_id: ID do projeto
            request_id: ID da requisição
            
        Returns:
            Resultado da operação
        """
        try:
            self._log_request("invoke", {
                "operation": operation,
                "model_id": model_id, 
                "project_id": project_id,
                "request_id": request_id
            })
            
            # Validar operação
            self._validate_invoke_request(operation, model_id, payload)
            
            # Executar via serviço
            result = await self.llm_service.invoke(
                operation=operation,
                model_id=model_id,
                payload=payload,
                project_id=project_id,
                request_id=request_id
            )
            
            self._log_response("invoke", True, {"request_id": result.get("request_id")})
            return result
            
        except Exception as e:
            self._log_response("invoke", False, {"error": str(e)})
            raise self._handle_error(e, "invoke")
    
    def _validate_invoke_request(self, operation: str, model_id: str, payload: Dict[str, Any]) -> None:
        """Valida requisição de invoke"""
        # Validar operação
        valid_operations = ["chat", "completion", "batch", "stream", "embedding"]
        if operation not in valid_operations:
            raise ValueError(f"Operation '{operation}' not supported. Valid: {valid_operations}")
        
        # Validar modelo
        if not model_id or not isinstance(model_id, str):
            raise ValueError("model_id is required and must be a string")
        
        # Validar payload
        if not isinstance(payload, dict):
            raise ValueError("payload must be a dictionary")
        
        # Validações específicas por operação
        if operation in ["chat", "completion"]:
            # Suportar tanto formato LangChain (messages) quanto formato legado (prompt)
            if "messages" not in payload and "prompt" not in payload:
                raise ValueError("messages or prompt is required for chat/completion operations")
            
            if "messages" in payload:
                if not isinstance(payload["messages"], list) or len(payload["messages"]) == 0:
                    raise ValueError("messages must be a non-empty list")
                # Verificar se cada mensagem tem o formato correto
                for msg in payload["messages"]:
                    if not isinstance(msg, dict) or "content" not in msg:
                        raise ValueError("each message must be a dict with 'content' field")
            elif "prompt" in payload:
                if not isinstance(payload["prompt"], str) or len(payload["prompt"].strip()) == 0:
                    raise ValueError("prompt must be a non-empty string")
    
    def _validate_generate_request(self, data: Dict[str, Any]) -> None:
        """Valida dados de requisição de geração"""
        required_fields = ["model", "prompt"]
        self._validate_required_fields(data, required_fields)
        
        # Validações específicas
        if not isinstance(data.get("prompt"), str) or len(data["prompt"].strip()) == 0:
            raise ValueError("Prompt must be a non-empty string")
        
        if data.get("max_tokens") is not None:
            max_tokens = data["max_tokens"]
            if not isinstance(max_tokens, int) or max_tokens < 1 or max_tokens > 32000:
                raise ValueError("max_tokens must be between 1 and 32000")
        
        if data.get("temperature") is not None:
            temp = data["temperature"]
            if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                raise ValueError("temperature must be between 0 and 2")
    
    def _filter_models_by_project(self, models: List, project_id: str) -> List:
        """Filtra modelos baseado em permissões do projeto"""
        # Por enquanto retorna todos - implementar lógica de governança
        return models


# Instância singleton do controller
llm_controller = LLMController()
