"""
Serviço de integração com OpenAI

Gerencia comunicação com a API da OpenAI para processamento de LLM.
"""

import os
from typing import Dict, List, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI
import json
import asyncio
from datetime import datetime

class OpenAIService:
    """Serviço para integração com OpenAI API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa o serviço OpenAI.
        
        Args:
            api_key: Chave da API OpenAI (se não fornecida, busca em variável de ambiente)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY não foi fornecida")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        
        # Modelos disponíveis (atualizados com gpt-4.1-nano)
        self.available_models = {
            "gpt-4.1-nano": {
                "max_tokens": 128000,
                "cost_per_1k_input": 0.000025,  # Muito baixo custo
                "cost_per_1k_output": 0.0001,
                "capabilities": ["text", "fast_response"]
            },
            "gpt-4.1-nano-2025-04-14": {
                "max_tokens": 128000,
                "cost_per_1k_input": 0.000025,
                "cost_per_1k_output": 0.0001,
                "capabilities": ["text", "fast_response"]
            },
            "gpt-4.1": {
                "max_tokens": 128000,
                "cost_per_1k_input": 0.003,
                "cost_per_1k_output": 0.012,
                "capabilities": ["text", "reasoning"]
            },
            "gpt-4.1-mini": {
                "max_tokens": 128000,
                "cost_per_1k_input": 0.000150,
                "cost_per_1k_output": 0.000600,
                "capabilities": ["text", "mini"]
            },
            "gpt-4o": {
                "max_tokens": 128000,
                "cost_per_1k_input": 0.005,
                "cost_per_1k_output": 0.015,
                "capabilities": ["text", "vision"]
            },
            "gpt-4o-mini": {
                "max_tokens": 128000,
                "cost_per_1k_input": 0.000150,
                "cost_per_1k_output": 0.000600,
                "capabilities": ["text", "vision"]
            },
            "gpt-3.5-turbo": {
                "max_tokens": 16384,
                "cost_per_1k_input": 0.0005,
                "cost_per_1k_output": 0.0015,
                "capabilities": ["text"]
            }
        }
    
    async def invoke_llm(
        self, 
        model: str, 
        messages: List[Dict[str, Any]], 
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Invoca um modelo LLM de forma síncrona.
        
        Args:
            model: Nome do modelo OpenAI
            messages: Lista de mensagens no formato OpenAI
            parameters: Parâmetros opcionais (temperature, max_tokens, etc)
            
        Returns:
            Resposta do LLM com usage tracking
        """
        
        if model not in self.available_models:
            raise ValueError(f"Modelo {model} não está disponível")
        
        # Parâmetros padrão
        params = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        # Aplicar parâmetros customizados
        if parameters:
            params.update(parameters)
        
        try:
            # Fazer requisição para OpenAI
            response = await self.client.chat.completions.create(**params)
            
            # Calcular custo
            model_info = self.available_models[model]
            input_cost = (response.usage.prompt_tokens / 1000) * model_info["cost_per_1k_input"]
            output_cost = (response.usage.completion_tokens / 1000) * model_info["cost_per_1k_output"]
            total_cost = input_cost + output_cost
            
            return {
                "content": response.choices[0].message.content,
                "model": model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                    "cost_usd": round(total_cost, 6)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "finish_reason": response.choices[0].finish_reason
            }
            
        except Exception as e:
            raise RuntimeError(f"Erro ao chamar OpenAI: {str(e)}")
    
    async def stream_llm(
        self, 
        model: str, 
        messages: List[Dict[str, Any]], 
        parameters: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Invoca um modelo LLM com streaming.
        
        Args:
            model: Nome do modelo OpenAI
            messages: Lista de mensagens no formato OpenAI
            parameters: Parâmetros opcionais
            
        Yields:
            Chunks da resposta em streaming
        """
        
        if model not in self.available_models:
            raise ValueError(f"Modelo {model} não está disponível")
        
        # Parâmetros padrão
        params = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": True
        }
        
        # Aplicar parâmetros customizados
        if parameters:
            params.update(parameters)
        
        try:
            # Stream da OpenAI
            stream = await self.client.chat.completions.create(**params)
            
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield {
                        "delta": chunk.choices[0].delta.content,
                        "finished": False
                    }
                
                # Chunk final com usage (se disponível)
                if chunk.choices[0].finish_reason is not None:
                    # Nota: streaming não retorna usage tokens diretamente
                    # Precisaríamos contar manualmente ou fazer chamada adicional
                    yield {
                        "delta": "",
                        "finished": True,
                        "finish_reason": chunk.choices[0].finish_reason,
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                    
        except Exception as e:
            raise RuntimeError(f"Erro no streaming OpenAI: {str(e)}")
    
    def get_available_models(self) -> Dict[str, Any]:
        """
        Retorna lista de modelos disponíveis.
        
        Returns:
            Dicionário com modelos e suas especificações
        """
        
        models = []
        for model_id, info in self.available_models.items():
            models.append({
                "id": model_id,
                "provider": "openai",
                "max_tokens": info["max_tokens"],
                "cost_per_1k_input": info["cost_per_1k_input"],
                "cost_per_1k_output": info["cost_per_1k_output"],
                "capabilities": info["capabilities"]
            })
        
        return {
            "models": models,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    async def validate_api_key(self) -> bool:
        """
        Valida se a API key está funcionando.
        
        Returns:
            True se válida, False caso contrário
        """
        
        try:
            # Fazer uma chamada simples para validar
            await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception:
            return False
