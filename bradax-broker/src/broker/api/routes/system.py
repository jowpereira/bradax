"""
Sistema de rotas para informações do sistema
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import platform
import sys
from datetime import datetime
import logging
import json

# Logger
logger = logging.getLogger(__name__)

# Criar router
router = APIRouter(tags=["System"])

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

@router.post("/telemetry")
async def receive_telemetry(request: Request):
    """
    Endpoint para receber dados de telemetria do SDK.
    
    Este endpoint recebe os dados de telemetria enviados pelo SDK
    e os registra no sistema de telemetria centralizado.
    """
    from ...services.telemetry import get_telemetry_collector
    
    try:
        body = await request.json()
        telemetry_collector = get_telemetry_collector()
        
        # Processar os dados recebidos
        if "event" in body:
            event_data = body["event"]
            project_id = body.get("project_id", "default")
            
            # Registrar evento de autenticação como proxy para telemetria geral
            event_id = telemetry_collector.record_authentication(
                project_id=project_id,
                success=True,
                method="sdk_telemetry",
                metadata=event_data
            )
            
            logger.info(f"Telemetria recebida e registrada: {event_id}")
            
            return JSONResponse(content={
                "success": True, 
                "message": "Telemetry event recorded",
                "event_id": event_id
            })
        else:
            return JSONResponse(
                status_code=400, 
                content={
                    "success": False, 
                    "error": "Missing event data in request body"
                }
            )
            
    except Exception as e:
        logger.error(f"Erro ao processar telemetria: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False, 
                "error": f"Internal server error: {str(e)}"
            }
        )
