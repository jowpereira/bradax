"""Teste de integração real do BradaxClient com projeto cadastrado.

Pré-requisitos via .env (não commitado):
- BRADAX_JWT_SECRET=<segredo>
- OPENAI_API_KEY ou BRADAX_BROKER_OPENAI_API_KEY=<sua_chave>

O teste:
1. Inicia o broker local se /health não responder.
2. Autentica no /api/v1/auth/token com projeto real de data/projects.json.
3. Usa o JWT no BradaxClient para executar invoke() sem mocks.
"""
import json
import os
import time
import uuid
import subprocess
import sys
import requests
import pytest

from bradax.client import BradaxClient

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BROKER_URL = os.getenv("BRADAX_SDK_BROKER_URL", "http://localhost:8000")
BROKER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "bradax-broker")


def _load_real_project_and_model():
    # raiz do workspace -> data/projects.json
    root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_file = os.path.join(root, "data", "projects.json")
    with open(data_file, "r", encoding="utf-8") as f:
        projects = json.load(f)
    for pid, pdata in projects.items():
        if pdata.get("status") == "active":
            model = (pdata.get("allowed_models") or ["gpt-4.1-nano"])[0]
            # Capturar o hash esperado pelo storage para validar a API key
            api_key_hash = pdata.get("api_key_hash") or ""
            return pid, model, api_key_hash
    raise AssertionError("Nenhum projeto ativo encontrado em data/projects.json")


def _ensure_broker_running(timeout=60):
    try:
        r = requests.get(f"{BROKER_URL}/health", timeout=2)
        if r.status_code == 200:
            return None  # já está rodando, não iniciar subprocess
    except Exception:
        pass

    env = os.environ.copy()
    # Garantir ambos nomes de env para compatibilidade
    jwt_secret = os.getenv("BRADAX_JWT_SECRET") or os.getenv("JWT_SECRET") or uuid.uuid4().hex
    env["BRADAX_JWT_SECRET"] = jwt_secret
    env["JWT_SECRET"] = jwt_secret
    # Ajudar resolução de paths do broker para encontrar /data
    workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    env.setdefault("BRADAX_PROJECT_ROOT", workspace_root)
    # Forçar UTF-8 no stdout/stderr do Python para evitar UnicodeEncodeError em Windows
    env.setdefault("PYTHONIOENCODING", "utf-8")
    # Chave OpenAI deve vir do .env local; não fornecemos default inseguro
    if not (env.get("OPENAI_API_KEY") or env.get("BRADAX_BROKER_OPENAI_API_KEY")):
        raise RuntimeError("OPENAI_API_KEY/BRADAX_BROKER_OPENAI_API_KEY não definido no ambiente")

    proc = subprocess.Popen(
        [sys.executable, "run.py"],
        cwd=BROKER_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    start = time.time()
    last_err = None
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{BROKER_URL}/health", timeout=2)
            if r.status_code == 200:
                return proc
        except Exception as e:
            last_err = e
        time.sleep(1)
    # falhou subir
    try:
        # Capturar logs para diagnóstico
        stdout, stderr = proc.communicate(timeout=2)
    except Exception:
        stdout, stderr = b"", b""
    try:
        proc.terminate()
    except Exception:
        pass
    err_msg = (
        f"Broker não subiu em {timeout}s: {last_err}\n"
        f"STDOUT:\n{stdout.decode(errors='ignore')}\n"
        f"STDERR:\n{stderr.decode(errors='ignore')}\n"
    )
    raise RuntimeError(err_msg)


def _obter_jwt(project_id: str, api_key_hash: str) -> str:
    # Monta API key VÁLIDA pelo storage: contém o hash do projeto dentro da key
    # projects.json usa api_key_hash: ex. 'hash_proj1' — basta conter no corpo
    org = "org_tests"
    # Incorporar o hash esperado (ambiental/teste) para satisfazer verify_api_key_hash
    safe_hash = (api_key_hash or "hash").replace(" ", "_")
    random_part = f"{safe_hash}_{uuid.uuid4().hex[:8]}"
    ts = str(int(time.time()))
    api_key = f"bradax_{project_id}_{org}_{random_part}_{ts}"

    payload = {"project_id": project_id, "api_key": api_key}
    resp = requests.post(f"{BROKER_URL}/api/v1/auth/token", json=payload, timeout=10)
    if resp.status_code != 200:
        raise AssertionError(f"Falha ao autenticar projeto: {resp.status_code} {resp.text}")
    data = resp.json()
    return data["access_token"]


@pytest.mark.integration
@pytest.mark.sdk
def test_sdk_invoke_simple_real_project():
    project_id, model, api_key_hash = _load_real_project_and_model()

    proc = _ensure_broker_running()
    try:
        token = _obter_jwt(project_id, api_key_hash)
        client = BradaxClient(project_token=token, broker_url=BROKER_URL, verbose=False)

        validation = client.validate_connection()
        assert validation, "Sem retorno de validação"

        result = client.invoke("Return number 42 only.", model=model, max_tokens=5, temperature=0.1)

        assert isinstance(result, dict), "Resultado não é dict"
        assert "content" in result, "Campo content ausente"
        assert result["content"].strip() != "", "Resposta vazia"
        meta = result.get("response_metadata", {})
        assert meta.get("request_id"), "request_id ausente (telemetria)"
        assert meta.get("model") == model, "Modelo retornado divergente"
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
