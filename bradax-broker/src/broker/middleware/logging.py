"""
Logging Middleware

Middleware para logging estruturado de requisições.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog


logger = structlog.get_logger("bradax.middleware.logging")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para logging estruturado de todas as requisições."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Processa requisições com logging estruturado.
        
        Args:
            request: Requisição HTTP
            call_next: Próximo middleware/handler
            
        Returns:
            Response HTTP
        """
        
        # Gerar ID único para a requisição
        request_id = str(uuid.uuid4())
        
        # Adicionar request ID ao contexto
        request.state.request_id = request_id
        
        # Log da requisição iniciando
        start_time = time.time()
        
        logger.info(
            "request_started",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        try:
            # Processar requisição
            response = await call_next(request)
            
            # Calcular tempo de processamento
            process_time = time.time() - start_time
            
            # Log da resposta
            logger.info(
                "request_completed",
                request_id=request_id,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2)
            )
            
            # Adicionar headers de rastreamento
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Log de erro
            process_time = time.time() - start_time
            
            logger.error(
                "request_failed",
                request_id=request_id,
                error=str(e),
                error_type=type(e).__name__,
                process_time_ms=round(process_time * 1000, 2)
            )
            
            # Re-raise a exceção
            raise
