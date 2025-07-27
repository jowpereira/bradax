"""
API Routes Module

Expõe todos os routers da API bradax Broker.
"""

from .auth import router as auth_router
from .llm import router as llm_router  
from .health import router as health_router
from .vector import router as vector_router
from .graph import router as graph_router
from .metrics import router as metrics_router

__all__ = [
    "auth_router",
    "llm_router", 
    "health_router",
    "vector_router",
    "graph_router", 
    "metrics_router"
]
