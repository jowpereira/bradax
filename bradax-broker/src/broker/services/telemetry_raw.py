"""
Utilitários de Telemetria Raw - Bradax Hub (UNIFICADO)

Funções para salvar requests/responses individuais como arquivos JSON
conforme nova arquitetura de telemetria full-stack.

CORRIGIDO: Usa caminho absoluto unificado, sem duplicação de pastas data
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

# USAR constantes unificadas (caminho absoluto)
from ..constants import HubStorageConstants

logger = logging.getLogger(__name__)


def generate_request_id() -> str:
    """Gera UUID único para requisição"""
    return str(uuid.uuid4())


def get_timestamp() -> str:
    """Retorna timestamp ISO atual"""
    return datetime.now(timezone.utc).isoformat()


def save_raw_request(
    request_id: str,
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    project_id: str,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Salva payload de entrada como JSON individual.
    
    Args:
        request_id: UUID da requisição
        prompt: Prompt original (string ou lista de mensagens)
        model: Nome do modelo
        temperature: Parâmetro temperature
        max_tokens: Máximo de tokens
        project_id: ID do projeto
        user_id: ID do usuário (opcional)
        metadata: Dados adicionais (opcional)
        
    Returns:
        bool: True se salvo com sucesso
    """
    try:
        # Criar diretório se não existir
        raw_dir = Path(HubStorageConstants.RAW_REQUESTS_DIR())
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        # Estrutura do payload
        payload = {
            "request_id": request_id,
            "timestamp": get_timestamp(),
            "project_id": project_id,
            "user_id": user_id,
            "model": model,
            "prompt": prompt,
            "parameters": {
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            "metadata": metadata or {}
        }
        
        # Salvar arquivo
        file_path = raw_dir / f"{request_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Request salva: {request_id} -> {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao salvar request {request_id}: {e}")
        return False


