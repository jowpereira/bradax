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
        from .interfaces import LLMProviderType, LLMCapability
        
        return [
            LLMModelInfo(
                model_id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                provider=LLMProviderType.OPENAI,
                max_tokens=4096,
                cost_per_1k_input=0.0015,
                cost_per_1k_output=0.002,
                capabilities=[LLMCapability.TEXT_GENERATION, LLMCapability.CODE_GENERATION],
                enabled=True,
                description="OpenAI's GPT-3.5 Turbo model"
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
            
            # Processar entrada: suportar tanto messages (LangChain) quanto prompt (legado)
            if "messages" in payload:
                messages = payload["messages"]
            elif "prompt" in payload:
                # Converter prompt string para formato messages
                messages = [{"role": "user", "content": payload["prompt"]}]
            else:
                raise ValueError("Either 'messages' or 'prompt' must be provided")
            
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
