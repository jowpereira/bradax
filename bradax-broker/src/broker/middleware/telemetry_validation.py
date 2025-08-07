"""
Middleware Anti-Burla de Telemetria - Bradax Broker

Valida que o SDK está enviando telemetria obrigatória.
Bloqueia qualquer tentativa de bypass da auditoria.
"""

import logging
import os
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import json
import time
from ..constants import BradaxEnvironment, get_hub_environment

logger = logging.getLogger(__name__)


class TelemetryValidationMiddleware:
    """
    Middleware que força telemetria obrigatória em todas as requisições do SDK.
    
    CARACTERÍSTICAS:
    - Valida headers de telemetria obrigatórios
    - Bloqueia requisições sem metadados de auditoria
    - Registra tentativas de bypass
    - Aplica políticas corporativas de compliance
    """
    
    def __init__(self, app):
        self.app = app
        
        # Endpoints que DEVEM ter telemetria obrigatória
        self.telemetry_required_endpoints = [
            "/api/v1/llm/invoke",
            "/api/v1/llm/batch",
            "/api/v1/llm/stream", 
            "/api/v1/vector/embed",
            "/api/v1/graph/execute"
        ]
        
        # Headers obrigatórios para auditoria (sincronizado com SDK)
        self.required_telemetry_headers = [
            "x-bradax-sdk-version",
            "x-bradax-machine-fingerprint", 
            "x-bradax-session-id",
            "x-bradax-telemetry-enabled",
            "x-bradax-environment",
            "x-bradax-platform", 
            "x-bradax-python-version"
        ]
    
    async def __call__(self, scope, receive, send):
        """
        Processa requisição ASGI validando telemetria obrigatória.
        
        Args:
            scope: ASGI scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
            
        # Construir request object para análise
        request = Request(scope, receive)
        
        # Verificar se endpoint requer telemetria
        if self._requires_telemetry(request.url.path):
            validation_result = await self._validate_telemetry_compliance(request)
            
            if not validation_result["valid"]:
                # 🚨 BLOQUEAR tentativa de bypass
                await self._log_security_violation(request, validation_result)
                
                response = JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": "TELEMETRY_BYPASS_BLOCKED",
                        "message": "🚨 VIOLAÇÃO DE SEGURANÇA: Telemetria obrigatória não detectada.",
                        "details": validation_result["violations"],
                        "policy": "Todas as interações devem ser auditadas conforme política corporativa.",
                        "action_required": "Use o SDK oficial sem modificações para telemetria."
                    }
                )
                await response(scope, receive, send)
                return
        
        # Processar requisição normalmente
        await self.app(scope, receive, send)
    
    def _requires_telemetry(self, path: str) -> bool:
        """
        Verifica se endpoint requer telemetria obrigatória.
        
        Args:
            path: Caminho da URL
            
        Returns:
            True se telemetria é obrigatória
        """
        return any(path.startswith(endpoint) for endpoint in self.telemetry_required_endpoints)
    
    async def _validate_telemetry_compliance(self, request: Request) -> Dict[str, Any]:
        """
        Valida compliance de telemetria na requisição.
        
        Args:
            request: Requisição FastAPI
            
        Returns:
            Dict com resultado da validação
        """
        violations = []
        
        # 1. Verificar headers obrigatórios
        for header in self.required_telemetry_headers:
            value = request.headers.get(header)
            if not value:
                violations.append(f"Header obrigatório ausente: {header}")
            elif header == "x-bradax-telemetry-enabled" and value.lower() != "true":
                violations.append(f"Telemetria desabilitada detectada: {header}={value}")
        
        # 2. Verificar User-Agent do SDK
        user_agent = request.headers.get("user-agent", "")
        if not user_agent.startswith("bradax-sdk/"):
            violations.append(f"User-Agent inválido: {user_agent} (esperado: bradax-sdk/x.x.x)")
        
        # 3. Verificar fingerprint da máquina
        machine_fingerprint = request.headers.get("x-bradax-machine-fingerprint")
        if machine_fingerprint:
            # Permitir fingerprints de desenvolvimento específicos
            development_fingerprints = ["8e219290de7aa69a", "machine_8e219290de7aa69a"] 
            environment = get_hub_environment()
            
            if environment == BradaxEnvironment.DEVELOPMENT:
                # Em desenvolvimento, permitir fingerprints conhecidos
                if machine_fingerprint not in development_fingerprints and not machine_fingerprint.startswith("machine_"):
                    violations.append(f"Machine fingerprint inválido: {machine_fingerprint}")
            else:
                # Em produção, sempre exigir formato correto
                if not machine_fingerprint.startswith("machine_"):
                    violations.append(f"Machine fingerprint inválido: {machine_fingerprint}")
        
        # 4. Verificar payload por tentativas de bypass
        # NOTA: Evitar request.body() em middleware pois consome o stream
        # Em vez disso, fazer validação na próxima versão ou em interceptor específico
        # if request.method == "POST":
        #     try:
        #         body = await request.body()
        #         if body:
        #             payload = json.loads(body)
        #             
        #             # Verificar tentativas de desabilitar telemetria no payload
        #             if self._check_telemetry_bypass_in_payload(payload):
        #                 violations.append("Tentativa de bypass de telemetria detectada no payload")
        #                 
        #     except Exception as e:
        #         logger.warning(f"Erro ao validar payload: {e}")
        
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "compliance_level": "FAILED" if violations else "COMPLIANT"
        }
    
    def _check_telemetry_bypass_in_payload(self, payload: Dict[str, Any]) -> bool:
        """
        Verifica tentativas de bypass de telemetria no payload.
        
        Args:
            payload: Payload da requisição
            
        Returns:
            True se bypass detectado
        """
        # Palavras-chave suspeitas de bypass
        bypass_keywords = [
            "disable_telemetry",
            "telemetry_enabled",
            "no_telemetry", 
            "skip_audit",
            "bypass_logging",
            "disable_logging"
        ]
        
        payload_str = json.dumps(payload).lower()
        
        for keyword in bypass_keywords:
            if keyword in payload_str:
                # Verificar se está tentando desabilitar
                if f'"{keyword}": false' in payload_str or f'"{keyword}":false' in payload_str:
                    return True
                if f'"{keyword}": "false"' in payload_str or f'"{keyword}":"false"' in payload_str:
                    return True
        
        return False
    
    async def _log_security_violation(self, request: Request, validation_result: Dict[str, Any]):
        """
        Registra violação de segurança para auditoria.
        
        Args:
            request: Requisição que violou política
            validation_result: Resultado da validação
        """
        violation_data = {
            "timestamp": time.time(),
            "event_type": "TELEMETRY_BYPASS_ATTEMPT",
            "severity": "HIGH",
            "source_ip": request.client.host if request.client else "unknown",
            "endpoint": str(request.url),
            "method": request.method,
            "user_agent": request.headers.get("user-agent", "unknown"),
            "violations": validation_result["violations"],
            "headers": dict(request.headers),
            "compliance_level": validation_result["compliance_level"]
        }
        
        # Log para sistema de auditoria
        logger.warning(
            f"🚨 VIOLAÇÃO DE SEGURANÇA - Tentativa de bypass de telemetria: "
            f"{request.client.host if request.client else 'unknown'} -> {request.url.path}"
        )
        logger.warning(f"Violações: {validation_result['violations']}")
        
        # TODO: Integrar com sistema de alertas de segurança
        # TODO: Notificar CISO/SOC sobre tentativa de bypass


def create_telemetry_validation_middleware():
    """
    Factory function para criar middleware de validação de telemetria.
    
    Returns:
        Instância configurada do middleware
    """
    return TelemetryValidationMiddleware
