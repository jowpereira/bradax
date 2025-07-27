"""
🏢 Bradax Corporate Client
Cliente corporativo para integração empresarial com a plataforma Bradax.
"""
from typing import Optional, Dict, Any, List
import httpx
from ..exceptions.bradax_exceptions import (
    BradaxError,
    BradaxAuthenticationError,
    BradaxValidationError,
    BradaxNetworkError
)
from ..config.sdk_config import BradaxSDKConfig

try:
    from bradax_constants import NetworkConstants, SecurityConstants
except ImportError:
    # Fallback em caso de problemas com constants
    class NetworkConstants:
        DEFAULT_TIMEOUT = 30
        DEFAULT_RETRIES = 3
    
    class SecurityConstants:
        JWT_EXPIRATION_MINUTES = 15
        API_KEY_PREFIX = "bradax_"


class BradaxCorporateClient:
    """Cliente corporativo para operações empresariais."""
    
    def __init__(self, config: Optional[BradaxSDKConfig] = None):
        """Inicializa cliente corporativo.
        
        Args:
            config: Configuração do SDK (opcional)
        """
        self.config = config or BradaxSDKConfig()
        self.session = None
        self._authenticated = False
    
    async def authenticate(self, api_key: str, project_id: str) -> bool:
        """Autentica cliente com API key corporativa.
        
        Args:
            api_key: Chave de API corporativa
            project_id: ID do projeto
            
        Returns:
            True se autenticação bem-sucedida
            
        Raises:
            BradaxAuthenticationError: Falha na autenticação
        """
        try:
            if not api_key.startswith(SecurityConstants.API_KEY_PREFIX):
                raise BradaxAuthenticationError(
                    f"API key deve começar com '{SecurityConstants.API_KEY_PREFIX}'"
                )
            
            self.session = httpx.AsyncClient(
                timeout=NetworkConstants.DEFAULT_TIMEOUT,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "X-Project-ID": project_id
                }
            )
            
            # Teste de conectividade
            response = await self.session.get(f"{self.config.broker_url}/health")
            response.raise_for_status()
            
            self._authenticated = True
            return True
            
        except httpx.HTTPError as e:
            raise BradaxNetworkError(f"Erro de rede: {e}")
        except Exception as e:
            raise BradaxAuthenticationError(f"Falha na autenticação: {e}")
    
    async def close(self):
        """Fecha sessão do cliente."""
        if self.session:
            await self.session.aclose()


# Classe de compatibilidade com código antigo
BradaxError = BradaxError
BradaxAuthenticationError = BradaxAuthenticationError  
BradaxValidationError = BradaxValidationError


class AuditLogger:
    """Logger de auditoria para operações corporativas."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.logs = []
    
    def log(self, action: str, details: Dict[str, Any]):
        """Registra ação de auditoria.
        
        Args:
            action: Ação realizada
            details: Detalhes da ação
        """
        import datetime
        log_entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "project_id": self.project_id,
            "action": action,
            "details": details
        }
        self.logs.append(log_entry)
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """Retorna logs de auditoria."""
        return self.logs.copy()
