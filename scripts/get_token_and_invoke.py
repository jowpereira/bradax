"""Utility: Obter token JWT real e (opcional) invocar via SDK.

Uso típico (broker já rodando em outro console):
  python scripts/get_token_and_invoke.py --project-id proj_real_001 --prompt "Conte uma piada." --invoke --write-token

Sem invocar (apenas gerar token e mostrar export):
  python scripts/get_token_and_invoke.py --project-id proj_real_001

Flags:
  --project-id <id>   Projeto alvo (default: primeiro ativo em data/projects.json)
  --prompt <texto>    Prompt para invocação (quando --invoke)
  --model <modelo>    Modelo específico (validação simples contra allowed_models)
  --invoke            Após gerar token, executar chamada real via SDK
  --write-token       Persistir BRADAX_PROJECT_TOKEN no .env
  --print-only        Apenas exibir comando de export (não altera .env)

Pré-requisitos:
  - Broker acessível (BRADAX_SDK_BROKER_URL ou http://localhost:8000)
  - OPENAI_API_KEY (ou BRADAX_BROKER_OPENAI_API_KEY) já configurada no processo do broker

Regra API Key Estrita:
  Formato: bradax_<project_id>_<org>_<stored_hash + random>_<timestamp>
  random_part deve iniciar com stored_hash (verify_api_key_hash).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Optional, Tuple

import requests

ROOT = Path(__file__).resolve().parents[1]
PROJECTS_JSON = ROOT / "data" / "projects.json"
ENV_PATH = ROOT / ".env"

# Carregar SDK local
SDK_SRC = ROOT / "bradax-sdk" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))
try:
    from bradax.client import BradaxClient  # type: ignore
except Exception as e:  # pragma: no cover
    print(f"[ERRO] Falha importando SDK: {e}")
    sys.exit(2)


def broker_url() -> str:
    return os.getenv("BRADAX_SDK_BROKER_URL", "http://localhost:8000").rstrip("/")


def is_broker_up(url: str) -> bool:
    try:
        r = requests.get(f"{url}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def load_project(project_id: Optional[str]) -> Tuple[str, dict]:
    if not PROJECTS_JSON.exists():
        raise SystemExit(f"projects.json não encontrado: {PROJECTS_JSON}")
    try:
        data = json.loads(PROJECTS_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"Falha lendo projects.json: {e}")
    if project_id:
        p = data.get(project_id)
        if not p:
            raise SystemExit(f"Projeto {project_id} não existe em projects.json")
        if p.get("status") != "active":
            raise SystemExit(f"Projeto {project_id} não está ativo")
        return project_id, p
    for pid, pdata in data.items():
        if pdata.get("status") == "active":
            return pid, pdata
    raise SystemExit("Nenhum projeto ativo encontrado")


def build_api_key(project_id: str, stored_hash: str, org: str = "orgcli") -> str:
    # Política: organization_id sem underscores para evitar ambiguidade no parsing
    if org == "default":
        org = "orgcli"
    org = org.replace('_', '')  # sanitização
    rand = uuid.uuid4().hex[:8]
    ts = str(int(time.time()))
    random_part = f"{stored_hash}{rand}"  # MUST start with stored_hash
    return f"bradax_{project_id}_{org}_{random_part}_{ts}"


def obtain_token(url: str, project_id: str, api_key: str) -> str:
    payload = {"project_id": project_id, "api_key": api_key}
    r = requests.post(f"{url}/api/v1/auth/token", json=payload, timeout=20)
    if r.status_code != 200:
        raise SystemExit(f"Falha ao obter token ({r.status_code}): {r.text}")
    return r.json()["access_token"]


def write_token(token: str):
    lines = []
    if ENV_PATH.exists():
        lines = [l for l in ENV_PATH.read_text(encoding="utf-8").splitlines() if not l.startswith("BRADAX_PROJECT_TOKEN=")]
    lines.append(f"BRADAX_PROJECT_TOKEN={token}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("[OK] Token gravado no .env")


def invoke(prompt: str, token: str, url: str, model: str):
    client = BradaxClient(project_token=token, broker_url=url, verbose=False)
    info = client.validate_connection()
    print("[VALIDATE]", info)
    result = client.invoke(prompt, model=model, temperature=0.2, max_tokens=96)
    print("\n=== RESPOSTA ===")
    print(result.get("content", result))
    return result


def parse_args():
    p = argparse.ArgumentParser(description="Gerar token estrito e opcionalmente invocar via SDK")
    p.add_argument("--project-id")
    p.add_argument("--prompt", default="Conte uma piada curta sobre vetores.")
    p.add_argument("--model")
    p.add_argument("--invoke", action="store_true")
    p.add_argument("--write-token", action="store_true")
    p.add_argument("--print-only", action="store_true")
    p.add_argument("--org-id", default="orgcli")
    return p.parse_args()


def main():
    args = parse_args()
    url = broker_url()
    if not is_broker_up(url):
        raise SystemExit(f"Broker indisponível em {url}. Certifique-se que está rodando.")

    project_id, pdata = load_project(args.project_id)
    stored_hash = pdata.get("api_key_hash") or "hash"
    api_key = build_api_key(project_id, stored_hash, args.org_id)
    # Validação local estrita do formato antes do POST (defensivo)
    body = api_key[len("bradax_") :]
    tokens = body.split("_")
    if len(tokens) < 4:
        raise SystemExit("API key gerada malformada (tokens insuficientes)")
    ts = tokens[-1]
    if not ts.isdigit():
        raise SystemExit("Timestamp final não numérico")
    expected_tokens = project_id.split('_')
    if tokens[:len(expected_tokens)] != expected_tokens:
        raise SystemExit(
            f"Tokens iniciais não batem com project_id esperado: {tokens[:len(expected_tokens)]} != {expected_tokens}"
        )
    org_index = len(expected_tokens)
    org_token = tokens[org_index]
    if '_' in org_token:
        raise SystemExit(f"organization_id '{org_token}' contém underscore (política estrita)")
    random_tokens = tokens[org_index + 1:-1]
    if not random_tokens:
        raise SystemExit("random_part ausente")
    rand_part = '_'.join(random_tokens)
    if not rand_part.startswith(stored_hash):
        raise SystemExit("random_part não inicia com stored_hash (violação de política)")
    print(f"[API_KEY] {api_key}")

    token = obtain_token(url, project_id, api_key)
    print(f"[TOKEN] obtido (len={len(token)})")

    if args.write_token and not args.print_only:
        write_token(token)
    elif args.print_only:
        print(f"# Export manual PowerShell:\n$env:BRADAX_PROJECT_TOKEN='{token}'")
    else:
        print(f"[INFO] Use para exportar (PowerShell): $env:BRADAX_PROJECT_TOKEN='{token}'")

    if args.invoke:
        model = args.model or (pdata.get("allowed_models") or ["gpt-4.1-nano"])[0]
        invoke(args.prompt, token, url, model)
    else:
        print("[INFO] Pulei invoke (adicione --invoke para chamar o modelo).")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
