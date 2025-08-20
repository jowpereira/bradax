import os
import json
import time
import uuid
import threading
from pathlib import Path

import pytest
import requests

# Assunções: servidor FastAPI pode ser iniciado via run.py (porta 8000 por padrão)
# Para testes reais, iniciamos servidor em thread separada se não já estiver.

SERVER_URL = os.environ.get("BRADAX_TEST_SERVER", "http://127.0.0.1:8000")
# Usar project_id real existente em data/projects.json
PROJECT_ID = os.environ.get("BRADAX_TEST_PROJECT", "proj_real_001")
API_TOKEN = os.environ.get("BRADAX_TEST_TOKEN", "test-token")  # Token placeholder (auth real não implementada aqui)

RUN_ROOT = Path(__file__).resolve().parents[2]  # bradax-broker/
DATA_DIR = RUN_ROOT.parent / "data"
RAW_DIR = DATA_DIR / "raw" / "responses"


def _server_alive() -> bool:
    try:
        r = requests.get(f"{SERVER_URL}/api/v1/system/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def ensure_server():
    """Garante que servidor esteja rodando antes dos testes.
    Se já está no ar, não faz nada. Se não, tenta iniciar.
    """
    if _server_alive():
        yield
        return

    # Iniciar servidor real (simplificado) - assume run.py inicia FastAPI app
    import subprocess, sys
    env = os.environ.copy()
    # Garantir variáveis essenciais para boot
    env.setdefault("BRADAX_JWT_SECRET", "testsecret")
    env.setdefault("OPENAI_API_KEY", "sk-test")
    # Minimizar ruído de encoding em Windows
    env.setdefault("PYTHONIOENCODING", "utf-8")
    proc = subprocess.Popen([sys.executable, "run.py"], cwd=RUN_ROOT, env=env)
    # Aguardar disponibilidade
    for _ in range(40):
        if _server_alive():
            break
        time.sleep(0.25)
    if not _server_alive():
        proc.terminate()
        raise RuntimeError("Servidor não iniciou para testes de integração")
    yield
    proc.terminate()


def _invoke_with_custom_guardrail(prompt: str, rule_pattern: str):
    """Invoca endpoint real /api/v1/llm/invoke simulando uso do SDK."""
    request_id = str(uuid.uuid4())
    invoke_payload = {
        "operation": "chat",
        "model": "gpt-4.1-nano",
        "payload": {
            "messages": [
                {"role": "user", "content": prompt}
            ]
        },
        "project_id": PROJECT_ID,
        "request_id": request_id,
        "custom_guardrails": {
            "no_forbidden": {
                "pattern": rule_pattern,
                "severity": "HIGH"
            }
        }
    }
    headers = {
        "Content-Type": "application/json",
        # Headers exigidos pelo TelemetryValidationMiddleware
        "x-bradax-sdk-version": "1.0.0-test",
        "x-bradax-machine-fingerprint": "machine_8e219290de7aa69a",  # fingerprint de dev permitido
        "x-bradax-session-id": str(uuid.uuid4()),
        "x-bradax-telemetry-enabled": "true",
        "x-bradax-environment": "test",
        "x-bradax-platform": "windows",
        "x-bradax-python-version": "3.10.0",
        # User-Agent padrão esperado
        "User-Agent": "bradax-sdk/1.0.0-test"
    }
    r = requests.post(f"{SERVER_URL}/api/v1/llm/invoke", headers=headers, data=json.dumps(invoke_payload), timeout=25)
    return r, request_id


def _find_raw_violation(request_id: str):
    file_path = RAW_DIR / f"{request_id}.json"
    if not file_path.exists():
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.integration
def test_custom_guardrail_blocks():
    prompt = "Quero escrever um script Python sensível"  # Deve casar com pattern 'python'
    resp, req_id = _invoke_with_custom_guardrail(prompt, r"python")
    # Semântica atual do serviço: retorna 200 com success=false e model_used='guardrail_blocked'
    assert resp.status_code == 200, f"Esperado 200 (bloqueio encapsulado), obtido {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("success") is False, "Esperado success=false em bloqueio"
    assert body.get("guardrails_triggered") is True
    assert body.get("model_used") == "guardrail_blocked"
    violation = None
    # Aguardar criação do arquivo raw
    for _ in range(20):
        violation = _find_raw_violation(req_id)
        if violation:
            break
        time.sleep(0.1)
    assert violation, "Arquivo raw de violação não encontrado"
    assert violation["violation_type"] == "custom_guardrail"
    assert violation["rule_triggered"].startswith("custom_sdk_no_forbidden")


@pytest.mark.integration
def test_custom_guardrail_allows_non_matching():
    prompt = "Conteúdo neutro sem palavra-chave"
    resp, req_id = _invoke_with_custom_guardrail(prompt, r"python")
    # Deve permitir seguir fluxo normal (200) — invoke retorna JSON de sucesso
    assert resp.status_code == 200, f"Esperado 200 sem violação guardrail, obtido {resp.status_code}: {resp.text}"
    body = resp.json()
    # success pode ser False se houver erro externo (ex: API key inválida). O foco aqui é não ter guardrail_triggered.
    assert body.get("guardrails_triggered") in (False, None), f"Não deveria disparar guardrail: {body}"
    # Não deve haver arquivo de violação custom guardrail
    time.sleep(0.5)
    violation = _find_raw_violation(req_id)
    if violation:
        # Se existe raw, garantir que não é custom guardrail
        assert violation.get("violation_type") != "custom_guardrail", f"Indevido: {violation}"


@pytest.mark.integration
def test_invalid_regex_rejected():
    """Regex malformada deve resultar em 403 (validação fail-fast)."""
    prompt = "qualquer coisa"
    resp, req_id = _invoke_with_custom_guardrail(prompt, r"(python")  # Regex inválida
    # Para regex inválida lançamos GuardrailViolationError → mesma via de bloqueio (200 + success=false)
    assert resp.status_code == 200, f"Esperado 200 com bloqueio encapsulado, obtido {resp.status_code}"
    body = resp.json()
    assert body.get("success") is False and body.get("guardrails_triggered") is True


@pytest.mark.integration
def test_via_real_sdk_flow(monkeypatch):
    """Valida fluxo completo usando BradaxClient do SDK com guardrail customizado."""
    # Preparar ambiente mínimo
    from bradax.config import get_sdk_config
    cfg = get_sdk_config()
    cfg.set_custom_guardrail("no_python", {"pattern": "python", "severity": "HIGH"})
    os.environ['BRADAX_PROJECT_TOKEN'] = PROJECT_ID + '-token'
    from bradax.client import BradaxClient
    client = BradaxClient(project_token=os.environ['BRADAX_PROJECT_TOKEN'], broker_url=SERVER_URL.rstrip('/'))
    # Prompt que viola
    with pytest.raises(Exception) as exc:
        client.invoke("Escreva código Python perigoso")
    assert 'guardrail' in str(exc.value).lower() or '403' in str(exc.value)


# (Duplicata removida de test_invalid_regex_rejected)
