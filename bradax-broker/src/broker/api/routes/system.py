"""
Sistema de rotas para informações do sistema
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
import platform
import sys
from datetime import datetime

# Criar router
router = APIRouter(prefix="/system", tags=["System"])

@router.get("/info")
async def get_system_info():
    """Retorna informações básicas do sistema"""
    return JSONResponse(content={
        "platform": platform.platform(),
        "python_version": sys.version,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy"
    })

@router.get("/health")
async def health_check():
    """Health check simples do sistema"""
    return JSONResponse(content={
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    })
