"""
bradax SDK - Runtime de IA generativa seguro e flexível

Este pacote fornece acesso ao Gen-AI Hub da Bradesco Seguros
através de uma API Python simples e poderosa.
"""

__version__ = "0.1.0"
__author__ = "Bradesco Seguros"

from .client.full import Full
from .client.student import Student

__all__ = ["Full", "Student"]
