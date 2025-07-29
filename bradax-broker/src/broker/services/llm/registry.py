"""
LLM Registry Implementation - Bradax Broker

Registro centralizado de modelos LLM com persistência JSON.
"""

import json
import asyncio
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from .interfaces import (
    ILLMRegistry, 
    LLMModelInfo, 
    LLMProviderType, 
    LLMCapability
)


class LLMRegistry(ILLMRegistry):
    """Registry para modelos LLM com persistência JSON"""
    
    def __init__(self, file_path: str = "data/llm_models.json"):
        self.file_path = Path(file_path)
        self.lock = threading.RLock()
        self._ensure_file_exists()
        self._models_cache: Dict[str, LLMModelInfo] = {}
        self._load_models()
    
    def _ensure_file_exists(self):
        """Garante que o arquivo JSON existe"""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write_json([])
    
    def _read_json(self) -> List[Dict[str, Any]]:
        """Lê dados do arquivo JSON"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _write_json(self, data: List[Dict[str, Any]]) -> bool:
        """Escreve dados no arquivo JSON"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Erro ao escrever arquivo {self.file_path}: {e}")
            return False
    
    def _load_models(self):
        """Carrega modelos do arquivo para cache"""
        with self.lock:
            models_data = self._read_json()
            self._models_cache = {}
            
            for model_data in models_data:
                try:
                    # Converter strings de enum de volta para enums
                    provider = LLMProviderType(model_data["provider"])
                    capabilities = [LLMCapability(cap) for cap in model_data["capabilities"]]
                    
                    model = LLMModelInfo(
                        model_id=model_data["model_id"],
                        name=model_data["name"],
                        provider=provider,
                        max_tokens=model_data["max_tokens"],
                        cost_per_1k_input=model_data["cost_per_1k_input"],
                        cost_per_1k_output=model_data["cost_per_1k_output"],
                        capabilities=capabilities,
                        enabled=model_data.get("enabled", True),
                        description=model_data.get("description"),
                        version=model_data.get("version")
                    )
                    
                    self._models_cache[model.model_id] = model
                    
                except (KeyError, ValueError) as e:
                    print(f"Erro ao carregar modelo {model_data}: {e}")
    
    def _save_models(self) -> bool:
        """Salva modelos do cache para arquivo"""
        with self.lock:
            models_data = [model.to_dict() for model in self._models_cache.values()]
            return self._write_json(models_data)
    
    async def _safe_operation(self, operation):
        """Executa operação de forma thread-safe"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, operation)
    
    async def register_model(self, model_info: LLMModelInfo) -> bool:
        """Registra um novo modelo"""
        def _register():
            with self.lock:
                if model_info.model_id in self._models_cache:
                    return False  # Modelo já existe
                
                self._models_cache[model_info.model_id] = model_info
                return self._save_models()
        
        return await self._safe_operation(_register)
    
    async def unregister_model(self, model_id: str) -> bool:
        """Remove um modelo do registro"""
        def _unregister():
            with self.lock:
                if model_id not in self._models_cache:
                    return False  # Modelo não existe
                
                del self._models_cache[model_id]
                return self._save_models()
        
        return await self._safe_operation(_unregister)
    
    async def get_model(self, model_id: str) -> Optional[LLMModelInfo]:
        """Busca informações de um modelo"""
        def _get():
            with self.lock:
                return self._models_cache.get(model_id)
        
        return await self._safe_operation(_get)
    
    async def list_models(self, 
                         provider: Optional[LLMProviderType] = None,
                         capability: Optional[LLMCapability] = None,
                         enabled_only: bool = True) -> List[LLMModelInfo]:
        """Lista modelos disponíveis com filtros"""
        def _list():
            with self.lock:
                models = list(self._models_cache.values())
                
                # Filtrar por habilitado
                if enabled_only:
                    models = [m for m in models if m.enabled]
                
                # Filtrar por provedor
                if provider:
                    models = [m for m in models if m.provider == provider]
                
                # Filtrar por capacidade
                if capability:
                    models = [m for m in models if capability in m.capabilities]
                
                return models
        
        return await self._safe_operation(_list)
    
    async def enable_model(self, model_id: str) -> bool:
        """Habilita um modelo"""
        def _enable():
            with self.lock:
                if model_id not in self._models_cache:
                    return False
                
                self._models_cache[model_id].enabled = True
                return self._save_models()
        
        return await self._safe_operation(_enable)
    
    async def disable_model(self, model_id: str) -> bool:
        """Desabilita um modelo"""
        def _disable():
            with self.lock:
                if model_id not in self._models_cache:
                    return False
                
                self._models_cache[model_id].enabled = False
                return self._save_models()
        
        return await self._safe_operation(_disable)
    
    async def update_model(self, model_id: str, updates: Dict[str, Any]) -> bool:
        """Atualiza informações de um modelo"""
        def _update():
            with self.lock:
                if model_id not in self._models_cache:
                    return False
                
                model = self._models_cache[model_id]
                
                # Aplicar atualizações seguras
                if "name" in updates:
                    model.name = updates["name"]
                if "description" in updates:
                    model.description = updates["description"]
                if "enabled" in updates:
                    model.enabled = updates["enabled"]
                if "max_tokens" in updates:
                    model.max_tokens = updates["max_tokens"]
                if "cost_per_1k_input" in updates:
                    model.cost_per_1k_input = updates["cost_per_1k_input"]
                if "cost_per_1k_output" in updates:
                    model.cost_per_1k_output = updates["cost_per_1k_output"]
                
                return self._save_models()
        
        return await self._safe_operation(_update)
    
    async def get_models_by_provider(self, provider: LLMProviderType) -> List[LLMModelInfo]:
        """Retorna todos os modelos de um provedor específico"""
        return await self.list_models(provider=provider, enabled_only=False)
    
    async def get_models_with_capability(self, capability: LLMCapability) -> List[LLMModelInfo]:
        """Retorna modelos que possuem uma capacidade específica"""
        return await self.list_models(capability=capability)
    
    async def count_models(self) -> Dict[str, int]:
        """Retorna contadores de modelos por status"""
        def _count():
            with self.lock:
                total = len(self._models_cache)
                enabled = len([m for m in self._models_cache.values() if m.enabled])
                disabled = total - enabled
                
                # Contar por provedor
                by_provider = {}
                for model in self._models_cache.values():
                    provider = model.provider.value
                    by_provider[provider] = by_provider.get(provider, 0) + 1
                
                return {
                    "total": total,
                    "enabled": enabled,
                    "disabled": disabled,
                    "by_provider": by_provider
                }
        
        return await self._safe_operation(_count)
    
    async def initialize_default_models(self):
        """Inicializa modelos padrão se o registry estiver vazio"""
        def _initialize():
            with self.lock:
                if self._models_cache:
                    return False  # Já tem modelos
                
                # Modelos OpenAI padrão
                default_models = [
                    LLMModelInfo(
                        model_id="gpt-4o",
                        name="GPT-4 Optimized",
                        provider=LLMProviderType.OPENAI,
                        max_tokens=128000,
                        cost_per_1k_input=0.0025,
                        cost_per_1k_output=0.010,
                        capabilities=[
                            LLMCapability.TEXT_GENERATION,
                            LLMCapability.REASONING,
                            LLMCapability.MULTIMODAL,
                            LLMCapability.FUNCTION_CALLING
                        ],
                        description="Modelo mais avançado da OpenAI"
                    ),
                    LLMModelInfo(
                        model_id="gpt-4o-mini",
                        name="GPT-4 Optimized Mini",
                        provider=LLMProviderType.OPENAI,
                        max_tokens=128000,
                        cost_per_1k_input=0.00015,
                        cost_per_1k_output=0.0006,
                        capabilities=[
                            LLMCapability.TEXT_GENERATION,
                            LLMCapability.FAST_RESPONSE,
                            LLMCapability.CODE_GENERATION
                        ],
                        description="Versão rápida e econômica"
                    )
                ]
                
                for model in default_models:
                    self._models_cache[model.model_id] = model
                
                return self._save_models()
        
        return await self._safe_operation(_initialize)
