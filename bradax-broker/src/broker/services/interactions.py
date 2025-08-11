"""Interactions Tracking - Bradax Broker

Registra estágios de cada requisição LLM em data/interactions.json para auditoria.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from ..utils.paths import get_data_dir


_lock = threading.RLock()
_MAX_ENTRIES = 5000

# Flag global para registrar eventos 'pass' (padrão: False)
INTERACTIONS_LOG_PASS_EVENTS = False

def _file_path() -> Path:
    return get_data_dir() / "interactions.json"

def _ensure_file():
    fp = _file_path()
    if not fp.exists():
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    return fp

def append_interaction_stage(request_id: str, project_id: str, stage: str, summary: str, extra: Optional[Dict[str, Any]] = None) -> bool:
    import uuid
    try:
        # Determinar se deve registrar evento 'pass'
        is_pass = False
        result = None
        guardrail_type = None
        action = None
        metadata = None
        # Permitir que extra contenha campos padronizados
        if extra:
            result = extra.pop("result", None)
            guardrail_type = extra.pop("guardrail_type", None)
            action = extra.pop("action", None)
            metadata = extra.pop("metadata", None)
            is_pass = (result == "pass")
        # Só registra eventos 'pass' se flag estiver True
        if is_pass and not INTERACTIONS_LOG_PASS_EVENTS:
            return False
        fp = _ensure_file()
        with _lock:
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                data = []
            entry = {
                "interaction_id": str(uuid.uuid4()),
                "request_id": request_id,
                "project_id": project_id,
                "stage": stage,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "summary": summary[:160],
                "result": result,
                "guardrail_type": guardrail_type,
                "action": action,
                "metadata": metadata,
                "extra": extra or {}
            }
            data.append(entry)
            if len(data) > _MAX_ENTRIES:
                data = data[-_MAX_ENTRIES:]
            with open(fp, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

__all__ = ["append_interaction_stage"]
