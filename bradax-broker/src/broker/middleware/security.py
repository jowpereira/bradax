"""
Security Middleware

Middleware para headers de segurança e proteções.
"""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware para adicionar headers de segurança."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Adiciona headers de segurança às respostas.
        
        Args:
            request: Requisição HTTP
            call_next: Próximo middleware/handler
            
        Returns:
            Response com headers de segurança
        """
        
        response = await call_next(request)
        
        # Headers de segurança
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", 
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'",
            "X-Permitted-Cross-Domain-Policies": "none"
        }
        
        # Aplicar headers
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response
