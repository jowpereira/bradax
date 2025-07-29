"""
Rate Limiting Middleware Otimizado

Middleware para controle de taxa de requisições com constantes internas.
"""

import time
from typing import Dict, Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityConstants:
    """Constantes de segurança centralizadas"""
    DEFAULT_REQUESTS_PER_MINUTE = 60
    RATE_LIMIT_WINDOW_SECONDS = 60
    RATE_LIMIT_CLEANUP_INTERVAL = 300


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para controle de taxa de requisições.
    
    Implementa rate limiting usando constantes centralizadas.
    """
    
    def __init__(
        self, 
        app,
        requests_per_minute: int = None,
        burst_size: int = 10
    ):
        """
        Inicializa o middleware de rate limiting.
        
        Args:
            app: Aplicação ASGI
            requests_per_minute: Limite de requests por minuto (usa constante se None)
            burst_size: Tamanho do burst permitido
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute or SecurityConstants.DEFAULT_REQUESTS_PER_MINUTE
        self.burst_size = burst_size
        self.clients: Dict[str, Dict] = {}
        self.last_cleanup = time.time()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Verifica rate limiting antes de processar a requisição.
        
        Args:
            request: Requisição HTTP
            call_next: Próximo middleware/handler
            
        Returns:
            Response HTTP ou erro 429
        """
        
        # Obter IP do cliente
        client_ip = self._get_client_ip(request)
        
        # Verificar rate limit (sempre ativo para produção)
        if not self._check_rate_limit(client_ip):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Too many requests.",
                headers={"Retry-After": str(SecurityConstants.RATE_LIMIT_WINDOW_SECONDS)}
            )
        
        # Processar requisição
        response = await call_next(request)
        
        # Adicionar headers informativos
        client_data = self.clients.get(client_ip, {})
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.requests_per_minute - client_data.get("count", 0))
        )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Obtém IP do cliente considerando proxies."""
        
        # Verificar headers de proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # IP direto
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """
        Verifica se o cliente excedeu o rate limit.
        
        Args:
            client_ip: IP do cliente
            
        Returns:
            True se dentro do limite, False caso contrário
        """
        
        now = time.time()
        
        # Inicializar dados do cliente se não existir
        if client_ip not in self.clients:
            self.clients[client_ip] = {
                "count": 0,
                "window_start": now,
                "last_request": now
            }
        
        client_data = self.clients[client_ip]
        
        # Verificar se precisa resetar janela - usar constante
        if now - client_data["window_start"] >= SecurityConstants.RATE_LIMIT_WINDOW_SECONDS:
            client_data["count"] = 0
            client_data["window_start"] = now
        
        # Verificar burst (muitas requisições muito rápidas)
        if now - client_data["last_request"] < 1 and client_data["count"] >= self.burst_size:
            return False
        
        # Verificar limite por minuto
        if client_data["count"] >= self.requests_per_minute:
            return False
        
        # Atualizar contadores
        client_data["count"] += 1
        client_data["last_request"] = now
        
        return True
    
    def cleanup_old_clients(self) -> None:
        """Remove dados de clientes antigos para economizar memória."""
        
        now = time.time()
        cutoff = now - SecurityConstants.RATE_LIMIT_CLEANUP_INTERVAL  # Usar constante
        
        clients_to_remove = [
            ip for ip, data in self.clients.items()
            if data["last_request"] < cutoff
        ]
        
        for ip in clients_to_remove:
            del self.clients[ip]
