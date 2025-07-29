"""
Middleware de Autenticação Simples para Testes
"""

from fastapi import HTTPException, Header
from typing import Optional


async def get_api_key(authorization: Optional[str] = Header(None)) -> str:
    """
    Validação simples de API key para testes.
    
    Em produção, isso seria muito mais robusto.
    """
    if not authorization:
        raise HTTPException(
            status_code=401, 
            detail="API key requerida no header Authorization"
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Authorization deve ser 'Bearer <api-key>'"
        )
    
    api_key = authorization.replace("Bearer ", "")
    
    # Para testes, aceitar qualquer key que contenha "test"
    if "test" in api_key.lower():
        return api_key
    
    # Simular keys válidas
    valid_keys = ["test-key", "demo-key", "dev-key"]
    
    if api_key in valid_keys:
        return api_key
    
    raise HTTPException(
        status_code=401, 
        detail="API key inválida"
    )
