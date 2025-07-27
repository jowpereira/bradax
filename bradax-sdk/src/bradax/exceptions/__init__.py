"""Pacote de exceções do bradax SDK"""

from .bradax_exceptions import (
    BradaxException,
    BradaxError,  # Alias principal  
    BradaxAuthenticationError,
    BradaxValidationError,
    BradaxNetworkError,
    BradaxConfigurationError,
    BradaxRateLimitError,
    BradaxComplianceError
)

__all__ = [
    "BradaxException",
    "BradaxError",  # Alias
    "BradaxAuthenticationError", 
    "BradaxValidationError",
    "BradaxNetworkError",
    "BradaxConfigurationError",
    "BradaxRateLimitError",
    "BradaxComplianceError"
]
