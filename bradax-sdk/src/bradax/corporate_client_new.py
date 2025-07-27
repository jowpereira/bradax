"""
Cliente SDK bradax - Versão Corporativa

SDK Python profissional para comunicação segura com o bradax Broker.
Inclui autenticação por projeto, guardrails automáticos e auditoria completa.
"""

# Re-exporta classes do novo módulo cliente
from .client.corporate_client import (
    BradaxCorporateClient,
    BradaxError,
    BradaxAuthenticationError,
    BradaxValidationError,
    AuditLogger
)

# Mantém compatibilidade com código antigo
__all__ = [
    'BradaxCorporateClient',
    'BradaxError',
    'BradaxAuthenticationError', 
    'BradaxValidationError',
    'AuditLogger'
]
