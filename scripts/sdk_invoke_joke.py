"""Execução real via SDK (sem fallbacks / sem mocks)

Pré-requisitos:
  1. Broker rodando e acessível em BRADAX_SDK_BROKER_URL (ex: http://localhost:8000)
  2. Token JWT real de projeto exportado em BRADAX_PROJECT_TOKEN
  3. OPENAI_API_KEY configurada (no processo do broker)

Objetivo: Usar SOMENTE o SDK para invocar um LLM pedindo uma piada.

Regras de Estrita Realidade:
  - Nenhum fallback de modelo fixo. Modelo deve estar na lista allowed_models do projeto.
  - Se --model não for passado, seleciona estritamente o primeiro allowed_models do projeto obtido via claims do JWT.
  - Sem chamadas HTTP manuais fora do SDK (exceto leitura local de projects.json).
  - Sem geração de token aqui (token já deve existir).

Uso:
  python scripts/sdk_invoke_joke.py [--model <model>] [--prompt "Conte uma piada curta original sobre IA."]

Exemplo rápido:
  $env:BRADAX_PROJECT_TOKEN='eyJ...' ; python scripts/sdk_invoke_joke.py --model gpt-4.1-nano
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

import jwt  # PyJWT

# Ajusta path para SDK local
ROOT = Path(__file__).resolve().parents[1]
SDK_SRC = ROOT / "bradax-sdk" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))
from bradax.client import BradaxClient  # type: ignore

PROJECTS_JSON = ROOT / "data" / "projects.json"


def require_env(var: str) -> str:
    val = os.getenv(var)
    if not val:
        raise SystemExit(f"Variável de ambiente obrigatória ausente: {var}")
    return val


def load_projects() -> Dict[str, Any]:
    if not PROJECTS_JSON.exists():
        raise SystemExit(f"projects.json não encontrado em {PROJECTS_JSON}")
    try:
        return json.loads(PROJECTS_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"Falha lendo projects.json: {e}")


def extract_project_id(token: str) -> str:
    try:
        # Decodifica sem verificar assinatura (somente para extrair claims não sensíveis)
        payload = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
    except Exception as e:
        raise SystemExit(f"Não foi possível decodificar JWT para extrair project_id: {e}")
    pid = payload.get("sub") or payload.get("project_id") or payload.get("projectId")
    if not pid:
        raise SystemExit("project_id não encontrado nas claims do token (sub | project_id | projectId)")
    return pid


def select_model(project_id: str, projects: Dict[str, Any], requested: str | None) -> str:
    pdata = projects.get(project_id)
    if not pdata:
        raise SystemExit(f"Projeto {project_id} não encontrado em projects.json")
    allowed = pdata.get("allowed_models") or []
    if not allowed:
        raise SystemExit(f"Projeto {project_id} sem allowed_models configurado")
    if requested:
        if requested not in allowed:
            raise SystemExit(f"Modelo '{requested}' não permitido. Allowed: {allowed}")
        return requested
    # Estritamente o primeiro
    return allowed[0]


def run(prompt: str, model: str, token: str, broker_url: str):
    client = BradaxClient(project_token=token, broker_url=broker_url.rstrip("/"), verbose=False)
    info = client.validate_connection()  # se falhar, exceção direta
    print("Conexão validada:", info)
    result = client.invoke(prompt, model=model, temperature=0.2, max_tokens=96)
    print("\n=== Resposta do Modelo ===")
    print(result.get("content", result))


def parse_args():
    p = argparse.ArgumentParser(description="Invocar LLM pedindo piada (real)")
    p.add_argument("--model", help="Modelo permitido (validação estrita)")
    p.add_argument("--prompt", default="Conte uma piada curta original sobre IA.")
    return p.parse_args()


def main():
    args = parse_args()
    token = require_env("BRADAX_PROJECT_TOKEN")
    broker_url = os.getenv("BRADAX_SDK_BROKER_URL", "http://localhost:8000")

    project_id = extract_project_id(token)
    projects = load_projects()
    model = select_model(project_id, projects, args.model)

    run(args.prompt, model, token, broker_url)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
