"""
System API Routes - Telemetria e Monitoramento

Endpoints para operações de sistema, métricas e health checks.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional

from ...controllers.system_controller import SystemController


# Criar router e controller
router = APIRouter(tags=["System Operations"])
system_controller = SystemController()


@router.get("/health")
async def get_system_health() -> Dict[str, Any]:
    """
    Health check completo do sistema
    
    Returns:
        Status detalhado de saúde do sistema
    """
    try:
        return system_controller.get_health_status()  # Método correto que existe
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_system_metrics() -> Dict[str, Any]:
    """
    Métricas de performance do sistema
    
    Returns:
        Métricas detalhadas de CPU, memória, disco, etc.
    """
    try:
        return system_controller.get_system_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_system_config() -> Dict[str, Any]:
    """
    Configurações atuais do sistema
    
    Returns:
        Configurações globais e de ambiente
    """
    try:
        return system_controller.get_configuration()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_configurations() -> Dict[str, Any]:
    """
    Recarrega configurações do sistema
    
    Returns:
        Status da operação de reload
    """
    try:
        return system_controller.reload_configurations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_services_status() -> Dict[str, Any]:
    """
    Status de todos os serviços
    
    Returns:
        Status detalhado de LLM, storage, etc.
    """
    try:
        return system_controller.get_service_status()  # Método correto (singular)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/telemetry")
async def get_system_telemetry() -> Dict[str, Any]:
    """
    Dados de telemetria do sistema
    
    Returns:
        Dados de telemetria e métricas de uso
    """
    try:
        response = system_controller.get_telemetry_data()
        if response.get("success"):
            return response.get("data")
        else:
            raise HTTPException(status_code=500, detail=response.get("error", "Erro na telemetria"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
