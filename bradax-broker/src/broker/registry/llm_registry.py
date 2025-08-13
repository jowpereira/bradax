"""
LLM Registry Module

Gerencia registro e validação de modelos LLM disponíveis na plataforma.
Garante que projetos só usem modelos habilitados no hub.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from pathlib import Path

from ..exceptions import (
    ValidationException,
    ConfigurationException,
    StorageException
)

logger = logging.getLogger(__name__)


class LLMModel:
    """Representa um modelo LLM habilitado na plataforma"""

    def __init__(self, model_data: Dict[str, Any]):
        self.model_id = model_data['model_id']
        self.name = model_data['name']
        self.provider = model_data['provider']
        self.model_type = model_data['model_type']
        self.status = model_data['status']
        self.capabilities = model_data.get('capabilities', [])
        self.pricing = model_data.get('pricing', {})
        self.limits = model_data.get('limits', {})
        self.configuration = model_data.get('configuration', {})
        self.security = model_data.get('security', {})
        self.metadata = model_data.get('metadata', {})

    def is_active(self) -> bool:
        """Verifica se o modelo está ativo"""
        # Alguns registros incluem "enabled" explícito; priorizar se presente.
        enabled_flag = self.metadata.get('enabled') if isinstance(self.metadata, dict) else None
        # Campo enabled pode estar na raiz
        root_enabled = getattr(self, 'enabled', None)
        if root_enabled is not None:
            return self.status == 'active' and bool(root_enabled)
        if enabled_flag is not None:
            return self.status == 'active' and bool(enabled_flag)
        return self.status == 'active'

    def supports_capability(self, capability: str) -> bool:
        """Verifica se o modelo suporta uma capacidade específica"""
        return capability in self.capabilities

    def get_cost_per_1k_tokens(self, token_type: str = 'input') -> float:
        """Obtém custo por 1k tokens"""
        key = f"{token_type}_tokens_per_1k"
        return self.pricing.get(key, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'model_id': self.model_id,
            'name': self.name,
            'provider': self.provider,
            'model_type': self.model_type,
            'status': self.status,
            'capabilities': self.capabilities,
            'pricing': self.pricing,
            'limits': self.limits,
            'configuration': self.configuration,
            'security': self.security,
            'metadata': self.metadata
        }


class LLMRegistry:
    """
    Registry de modelos LLM da plataforma - SEM FALLBACKS

    Responsabilidades:
    - Carregamento de modelos disponíveis
    - Validação de modelos usados em projetos
    - Cache controlado de modelos ativos
    - Métricas de uso por modelo
    """

    def __init__(self, data_path: Optional[str] = None):
        """
        Inicializa registry com path obrigatório

        Args:
            data_path: Caminho para diretório de dados (opcional, auto-detecta)

        Raises:
            ConfigurationException: Path não encontrado
        """
        self.data_path = self._resolve_data_path(data_path)
        self.models_file = self.data_path / "llm_models.json"

        # Valida existência obrigatória
        self._validate_registry_integrity()

        # Cache controlado (TTL de 10 minutos)
        self._models_cache: Optional[Dict[str, LLMModel]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 600

        logger.info(f"LLMRegistry inicializado: {self.models_file}")

    def _resolve_data_path(self, data_path: Optional[str]) -> Path:
        """
        Resolve caminho para dados - FALHA SE NÃO ENCONTRAR

        Raises:
            ConfigurationException: Caminho inválido
        """
        if data_path:
            path = Path(data_path)
        else:
            # Auto-detecção a partir do módulo atual usando sistema centralizado
            from ..utils.paths import get_data_dir
            path = get_data_dir()

        if not path.exists():
            raise ConfigurationException(
                f"Diretório de dados não encontrado: {path}",
                severity="CRITICAL",
                details={
                    "attempted_path": str(path),
                    "working_directory": str(Path.cwd()),
                    "current_file": str(Path(__file__))
                }
            )

        return path

    def _validate_registry_integrity(self) -> None:
        """
        Valida integridade do registry - FALHA EXPLICITAMENTE

        Raises:
            StorageException: Arquivos corrompidos ou ausentes
        """
        if not self.models_file.exists():
            raise StorageException(
                f"Arquivo de modelos não encontrado: {self.models_file}",
                storage_type="file",
                operation="validate_integrity",
                resource_id=str(self.models_file)
            )

        try:
            with open(self.models_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                raise StorageException(
                    "llm_models.json deve conter array JSON",
                    storage_type="json",
                    operation="validate_integrity"
                )

            if len(data) == 0:
                raise StorageException(
                    "llm_models.json não pode estar vazio",
                    storage_type="json",
                    operation="validate_integrity"
                )

            logger.info(f"Registry validado: {len(data)} modelos carregados")

        except json.JSONDecodeError as e:
            raise StorageException(
                f"llm_models.json com JSON inválido: {e}",
                storage_type="json",
                operation="validate_integrity"
            )
        except Exception as e:
            raise StorageException(
                f"Erro ao validar registry: {e}",
                storage_type="file",
                operation="validate_integrity"
            )

    def _load_models(self) -> Dict[str, LLMModel]:
        """
        Carrega modelos com cache controlado

        Returns:
            Dict com todos os modelos por model_id

        Raises:
            StorageException: Falha ao carregar dados
        """
        now = datetime.utcnow()

        # Verifica cache válido
        if (self._models_cache is not None and
            self._cache_timestamp is not None and
            (now - self._cache_timestamp).total_seconds() < self._cache_ttl_seconds):
            return self._models_cache

        # Carrega dados frescos
        try:
            with open(self.models_file, 'r', encoding='utf-8') as f:
                models_data = json.load(f)

            # Converte para objetos LLMModel
            models_dict = {}
            for model_data in models_data:
                if 'model_id' not in model_data:
                    logger.warning(f"Modelo sem model_id ignorado: {model_data}")
                    continue

                model = LLMModel(model_data)
                models_dict[model.model_id] = model

            # Atualiza cache
            self._models_cache = models_dict
            self._cache_timestamp = now

            logger.debug(f"Modelos recarregados do registry: {len(models_dict)} modelos")
            return models_dict

        except Exception as e:
            raise StorageException(
                f"Falha ao carregar llm_models.json: {e}",
                storage_type="json",
                operation="load_models"
            )

    def get_model(self, model_id: str) -> LLMModel:
        """
        Obtém modelo específico

        Args:
            model_id: ID do modelo

        Returns:
            LLMModel: Modelo encontrado

        Raises:
            ValidationException: Modelo não encontrado ou inativo
        """
        if not model_id or not isinstance(model_id, str):
            raise ValidationException(
                "model_id deve ser string não vazia",
                field_name="model_id",
                invalid_value=model_id,
                validation_rule="non_empty_string"
            )

        models = self._load_models()

        if model_id not in models:
            available_models = list(models.keys())
            raise ValidationException(
                f"Modelo não encontrado no registry: {model_id}",
                field_name="model_id",
                invalid_value=model_id,
                validation_rule="model_exists_in_registry"
            )

        model = models[model_id]

        if not model.is_active():
            raise ValidationException(
                f"Modelo {model_id} não está ativo",
                field_name="model_status",
                invalid_value=model.status,
                validation_rule="model_must_be_active"
            )

        return model

    def validate_project_model(self, project_model_id: str, project_id: str) -> LLMModel:
        """
        VALIDAÇÃO CRÍTICA: Verifica se modelo do projeto está habilitado na plataforma

        Args:
            project_model_id: ID do modelo configurado no projeto
            project_id: ID do projeto (para logging)

        Returns:
            LLMModel: Modelo validado

        Raises:
            ValidationException: Modelo não habilitado na plataforma
        """
        try:
            model = self.get_model(project_model_id)

            logger.info(f"Projeto {project_id} usando modelo válido: {project_model_id}")
            return model

        except ValidationException as e:
            # Re-lança com contexto específico do projeto
            raise ValidationException(
                f"Projeto {project_id} configurado com modelo não habilitado: {project_model_id}",
                field_name="project_model",
                invalid_value=project_model_id,
                validation_rule="model_must_be_enabled_in_platform"
            )

    def list_active_models(self) -> List[str]:
        """
        Lista IDs de todos os modelos ativos

        Returns:
            List[str]: IDs dos modelos ativos
        """
        models = self._load_models()

        active_models = [
            model_id for model_id, model in models.items()
            if model.is_active()
        ]

        return active_models

    def get_models_by_capability(self, capability: str) -> List[LLMModel]:
        """
        Obtém modelos que suportam uma capacidade específica

        Args:
            capability: Capacidade requerida

        Returns:
            List[LLMModel]: Modelos que suportam a capacidade
        """
        models = self._load_models()

        capable_models = [
            model for model in models.values()
            if model.is_active() and model.supports_capability(capability)
        ]

        return capable_models

    def get_cheapest_models(self, limit: int = 3) -> List[LLMModel]:
        """
        Obtém os modelos mais baratos (por input tokens)

        Args:
            limit: Número máximo de modelos a retornar

        Returns:
            List[LLMModel]: Modelos ordenados por preço
        """
        models = self._load_models()

        active_models = [model for model in models.values() if model.is_active()]

        # Ordena por preço de input tokens
        sorted_models = sorted(
            active_models,
            key=lambda m: m.get_cost_per_1k_tokens('input')
        )

        return sorted_models[:limit]

    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Obtém estatísticas do registry

        Returns:
            Dict com estatísticas dos modelos
        """
        models = self._load_models()

        active_count = len([m for m in models.values() if m.is_active()])
        providers = set(m.provider for m in models.values())
        model_types = set(m.model_type for m in models.values())

        return {
            "total_models": len(models),
            "active_models": active_count,
            "inactive_models": len(models) - active_count,
            "providers": list(providers),
            "model_types": list(model_types),
            "cache_status": {
                "cached": self._models_cache is not None,
                "cache_age_seconds": (
                    (datetime.utcnow() - self._cache_timestamp).total_seconds()
                    if self._cache_timestamp else None
                )
            }
        }

    def invalidate_cache(self) -> None:
        """Invalida cache de modelos forçando reload"""
        self._models_cache = None
        self._cache_timestamp = None
        logger.info("Cache de modelos invalidado")


# Singleton para uso global
_llm_registry: Optional[LLMRegistry] = None


def get_llm_registry() -> LLMRegistry:
    """
    Factory function para LLMRegistry singleton

    Returns:
        LLMRegistry: Instância única do registry
    """
    global _llm_registry

    if _llm_registry is None:
        _llm_registry = LLMRegistry()

    return _llm_registry
