"""
bradax SDK - Cliente Python Corporativo Modular

SDK Python profissional com arquitetura modular para comunicação 
segura com o bradax Broker. Elimina hard-code e implementa 
separação clara de responsabilidades.

Arquitetura Modular:
- auth/: Módulo de autenticação e autorização
- http/: Módulo de comunicação HTTP
- validation/: Módulo de validação e compliance
- exceptions/: Módulo de exceções customizadas
- client/: Módulo principal do cliente
- config/: Módulo de configuração

Uso corporativo recomendado:
    from bradax import CorporateBradaxClient, create_client
    
    # Cliente corporativo
    client = CorporateBradaxClient(
        project_token="proj_ti_ai_chatbot_2025_a1b2c3d4",
        broker_url="https://api.bradax.com"
    )
    
    # Ou via factory
    client = create_client(
        project_token="proj_ti_ai_chatbot_2025_a1b2c3d4",
        environment="production"
    )
"""

import os
import sys

# Adicionar o path para bradax-constants se não estiver instalado
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'bradax-constants', 'src'))

try:
    from bradax_constants import OrganizationConstants
    PACKAGE_AUTHOR = OrganizationConstants.PACKAGE_AUTHOR
except ImportError:
    PACKAGE_AUTHOR = "Bradax Development Team"

# Imports principais da arquitetura modular
from .client.corporate_client import (
    CorporateBradaxClient,
    create_client
)

from .auth.project_auth import (
    ProjectAuth,
    ProjectConfig
)

from .validation.audit_logger import AuditLogger
from .validation.compliance_validator import ComplianceValidator

from .exceptions.bradax_exceptions import (
    BradaxException,
    BradaxAuthenticationError,
    BradaxValidationError,
    BradaxNetworkError
)

# Compatibilidade com código legado (DEPRECATED)
from .client.corporate_client import BradaxClient

# Client padrão recomendado
BradaxCorporateClient = CorporateBradaxClient

__version__ = "1.0.0-modular"
__author__ = PACKAGE_AUTHOR
__all__ = [
    # Cliente principal
    "CorporateBradaxClient",
    "BradaxCorporateClient", 
    "create_client",
    
    # Módulos de autenticação
    "ProjectAuth",
    "ProjectConfig",
    
    # Módulos de validação
    "AuditLogger",
    "ComplianceValidator",
    
    # Módulos de exceções
    "BradaxException",
    "BradaxAuthenticationError",
    "BradaxValidationError",
    "BradaxNetworkError",
    
    # Compatibilidade legada
    "BradaxClient"  # DEPRECATED
]
