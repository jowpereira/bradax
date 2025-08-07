"""
bradax SDK - Cliente governado para LLM

Interface simples para devs usarem modelos através do hub com
telemetria e guardrails obrigatórios (não desabilitáveis).
"""

# Cliente principal
from .client import BradaxClient

# Telemetry interceptor
from .telemetry_interceptor import (
    TelemetryInterceptor,
    initialize_global_telemetry, 
    get_telemetry_interceptor,
    chat_completion,
    completion
)

# Classes de exceção 
from .exceptions.bradax_exceptions import (
    BradaxError,
    BradaxAuthenticationError,
    BradaxConnectionError,
    BradaxConfigurationError,
    BradaxValidationError,
    BradaxBrokerError
)

# Informações do pacote
__version__ = "1.0.0-governado"
__author__ = "Bradax Development Team"

# Exportar apenas o necessário
__all__ = [
    "BradaxClient",
    "BradaxError",
    "BradaxAuthenticationError", 
    "BradaxConnectionError",
    "BradaxConfigurationError",
    "BradaxValidationError",
    "BradaxBrokerError"
]