def save_raw_response(
    request_id: str,
    response_data: Optional[Dict[str, Any]] = None,
    response_text: Optional[str] = None,
    usage_tokens: Optional[int] = None,
    latency_ms: Optional[float] = None,
    finish_reason: Optional[str] = None,
    model_used: Optional[str] = None,
    status_code: int = 200,
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Salva resposta como JSON individual.
    
    Suporta duas formas de uso:
    1. Parâmetros individuais (legacy)
    2. Dicionário completo via response_data (novo)
    
    Args:
        request_id: UUID da requisição original
        response_data: Dict completo com dados (novo método)
        response_text: Texto da resposta do modelo
        usage_tokens: Tokens consumidos
        latency_ms: Latência em milissegundos
        finish_reason: Razão de finalização
        model_used: Modelo que foi usado
        status_code: Status HTTP (200 = sucesso)
        error_message: Mensagem de erro (se houver)
        metadata: Dados adicionais (opcional)
        
    Returns:
        str: Caminho do arquivo salvo
    """
    try:
        # Criar diretório se não existir
        raw_dir = Path(HubStorageConstants.RAW_RESPONSES_DIR())
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        # Se response_data foi fornecido, usar ele
        if response_data:
            payload = response_data.copy()
            # Garantir que request_id está correto
            payload["request_id"] = request_id
        else:
            # Usar parâmetros individuais (legacy)
            payload = {
                "request_id": request_id,
                "timestamp": get_timestamp(),
                "response_text": response_text,
                "usage_tokens": usage_tokens,
                "latency_ms": latency_ms,
                "finish_reason": finish_reason,
                "model_used": model_used,
                "status_code": status_code,
                "error_message": error_message,
                "metadata": metadata or {},
                "success": status_code == 200 and not error_message
            }
        
        # Salvar arquivo
        file_path = raw_dir / f"{request_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Response raw salvo: {file_path}")
        return str(file_path)
        
    except Exception as e:
        logger.error(f"Erro ao salvar response raw {request_id}: {e}")
        return ""


def save_guardrail_violation(
    request_id: str,
    violation_type: str,
    content_blocked: str,
    rule_triggered: str,
    stage: str,  # "input" ou "output"
    project_id: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Salva violação de guardrail.
    
    Args:
        request_id: UUID da requisição
        violation_type: Tipo de violação
        content_blocked: Conteúdo que foi bloqueado
        rule_triggered: Regra que foi acionada
        stage: "input" ou "output"
        project_id: ID do projeto
        metadata: Dados adicionais
        
    Returns:
        bool: True se salvo com sucesso
    """
    try:
        # Criar diretório se não existir
        raw_dir = Path(HubStorageConstants.RAW_RESPONSES_DIR())
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        # Estrutura da violação
        payload = {
            "request_id": request_id,
            "timestamp": get_timestamp(),
            "event_type": "guardrail_violation",
            "violation_type": violation_type,
            "stage": stage,
            "rule_triggered": rule_triggered,
            "content_blocked": content_blocked[:500],  # Limitar tamanho
            "project_id": project_id,
            "status_code": 403,  # Forbidden
            "metadata": metadata or {}
        }
        
        # Salvar arquivo
        file_path = raw_dir / f"{request_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        
        logger.warning(f"Guardrail violation salva: {request_id} -> {rule_triggered}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao salvar violação {request_id}: {e}")
        return False


def load_raw_request(request_id: str) -> Optional[Dict[str, Any]]:
    """
    Carrega payload de requisição.
    
    Args:
        request_id: UUID da requisição
        
    Returns:
        Dict com dados ou None se não encontrado
    """
    try:
        file_path = Path(HubStorageConstants.RAW_REQUESTS_DIR()) / f"{request_id}.json"
        
        if not file_path.exists():
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    except Exception as e:
        logger.error(f"Erro ao carregar request {request_id}: {e}")
        return None


def load_raw_response(request_id: str) -> Optional[Dict[str, Any]]:
    """
    Carrega resposta.
    
    Args:
        request_id: UUID da requisição
        
    Returns:
        Dict com dados ou None se não encontrado
    """
    try:
        file_path = Path(HubStorageConstants.RAW_RESPONSES_DIR()) / f"{request_id}.json"
        
        if not file_path.exists():
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    except Exception as e:
        logger.error(f"Erro ao carregar response {request_id}: {e}")
        return None


def load_guardrail_violation(request_id: str) -> Optional[Dict[str, Any]]:
    """
    Carrega dados de violação de guardrail.
    
    Args:
        request_id: UUID da requisição com violação
        
    Returns:
        Dict com dados da violação ou None se não encontrado
    """
    try:
        file_path = Path(HubStorageConstants.RAW_REQUESTS_DIR()) / f"{request_id}.json"
        
        if not file_path.exists():
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Verificar se é realmente uma violação de guardrail
        if data.get("event_type") == "guardrail_violation":
            return data
        
        return None
            
    except Exception as e:
        logger.error(f"Erro ao carregar guardrail violation {request_id}: {e}")
        return None


def validate_request_response_pair(request_id: str) -> Dict[str, Any]:
    """
    Valida integridade entre request e response.
    
    Args:
        request_id: UUID da requisição
        
    Returns:
        Dict com resultado da validação
    """
    request_data = load_raw_request(request_id)
    response_data = load_raw_response(request_id)
    
    result = {
        "request_id": request_id,
        "has_request": request_data is not None,
        "has_response": response_data is not None,
        "is_complete": False,
        "issues": []
    }
    
    if not request_data:
        result["issues"].append("Request file missing")
    
    if not response_data:
        result["issues"].append("Response file missing")
    
    if request_data and response_data:
        # Validar correlação
        if request_data.get("request_id") != response_data.get("request_id"):
            result["issues"].append("Request ID mismatch")
        
        # Validar timestamps
        req_time = request_data.get("timestamp")
        resp_time = response_data.get("timestamp")
        if req_time and resp_time and resp_time < req_time:
            result["issues"].append("Response timestamp before request")
    
    result["is_complete"] = len(result["issues"]) == 0
    
    return result


def consolidate_telemetry_to_json(
    request_id: str,
    project_id: str,
    model: str,
    prompt: str,
    response_text: str,
    processing_time_ms: int,
    usage_tokens: Optional[int] = None,
    cost_usd: Optional[float] = None,
    status: str = "success",
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Consolida entrada de telemetria no arquivo telemetry.json principal.
    Fallback quando repositories não estão disponíveis.
    
    Args:
        request_id: UUID da requisição
        project_id: ID do projeto
        model: Modelo usado
        prompt: Prompt original (truncado)
        response_text: Resposta (truncada)
        processing_time_ms: Tempo de processamento
        usage_tokens: Tokens usados
        cost_usd: Custo estimado
        status: Status da operação
        metadata: Dados adicionais
        
    Returns:
        bool: True se salvou com sucesso
    """
    try:
        # Caminho do arquivo de telemetria consolidada
        telemetry_file = Path(HubStorageConstants.DATA_DIR()) / HubStorageConstants.TELEMETRY_FILE
        
        # Criar diretório se não existir
        telemetry_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Carregar dados existentes
        try:
            with open(telemetry_file, 'r', encoding='utf-8') as f:
                telemetry_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            telemetry_data = []
        
        # Criar entrada consolidada
        telemetry_entry = {
            "id": str(uuid.uuid4()),
            "request_id": request_id,
            "project_id": project_id,
            "timestamp": get_timestamp(),
            "model": model,
            "prompt_preview": prompt[:200] + "..." if len(prompt) > 200 else prompt,
            "response_preview": response_text[:200] + "..." if len(response_text) > 200 else response_text,
            "processing_time_ms": processing_time_ms,
            "usage_tokens": usage_tokens,
            "cost_usd": cost_usd,
            "status": status,
            "metadata": metadata or {}
        }
        
        # Adicionar nova entrada
        telemetry_data.append(telemetry_entry)
        
        # Manter apenas últimas 1000 entradas para performance
        if len(telemetry_data) > 1000:
            telemetry_data = telemetry_data[-1000:]
        
        # Salvar arquivo atualizado
        with open(telemetry_file, 'w', encoding='utf-8') as f:
            json.dump(telemetry_data, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Telemetria consolidada salva: {request_id}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao consolidar telemetria {request_id}: {e}")
        return False


def consolidate_guardrail_event_to_json(
    request_id: str,
    project_id: str,
    rule_id: str,
    action: str,
    stage: str,
    content_blocked: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Consolida evento de guardrail no arquivo guardrail_events.json.
    Fallback quando repositories não estão disponíveis.
    
    Args:
        request_id: UUID da requisição
        project_id: ID do projeto
        rule_id: ID da regra violada
        action: Ação tomada (BLOCK, SANITIZE, FLAG)
        stage: Estágio (input, output)
        content_blocked: Conteúdo que foi bloqueado (truncado)
        metadata: Dados adicionais
        
    Returns:
        bool: True se salvou com sucesso
    """
    try:
        # Caminho do arquivo de eventos de guardrails
        guardrail_file = Path(HubStorageConstants.DATA_DIR()) / HubStorageConstants.GUARDRAILS_FILE
        
        # Criar diretório se não existir
        guardrail_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Carregar dados existentes
        try:
            with open(guardrail_file, 'r', encoding='utf-8') as f:
                guardrail_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            guardrail_data = []
        
        # Criar entrada consolidada
        guardrail_entry = {
            "id": str(uuid.uuid4()),
            "request_id": request_id,
            "project_id": project_id,
            "timestamp": get_timestamp(),
            "rule_id": rule_id,
            "action": action,
            "stage": stage,
            "content_preview": content_blocked[:300] + "..." if len(content_blocked) > 300 else content_blocked,
            "metadata": metadata or {}
        }
        
        # Adicionar nova entrada
        guardrail_data.append(guardrail_entry)
        
        # Manter apenas últimas 500 entradas para performance
        if len(guardrail_data) > 500:
            guardrail_data = guardrail_data[-500:]
        
        # Salvar arquivo atualizado
        with open(guardrail_file, 'w', encoding='utf-8') as f:
            json.dump(guardrail_data, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Evento de guardrail consolidado salvo: {request_id}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao consolidar evento de guardrail {request_id}: {e}")
        return False
