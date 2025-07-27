"""
CORS Configuration

Configuração de Cross-Origin Resource Sharing.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app: FastAPI, allow_origins: list = None) -> None:
    """
    Configura CORS para a aplicação.
    
    Args:
        app: Instância FastAPI
        allow_origins: Lista de origens permitidas
    """
    
    if allow_origins is None:
        allow_origins = [
            "http://localhost:3000",  # React dev
            "http://localhost:8080",  # Vue dev
            "http://localhost:4200",  # Angular dev
            "https://localhost:3000", # HTTPS local
        ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"]
    )
