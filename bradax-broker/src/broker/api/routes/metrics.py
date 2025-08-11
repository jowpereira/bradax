"""
Metrics and Monitoring endpoints

Endpoints para coleta de métricas e monitoramento
da plataforma bradax.
"""

from typing import Dict, Any, List
from fastapi import APIRouter
import time
import psutil
import json

router = APIRouter()


@router.get("/system", summary="Métricas do sistema")
async def get_system_metrics() -> Dict[str, Any]:
    """
    Retorna métricas básicas do sistema.
    
    Returns:
        Métricas de CPU, memória, disco
    """
    
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memória
        memory = psutil.virtual_memory()
        
        # Disco
        disk = psutil.disk_usage('/')
        
        return {
            "system": {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "cores": cpu_count
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "usage_percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "usage_percent": round((disk.used / disk.total) * 100, 2)
                }
            },
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    except Exception as e:
        # Fallback se psutil não estiver disponível
        return {
            "system": {
                "status": "metrics_unavailable",
                "error": str(e)
            },
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }