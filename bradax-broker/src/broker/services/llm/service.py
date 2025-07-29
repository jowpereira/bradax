"""
LLM Service - Bradax Broker

Serviço principal para orquestração de LLMs usando LangChain.
"""

import time
import uuid
from typing import Dict, List, Optional
from datetime import datetime, timezone

from .interfaces import LLMRequest, LLMResponse, LLMModelInfo
from .providers import get_provider, get_available_providers
from .registry import LLMRegistry


class LLMService:
    """Serviço principal de LLM com LangChain"""
    
    def __init__(self):
        try:
            self.providers = get_available_providers()
            self.registry = LLMRegistry()  # Integração do registry para governança
            print(f"✅ LLM Service inicializado com providers: {list(self.providers.keys())}")
            print(f"✅ LLM Registry integrado para governança de modelos")
        except Exception as e:
            print(f"⚠️ Erro ao inicializar LLM Service: {e}")
            self.providers = {}
            self.registry = None
    
    def get_available_models(self) -> List[LLMModelInfo]:
        """Retorna modelos disponíveis"""
        return [
            LLMModelInfo(
                model_id="gpt-3.5-turbo",
                provider_name="openai",
                model_name="GPT-3.5 Turbo",
                context_window=4096,
                max_tokens=4096,
                supports_streaming=True,
                supports_function_calling=True
            )
        ]
    
    async def invoke(self, operation: str, model_id: str, payload: Dict, 
                    project_id: Optional[str] = None, request_id: Optional[str] = None) -> Dict:
        """Método de invocação para LLM"""
        req_id = request_id or str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Obter provider
            provider = get_provider("openai")
            
            # Extrair mensagens
            messages = payload.get("messages", [])
            
            # Invocar
            result_text = provider.invoke(messages)
            
            return {
                "request_id": req_id,
                "success": True,
                "response_text": result_text,
                "model_used": model_id,
                "response_time_ms": int((time.time() - start_time) * 1000)
            }
            
        except Exception as e:
            return {
                "request_id": req_id,
                "success": False,
                "error": str(e),
                "model_used": model_id,
                "response_time_ms": int((time.time() - start_time) * 1000)
            }


# Instância global
llm_service = LLMService()
