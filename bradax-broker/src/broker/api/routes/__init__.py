"""
API Routes Module

Expõe todos os routers da API bradax Broker.
"""

from . import auth, llm, health, metrics, projects, system

__all__ = [
    "auth",
    "llm", 
    "health",
    "metrics",
    "projects",
    "system"
]
