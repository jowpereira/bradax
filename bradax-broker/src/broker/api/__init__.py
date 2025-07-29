"""
Router principal da API

Centraliza e registra todos os routers de endpoints.
"""

from fastapi import APIRouter

# Import dos routers individuais
from .routes import health, auth, llm, metrics

# Router principal da API
api_router = APIRouter()

# Registrar todos os routers com seus prefixos
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"]
)

api_router.include_router(
    auth.router,
    prefix="/auth", 
    tags=["Authentication"]
)

api_router.include_router(
    llm.router,
    prefix="/llm",
    tags=["LLM Operations"]
)

api_router.include_router(
    metrics.router,
    prefix="/metrics",
    tags=["Metrics & Monitoring"]
)
