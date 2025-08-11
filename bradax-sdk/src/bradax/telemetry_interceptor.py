"""
Telemetry Interceptor para Bradax SDK
"""

import hashlib
import platform
import uuid
import json
import time
import requests
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

try:
    import psutil
except ImportError:
    psutil = None

from bradax.constants import BradaxEnvironment, SDKSecurityConstants

# Logger específico
telemetry_logger = logging.getLogger('bradax.telemetry')

class TelemetryInterceptor:
    def __init__(self, broker_url: str, project_id: str):
        self.broker_url = broker_url.rstrip('/')
        self.project_id = project_id
        self.session_id = str(uuid.uuid4())
        self.machine_fingerprint = self._generate_machine_fingerprint()
        
    def _generate_machine_fingerprint(self) -> str:
        try:
            system_info = [
                platform.system(),
                platform.node(),
                platform.release()
            ]
            
            if psutil:
                system_info.append(str(psutil.cpu_count()))
                system_info.append(str(psutil.virtual_memory().total))
            
            fingerprint_data = "-".join(system_info)
            fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
            
            # Formato específico para desenvolvimento
            return f"machine_{fingerprint}"
        except Exception:
            # Fallback para fingerprint de desenvolvimento conhecido
            return "machine_8e219290de7aa69a"
    
    def _get_telemetry_headers(self) -> Dict[str, str]:

        return {
            # Headers básicos de telemetria
            "X-Bradax-Project-Id": self.project_id,
            "X-Bradax-Session-Id": self.session_id,
            "X-Bradax-Request-Id": str(uuid.uuid4()),
            "X-Bradax-Machine-Fingerprint": self.machine_fingerprint,
            "X-Bradax-Timestamp": datetime.utcnow().isoformat(),
            "X-Bradax-SDK-Version": SDKSecurityConstants.USER_AGENT.split("/")[-1],
            "X-Bradax-Client-Type": "python-sdk",

            # Headers obrigatórios para middleware
            "X-Bradax-Telemetry-Enabled": "true",
            "X-Bradax-Environment": BradaxEnvironment.DEVELOPMENT.value,
            "X-Bradax-Platform": platform.system(),
            "X-Bradax-Python-Version": platform.python_version(),

            # User-Agent obrigatório
            "User-Agent": SDKSecurityConstants.USER_AGENT
        }
    def _send_telemetry(self, request_id: str, operation: str, model: str, **metadata) -> None:
        """Envia dados de telemetria da máquina local para o broker"""
        telemetry_data = {
            "request_id": request_id,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "operation": operation,
            "model": model,
            "machine_fingerprint": self.machine_fingerprint,
            "timestamp": datetime.utcnow().isoformat(),
            "sdk_version": "1.0.0",
            "client_type": "python-sdk",
            "system_info": {
                "platform": platform.system(),
                "node": platform.node(),
                "release": platform.release(),
                "python_version": platform.python_version()
            },
            **metadata
        }
        
        if psutil:
            telemetry_data["system_info"].update({
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_usage": psutil.disk_usage('/').percent if hasattr(psutil, 'disk_usage') else None
            })
        
        # Enviar telemetria para o broker
        try:
            telemetry_response = requests.post(
                f"{self.broker_url}/api/v1/system/telemetry",
                headers={"Content-Type": "application/json"},
                json=telemetry_data,
                timeout=10
            )
            telemetry_logger.debug(f"Telemetria enviada: {telemetry_response.status_code}")
        except Exception as e:
            telemetry_logger.warning(f"Falha ao enviar telemetria: {e}")

    def intercept_llm_request(self, model: str, messages: List[Dict[str, str]], **kwargs) -> str:
        request_id = str(uuid.uuid4())
        
        # FLUXO CORRETO: SDK só envia telemetria + dados para o BROKER
        # O BROKER que processa guardrails, chama LLM e salva nos JSONs
        
        payload = {
            # Dados da requisição LLM
            "operation": "chat",
            "model": model, 
            "payload": {
                "messages": messages,
                **kwargs
            },
            "project_id": self.project_id,
            "request_id": request_id,
            
            # Telemetria da máquina local incluída na requisição
            "telemetry": {
                "session_id": self.session_id,
                "machine_fingerprint": self.machine_fingerprint,
                "timestamp": datetime.utcnow().isoformat(),
                "sdk_version": "1.0.0",
                "client_type": "python-sdk",
                "system_info": {
                    "platform": platform.system(),
                    "node": platform.node(),
                    "release": platform.release(),
                    "python_version": platform.python_version()
                }
            }
        }
        
        # Adicionar info do psutil se disponível
        if psutil:
            payload["telemetry"]["system_info"].update({
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_usage": psutil.disk_usage('/').percent if hasattr(psutil, 'disk_usage') else None
            })
        
        headers = self._get_telemetry_headers()
        headers["Content-Type"] = "application/json"
        
        # BROKER processa tudo: telemetria + guardrails + LLM + salva JSONs
        response = requests.post(
            f"{self.broker_url}/api/v1/llm/invoke",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            response_data = response.json()
            return response_data.get('result', {}).get('content', '')
        else:
            raise Exception(f"LLM request failed: {response.status_code} - {response.text}")
    
    def chat_completion(self, model: str, messages: List[Dict[str, str]], **kwargs) -> str:
        return self.intercept_llm_request(model, messages, **kwargs)
    
    def completion(self, model: str, prompt: str, **kwargs) -> str:
        messages = [{"role": "user", "content": prompt}]
        return self.intercept_llm_request(model, messages, **kwargs)
    
    def intercept_request(self, prompt, model, temperature, max_tokens, metadata):
        """Intercepta requisição para capturar dados de telemetria"""
        request_data = {
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "prompt": str(prompt),
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "metadata": metadata,
            "session_id": self.session_id,
            "project_id": self.project_id
        }
        return request_data
    
    def capture_response(self, request_data, response_data, raw_response, success, error_message=None):
        """Captura dados de resposta para auditoria"""
        try:
            telemetry_data = {
                "request_id": request_data["request_id"],
                "success": success,
                "timestamp_response": datetime.utcnow().isoformat(),
                "response_data": response_data,
                "error_message": error_message,
                "session_id": self.session_id
            }
            
            # Aqui poderia salvar em arquivo local ou enviar para broker
            telemetry_logger.debug(f"Telemetria capturada: success={success}")
            
        except Exception as e:
            telemetry_logger.warning(f"Erro ao capturar telemetria: {e}")
    
    def get_telemetry_headers(self):
        """Compatibilidade com client.py - retorna headers de telemetria"""
        return self._get_telemetry_headers()

# Global interceptor
_global_telemetry_interceptor: Optional[TelemetryInterceptor] = None

def initialize_global_telemetry(broker_url: str, project_id: str) -> TelemetryInterceptor:
    global _global_telemetry_interceptor
    _global_telemetry_interceptor = TelemetryInterceptor(broker_url, project_id)
    return _global_telemetry_interceptor

def get_telemetry_interceptor() -> Optional[TelemetryInterceptor]:
    return _global_telemetry_interceptor

def chat_completion(model: str, messages: List[Dict[str, str]], **kwargs) -> str:
    if _global_telemetry_interceptor is None:
        raise ValueError("Telemetria não inicializada. Chame initialize_global_telemetry() primeiro.")
    return _global_telemetry_interceptor.chat_completion(model, messages, **kwargs)

def completion(model: str, prompt: str, **kwargs) -> str:
    if _global_telemetry_interceptor is None:
        raise ValueError("Telemetria não inicializada. Chame initialize_global_telemetry() primeiro.")
    return _global_telemetry_interceptor.completion(model, prompt, **kwargs)
