"""Pacote de exceções do bradax SDK"""

from .bradax_exceptions import (
    BradaxException,
    BradaxAuthenticationError,
    BradaxValidationError,
    BradaxNetworkError,
    BradaxConfigurationError,
    BradaxRateLimitError,
    BradaxComplianceError,
    create_exception_from_http_status
)

__all__ = [
    "BradaxException",
    "BradaxAuthenticationError", 
    "BradaxValidationError",
    "BradaxNetworkError",
    "BradaxConfigurationError",
    "BradaxRateLimitError",
    "BradaxComplianceError",
    "create_exception_from_http_status"
]
