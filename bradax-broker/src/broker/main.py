"""
Aplicação principal do bradax Broker

Este módulo implementa o servidor FastAPI que atua como proxy
seguro para operações de LLM, Vector DB e Graph execution.
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog

from .config import settings
from .api.routes import health, auth, llm, vector, graph, metrics
from .middleware.logging import LoggingMiddleware
from .middleware.security import SecurityMiddleware
from .middleware.rate_limiting import RateLimitingMiddleware


# Configurar logging estruturado
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    # Startup
    logger.info("🚀 Iniciando bradax Broker", version="0.1.0")
    
    # Inicializar componentes
    await startup_event()
    
    yield
    
    # Shutdown
    logger.info("🛑 Encerrando bradax Broker")
    await shutdown_event()


async def startup_event():
    """Eventos de inicialização"""
    logger.info("📋 Inicializando componentes do Broker...")
    
    # TODO: Inicializar cofre de chaves
    # TODO: Verificar conectividade com LLM providers
    # TODO: Inicializar cache Redis
    # TODO: Configurar observabilidade
    
    logger.info("✅ Broker inicializado com sucesso")


async def shutdown_event():
    """Eventos de encerramento"""
    logger.info("📋 Encerrando componentes do Broker...")
    
    # TODO: Fechar conexões
    # TODO: Salvar estado do cofre de chaves
    # TODO: Flush logs e métricas
    
    logger.info("✅ Broker encerrado com sucesso")


def create_app() -> FastAPI:
    """Factory para criar a aplicação FastAPI"""
    
    app = FastAPI(
        title="bradax Broker",
        description="Runtime de IA generativa seguro e flexível para bradax AI Solutions",
        version="0.1.0",
        docs_url="/docs" if settings.BRADAX_BROKER_DEBUG else None,
        redoc_url="/redoc" if settings.BRADAX_BROKER_DEBUG else None,
        openapi_url="/openapi.json" if settings.BRADAX_BROKER_DEBUG else None,
        lifespan=lifespan
    )
    
    # Middlewares de segurança (ordem importa!)
    setup_middlewares(app)
    
    # Rotas da API
    setup_routes(app)
    
    # Handlers de erro
    setup_error_handlers(app)
    
    return app


def setup_middlewares(app: FastAPI):
    """Configura middlewares da aplicação"""
    
    # CORS - apenas para desenvolvimento local
    if settings.BRADAX_BROKER_DEBUG:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.BRADAX_BROKER_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
        )
    
    # Trusted hosts
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.BRADAX_BROKER_ALLOWED_HOSTS
    )
    
    # Middlewares customizados
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(RateLimitingMiddleware) 
    app.add_middleware(LoggingMiddleware)


def setup_routes(app: FastAPI):
    """Configura as rotas da API"""
    
    # Health check (sem autenticação)
    app.include_router(health.router, prefix="/health", tags=["Health"])
    
    # API v1 (com autenticação)
    api_v1_prefix = "/api/v1"
    
    app.include_router(
        auth.router, 
        prefix=f"{api_v1_prefix}/auth", 
        tags=["Authentication"]
    )
    
    app.include_router(
        llm.router, 
        prefix=f"{api_v1_prefix}/llm", 
        tags=["LLM Operations"]
    )
    
    app.include_router(
        vector.router, 
        prefix=f"{api_v1_prefix}/vectors", 
        tags=["Vector Database"]
    )
    
    app.include_router(
        graph.router, 
        prefix=f"{api_v1_prefix}/graphs", 
        tags=["Graph Management"]
    )
    
    app.include_router(
        metrics.router, 
        prefix=f"{api_v1_prefix}/metrics", 
        tags=["Observability"]
    )


def setup_error_handlers(app: FastAPI):
    """Configura handlers de erro customizados"""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handler para HTTPException padronizado"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "message": exc.detail,
                "status_code": exc.status_code,
                "request_id": getattr(request.state, "request_id", None),
                "timestamp": structlog.processors.TimeStamper().format_timestamp(None)
            }
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handler para ValueError"""
        logger.error(
            "Erro de validação",
            error=str(exc),
            request_id=getattr(request.state, "request_id", None)
        )
        
        return JSONResponse(
            status_code=400,
            content={
                "error": "validation_error",
                "message": str(exc),
                "request_id": getattr(request.state, "request_id", None),
                "timestamp": structlog.processors.TimeStamper().format_timestamp(None)
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handler para exceções gerais"""
        logger.error(
            "Erro interno do servidor",
            error=str(exc),
            error_type=type(exc).__name__,
            request_id=getattr(request.state, "request_id", None),
            exc_info=True
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "Erro interno do servidor",
                "request_id": getattr(request.state, "request_id", None),
                "timestamp": structlog.processors.TimeStamper().format_timestamp(None)
            }
        )


# Instância da aplicação
app = create_app()


def main():
    """Ponto de entrada principal"""
    uvicorn.run(
        "broker.main:app",
        host=settings.BRADAX_BROKER_HOST,
        port=settings.BRADAX_BROKER_PORT,
        reload=settings.BRADAX_BROKER_DEBUG,
        log_level="debug" if settings.BRADAX_BROKER_DEBUG else "info",
        access_log=settings.BRADAX_BROKER_DEBUG,
        loop="asyncio"
    )


if __name__ == "__main__":
    main()
