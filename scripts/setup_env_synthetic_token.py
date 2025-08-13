"""Setup de ambiente com token sintético para o SDK Bradax.

Objetivo:
 1. Garantir variáveis mínimas no .env (BRADAX_SDK_BROKER_URL, BRADAX_JWT_SECRET se faltar)
 2. Validar presença de OPENAI_API_KEY (ou BRADAX_BROKER_OPENAI_API_KEY)
 3. Gerar API key sintética compatível com storage (contendo api_key_hash do projeto)
 4. Obter JWT via /api/v1/auth/token e expor BRADAX_PROJECT_TOKEN
 5. (Opcional) iniciar broker se não estiver rodando (--start-broker)
 6. (Opcional) gravar token no .env (--write-token) ou apenas exibir export

Uso típico:
  python scripts/setup_env_synthetic_token.py --project-id proj_real_001 --start-broker --write-token

Segurança:
- Não grava OPENAI_API_KEY se ausente (apenas alerta)
- Escrever o JWT no .env é opcional (flag). Avalie risco antes de commitar.
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
from typing import Tuple

import requests

try:  # opcional
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None

ROOT = Path(__file__).resolve().parents[1]
BROKER_DIR = ROOT / "bradax-broker"
ENV_PATH = ROOT / ".env"


def load_env():
    if load_dotenv and ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH)


def ensure_base_env() -> bool:
    """Garante linhas mínimas no .env. Retorna True se houve alteração."""
    changed = False
    existing = {}
    lines = []
    if ENV_PATH.exists():
        raw = ENV_PATH.read_text(encoding="utf-8").splitlines()
        lines = raw[:]
        for l in raw:
            if "=" in l and not l.strip().startswith("#"):
                k, v = l.split("=", 1)
                existing[k.strip()] = v.strip()
    else:
        lines.append("# .env gerado parcialmente pelo setup_env_synthetic_token.py")
        changed = True

    if "BRADAX_SDK_BROKER_URL" not in existing:
        lines.append("BRADAX_SDK_BROKER_URL=http://localhost:8000")
        changed = True

    if "BRADAX_JWT_SECRET" not in existing:
        # Segredo aleatório (hex 32)
        jwt_secret = uuid.uuid4().hex + uuid.uuid4().hex
        lines.append(f"BRADAX_JWT_SECRET={jwt_secret}")
        changed = True

    if changed:
        ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return changed


def require_openai_key():
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("BRADAX_BROKER_OPENAI_API_KEY")):
        print("[ERRO] OPENAI_API_KEY ou BRADAX_BROKER_OPENAI_API_KEY ausente. Defina antes de continuar.")
        print("        Ex.: PowerShell =>  $env:OPENAI_API_KEY='sk-...'\n")
        sys.exit(2)


def pick_project(project_id: str | None) -> Tuple[str, str]:
    data_file = ROOT / "data" / "projects.json"
    if not data_file.exists():
        raise FileNotFoundError(f"projects.json não encontrado em {data_file}")
    projects = json.loads(data_file.read_text(encoding="utf-8"))
    if project_id:
        pdata = projects.get(project_id)
        if not pdata:
            raise SystemExit(f"Projeto {project_id} não encontrado.")
        if pdata.get("status") != "active":
            raise SystemExit(f"Projeto {project_id} não está ativo.")
        return project_id, pdata.get("api_key_hash", "")
    # fallback primeiro ativo
    for pid, pdata in projects.items():
        if pdata.get("status") == "active":
            return pid, pdata.get("api_key_hash", "")
    raise SystemExit("Nenhum projeto ativo em projects.json")


def build_synthetic_api_key(project_id: str, api_key_hash: str) -> str:
    """Constroi API key sintética válida.

    OBS: _parse_api_key espera a ordem (após prefixo):
        0: project_id
        1: organization_id
        2: random_part
        3: timestamp

    Para satisfazer verify_api_key_hash() que aceita stored_hash == hash(api_key)[:16]
    OU stored_hash contido em api_key, embutimos o hash no random_part.
    """
    org = os.getenv("BRADAX_ORG_ID", "org_cli")
    if org == "default":
        org = "orgcli"
    safe_hash = (api_key_hash or "hash").replace(" ", "_")[:12]
    rand = uuid.uuid4().hex[:8]
    random_part = f"{safe_hash}{rand}"  # componente 3
    ts = str(int(time.time()))
    return f"bradax_{project_id}_{org}_{random_part}_{ts}"


def broker_url() -> str:
    return os.getenv("BRADAX_SDK_BROKER_URL", "http://localhost:8000").rstrip("/")


def is_broker_up(url: str) -> bool:
    try:
        r = requests.get(f"{url}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def start_broker_subprocess(env: dict):
    print("[INFO] Iniciando broker em subprocess...")
    return subprocess.Popen(
        [sys.executable, "run.py"],
        cwd=str(BROKER_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def wait_broker(url: str, timeout: int = 40) -> None:
    import time as _t
    start = _t.time()
    last_err = None
    while _t.time() - start < timeout:
        if is_broker_up(url):
            return
        _t.sleep(1)
    raise SystemExit(f"Broker não ficou saudável em {timeout}s. Último erro: {last_err}")


def request_token(url: str, project_id: str, api_key: str) -> str:
    payload = {"project_id": project_id, "api_key": api_key}
    r = requests.post(f"{url}/api/v1/auth/token", json=payload, timeout=15)
    if r.status_code != 200:
        raise SystemExit(f"Falha ao obter token: {r.status_code} {r.text}")
    return r.json()["access_token"]


def write_token_to_env(token: str):
    # Append preservando existente
    lines = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
        # Remove linha antiga de token se houver
        lines = [l for l in lines if not l.startswith("BRADAX_PROJECT_TOKEN=")]
    lines.append(f"BRADAX_PROJECT_TOKEN={token}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args():
    p = argparse.ArgumentParser(description="Setup ambiente com token sintético para SDK")
    p.add_argument("--project-id", help="Projeto alvo (default: primeiro ativo)")
    p.add_argument("--start-broker", action="store_true", help="Iniciar broker se não estiver rodando")
    p.add_argument("--write-token", action="store_true", help="Gravar JWT no .env (cuidado de segurança)")
    p.add_argument("--print-only", action="store_true", help="Apenas exibir export do token, não alterar .env")
    return p.parse_args()


def main():
    args = parse_args()
    load_env()

    changed = ensure_base_env()
    if changed:
        # Recarregar para incluir novos valores
        load_env()

    require_openai_key()

    url = broker_url()

    # Broker
    proc = None
    if not is_broker_up(url):
        if args.start_broker:
            # Montar env para broker
            env = os.environ.copy()
            env.setdefault("PYTHONIOENCODING", "utf-8")
            # Garantir que broker leia mesmo secret
            env.setdefault("BRADAX_JWT_SECRET", os.getenv("BRADAX_JWT_SECRET", uuid.uuid4().hex))
            proc = start_broker_subprocess(env)
            wait_broker(url)
        else:
            print("[ERRO] Broker não acessível e --start-broker não usado.")
            print("       Inicie manualmente ou use --start-broker.")
            sys.exit(3)

    project_id, api_key_hash = pick_project(args.project_id)
    api_key = build_synthetic_api_key(project_id, api_key_hash)
    token = request_token(url, project_id, api_key)

    if args.write_token and not args.print_only:
        write_token_to_env(token)
        print(f"[OK] Token gravado em .env (BRADAX_PROJECT_TOKEN) — projeto: {project_id}")
    elif args.print_only:
        print(f"export BRADAX_PROJECT_TOKEN={token}")
    else:
        print(f"[INFO] Token obtido (não gravado). Use no shell:")
        print(f"  # PowerShell\n  $env:BRADAX_PROJECT_TOKEN='{token}'\n")

    print("Resumo:")
    print(f"  Broker URL: {url}")
    print(f"  Projeto: {project_id}")
    print(f"  API Key sintética: {api_key[:40]}...")
    print(f"  Token (JWT) tamanho: {len(token)}")
    if proc:
        print("[INFO] Broker iniciado em subprocess — mantenha este script aberto se quiser logs.")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
