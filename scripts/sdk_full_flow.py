"""End-to-end SDK Flow

Gera API key estrita (sem fallback), obtém JWT, valida conexão via SDK e invoca o modelo.

Fluxo: Broker (já rodando ou opcional --start-broker) -> /auth/token -> SDK.validate_connection -> SDK.invoke

Requisitos:
  - Broker acessível em BRADAX_SDK_BROKER_URL (default http://localhost:8000)
  - OPENAI_API_KEY exportada (ou BRADAX_BROKER_OPENAI_API_KEY)
  - Projeto existente em data/projects.json com api_key_hash

Uso rápido:
  python scripts/sdk_full_flow.py --project-id proj_real_001 --prompt "Conte uma piada." --write-token

Opções:
  --start-broker  : tenta iniciar broker se não estiver no ar
  --write-token   : persiste BRADAX_PROJECT_TOKEN no .env
  --model         : modelo (default: primeiro allowed_models)
  --org-id        : organização (default: orgcli)

Segurança: JWT só é gravado em .env se --write-token for usado.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
import subprocess
from pathlib import Path
from typing import Optional

import requests

try:  # opcional
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
BROKER_DIR = ROOT / "bradax-broker"
PROJECTS_JSON = ROOT / "data" / "projects.json"

# Ajustar sys.path para SDK local
SDK_SRC = ROOT / "bradax-sdk" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))
from bradax.client import BradaxClient  # type: ignore


def load_env():
    if load_dotenv and ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH)


def ensure_env_base():
    changed = False
    existing = {}
    lines = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
        for l in lines:
            if "=" in l and not l.strip().startswith("#"):
                k, v = l.split("=", 1)
                existing[k.strip()] = v.strip()
    else:
        changed = True
    if "BRADAX_SDK_BROKER_URL" not in existing:
        lines.append("BRADAX_SDK_BROKER_URL=http://localhost:8000")
        changed = True
    if changed:
        ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if load_dotenv:
        load_dotenv(dotenv_path=ENV_PATH)


def broker_url() -> str:
    return os.getenv("BRADAX_SDK_BROKER_URL", "http://localhost:8000").rstrip("/")


def is_broker_up(url: str) -> bool:
    try:
        r = requests.get(f"{url}/health", timeout=3, allow_redirects=True)
        return r.status_code == 200
    except Exception:
        return False


def start_broker() -> subprocess.Popen:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("BRADAX_JWT_SECRET", uuid.uuid4().hex)
    print("[INFO] Iniciando broker...")
    proc = subprocess.Popen(
        [sys.executable, "run.py"],
        cwd=str(BROKER_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Aguardar saudável
    for _ in range(40):
        if is_broker_up(broker_url()):
            return proc
        time.sleep(1)
    raise SystemExit("Broker não ficou saudável em 40s")


def load_project(project_id: Optional[str]):
    if not PROJECTS_JSON.exists():
        raise SystemExit(f"projects.json não encontrado: {PROJECTS_JSON}")
    data = json.loads(PROJECTS_JSON.read_text(encoding="utf-8"))
    if project_id:
        proj = data.get(project_id)
        if not proj:
            raise SystemExit(f"Projeto {project_id} não existe")
        if proj.get("status") != "active":
            raise SystemExit(f"Projeto {project_id} não está ativo")
        return project_id, proj
    # fallback primeiro ativo
    for pid, pdata in data.items():
        if pdata.get("status") == "active":
            return pid, pdata
    raise SystemExit("Nenhum projeto ativo em projects.json")


def build_api_key(project_id: str, org_id: str, stored_hash: str) -> str:
    # Estrita: random_part inicia com stored_hash
    rand = uuid.uuid4().hex[:8]
    ts = str(int(time.time()))
    random_part = f"{stored_hash}{rand}"  # verify_api_key_hash exige startswith
    return f"bradax_{project_id}_{org_id}_{random_part}_{ts}"


def request_token(url: str, project_id: str, api_key: str) -> str:
    payload = {"project_id": project_id, "api_key": api_key}
    r = requests.post(f"{url}/api/v1/auth/token", json=payload, timeout=20)
    if r.status_code != 200:
        raise SystemExit(f"Falha token {r.status_code}: {r.text}")
    return r.json()["access_token"]


def write_token(token: str):
    lines = []
    if ENV_PATH.exists():
        lines = [l for l in ENV_PATH.read_text(encoding="utf-8").splitlines() if not l.startswith("BRADAX_PROJECT_TOKEN=")]
    lines.append(f"BRADAX_PROJECT_TOKEN={token}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("[OK] Token gravado em .env")


def invoke_via_sdk(token: str, url: str, prompt: str, model: str):
    client = BradaxClient(project_token=token, broker_url=url, verbose=False)
    info = client.validate_connection()
    print("[OK] validate_connection =>", info)
    result = client.invoke(prompt, model=model, temperature=0.2, max_tokens=128)
    print("[RESP]")
    print(result.get("content", result))


def parse_args():
    p = argparse.ArgumentParser(description="Fluxo completo: API key -> token -> SDK.invoke")
    p.add_argument("--project-id")
    p.add_argument("--org-id", default="orgcli")
    p.add_argument("--prompt", default="Diga 'OK' em uma frase curta.")
    p.add_argument("--model")
    p.add_argument("--write-token", action="store_true")
    p.add_argument("--start-broker", action="store_true")
    return p.parse_args()


def require_openai_key():
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("BRADAX_BROKER_OPENAI_API_KEY")):
        raise SystemExit("OPENAI_API_KEY ausente. Exporte antes de continuar.")


def main():
    args = parse_args()
    load_env()
    ensure_env_base()
    require_openai_key()

    url = broker_url()
    proc = None
    if not is_broker_up(url):
        if args.start_broker:
            proc = start_broker()
        else:
            raise SystemExit("Broker indisponível. Use --start-broker ou suba manualmente.")

    project_id, pdata = load_project(args.project_id)
    stored_hash = pdata.get("api_key_hash") or "hash"
    org_id = args.org_id
    if org_id == "default":
        org_id = "orgcli"

    api_key = build_api_key(project_id, org_id, stored_hash)
    print(f"[API_KEY] {api_key}")

    token = request_token(url, project_id, api_key)
    print("[OK] Token obtido (JWT tamanho:", len(token), ")")

    if args.write_token:
        write_token(token)
    else:
        print("[INFO] Exporte manualmente se quiser reutilizar:")
        print(f"  # PowerShell\n  $env:BRADAX_PROJECT_TOKEN='{token}'")

    model = args.model or (pdata.get("allowed_models") or ["gpt-4.1-nano"])[0]
    invoke_via_sdk(token, url, args.prompt, model)

    if proc:
        print("[INFO] Broker iniciado por este script continua rodando (PID:", proc.pid, ")")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
