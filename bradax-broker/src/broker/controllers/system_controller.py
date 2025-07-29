"""
System Controller - Padrão MVC

Controller central para operações de sistema, configurações e saúde.
"""

from typing import Dict, Any, Optional
from fastapi import HTTPException
import time
import platform
import psutil
import os

from ..controllers import BaseController, ControllerResponse
from ..services.llm.service import LLMService
from ..storage.json_storage import JsonStorage
from ..config import settings


class SystemController(BaseController):
    """
    Controller para operações de sistema
    
    Responsável por:
    - Health checks
    - Métricas de sistema
    - Configurações globais
    - Status de serviços
    """
    
    def __init__(self):
        super().__init__()
        self.llm_service = LLMService()
        self.storage = JsonStorage()
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Verifica saúde geral do sistema
        
        Returns:
            Status de saúde de todos os componentes
        """
        try:
            self._log_request("health_check")
            
            # Verificar componentes críticos
            components = {
                "storage": self._check_storage_health(),
                "llm_service": self._check_llm_service_health(),
                "memory": self._check_memory_health(),
                "disk": self._check_disk_health()
            }
            
            # Status geral
            all_healthy = all(comp["healthy"] for comp in components.values())
            
            health_data = {
                "status": "healthy" if all_healthy else "degraded",
                "timestamp": time.time(),
                "components": components,
                "version": "0.1.0",
                "uptime_seconds": self._get_uptime()
            }
            
            self._log_response("health_check", all_healthy, {"status": health_data["status"]})
            
            return ControllerResponse.success(
                data=health_data,
                message="Health check completed"
            )
            
        except Exception as e:
            self._log_response("health_check", False, {"error": str(e)})
            raise self._handle_error(e, "health_check")
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Obtém métricas detalhadas do sistema
        
        Returns:
            Métricas de performance e uso
        """
        try:
            self._log_request("system_metrics")
            
            # Métricas de sistema
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Métricas da aplicação
            process = psutil.Process(os.getpid())
            
            metrics_data = {
                "system": {
                    "platform": platform.system(),
                    "python_version": platform.python_version(),
                    "cpu_percent": cpu_percent,
                    "cpu_count": psutil.cpu_count(),
                    "memory": {
                        "total_gb": round(memory.total / (1024**3), 2),
                        "available_gb": round(memory.available / (1024**3), 2),
                        "percent_used": memory.percent
                    },
                    "disk": {
                        "total_gb": round(disk.total / (1024**3), 2),
                        "free_gb": round(disk.free / (1024**3), 2),
                        "percent_used": round((disk.used / disk.total) * 100, 2)
                    }
                },
                "application": {
                    "memory_mb": round(process.memory_info().rss / (1024**2), 2),
                    "cpu_percent": process.cpu_percent(),
                    "threads": process.num_threads(),
                    "uptime_seconds": self._get_uptime()
                },
                "timestamp": time.time()
            }
            
            self._log_response("system_metrics", True, {"metrics_collected": len(metrics_data)})
            
            return ControllerResponse.success(
                data=metrics_data,
                message="System metrics collected"
            )
            
        except Exception as e:
            self._log_response("system_metrics", False, {"error": str(e)})
            raise self._handle_error(e, "system_metrics")
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Obtém status de todos os serviços
        
        Returns:
            Status detalhado de cada serviço
        """
        try:
            self._log_request("service_status")
            
            services = {
                "llm_service": self._get_llm_service_status(),
                "storage_service": self._get_storage_service_status(),
                "auth_service": self._get_auth_service_status()
            }
            
            # Contar serviços funcionais
            healthy_services = sum(1 for service in services.values() if service["healthy"])
            total_services = len(services)
            
            status_data = {
                "services": services,
                "summary": {
                    "healthy_count": healthy_services,
                    "total_count": total_services,
                    "overall_health": healthy_services / total_services if total_services > 0 else 0
                },
                "timestamp": time.time()
            }
            
            self._log_response("service_status", True, {"healthy_services": healthy_services})
            
            return ControllerResponse.success(
                data=status_data,
                message="Service status retrieved"
            )
            
        except Exception as e:
            self._log_response("service_status", False, {"error": str(e)})
            raise self._handle_error(e, "service_status")
    
    def get_configuration(self) -> Dict[str, Any]:
        """
        Obtém configurações do sistema (sem dados sensíveis)
        
        Returns:
            Configurações públicas
        """
        try:
            self._log_request("get_configuration")
            
            config_data = {
                "debug": settings.debug,
                "environment": getattr(settings, 'environment', 'development'),
                "cors_enabled": bool(getattr(settings, 'cors_origins', [])),
                "rate_limiting": {
                    "enabled": True,  # Assumindo que está sempre habilitado
                    "requests_per_minute": getattr(settings, 'rate_limit', 60)
                },
                "features": {
                    "llm_service": True,
                    "telemetry": True,
                    "guardrails": True
                },
                "version": "0.1.0",
                "timestamp": time.time()
            }
            
            self._log_response("get_configuration", True, {"config_items": len(config_data)})
            
            return ControllerResponse.success(
                data=config_data,
                message="Configuration retrieved"
            )
            
        except Exception as e:
            self._log_response("get_configuration", False, {"error": str(e)})
            raise self._handle_error(e, "get_configuration")
    
    def _check_storage_health(self) -> Dict[str, Any]:
        """Verifica saúde do sistema de storage"""
        try:
            # Tentar operação básica de leitura
            self.storage.load_projects()
            return {"healthy": True, "message": "Storage accessible"}
        except Exception as e:
            return {"healthy": False, "message": f"Storage error: {str(e)}"}
    
    def _check_llm_service_health(self) -> Dict[str, Any]:
        """Verifica saúde do serviço LLM"""
        try:
            models = self.llm_service.get_available_models()
            provider_status = self.llm_service.get_provider_status()
            active_providers = sum(1 for status in provider_status.values() if status)
            
            return {
                "healthy": active_providers > 0,
                "message": f"{len(models)} models, {active_providers} active providers"
            }
        except Exception as e:
            return {"healthy": False, "message": f"LLM service error: {str(e)}"}
    
    def _check_memory_health(self) -> Dict[str, Any]:
        """Verifica uso de memória"""
        try:
            memory = psutil.virtual_memory()
            healthy = memory.percent < 90  # Menos de 90% de uso
            
            return {
                "healthy": healthy,
                "message": f"Memory usage: {memory.percent:.1f}%"
            }
        except Exception as e:
            return {"healthy": False, "message": f"Memory check error: {str(e)}"}
    
    def _check_disk_health(self) -> Dict[str, Any]:
        """Verifica uso de disco"""
        try:
            disk = psutil.disk_usage('/')
            usage_percent = (disk.used / disk.total) * 100
            healthy = usage_percent < 90  # Menos de 90% de uso
            
            return {
                "healthy": healthy,
                "message": f"Disk usage: {usage_percent:.1f}%"
            }
        except Exception as e:
            return {"healthy": False, "message": f"Disk check error: {str(e)}"}
    
    def _get_llm_service_status(self) -> Dict[str, Any]:
        """Status detalhado do serviço LLM"""
        try:
            provider_status = self.llm_service.get_provider_status()
            models = self.llm_service.get_available_models()
            
            return {
                "healthy": any(provider_status.values()),
                "providers": provider_status,
                "models_count": len(models),
                "enabled_models": len([m for m in models if m.enabled])
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def _get_storage_service_status(self) -> Dict[str, Any]:
        """Status detalhado do serviço de storage"""
        try:
            projects = self.storage.load_projects().get("projects", [])
            return {
                "healthy": True,
                "projects_count": len(projects),
                "active_projects": len([p for p in projects if p.get("active", True)])
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def _get_auth_service_status(self) -> Dict[str, Any]:
        """Status detalhado do serviço de autenticação"""
        try:
            # Por enquanto assumindo que auth está sempre funcionando
            return {
                "healthy": True,
                "message": "Authentication service operational"
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def _get_uptime(self) -> float:
        """Calcula uptime aproximado da aplicação"""
        try:
            process = psutil.Process(os.getpid())
            return time.time() - process.create_time()
        except:
            return 0.0


# Instância singleton do controller
system_controller = SystemController()
