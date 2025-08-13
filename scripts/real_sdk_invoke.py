"""bradax SDK Demo CLI

Script mínimo QUE USA SOMENTE O SDK (sem requests diretos ao broker) para:
1. Validar configuração ambiente (.env broker URL)
2. Consumir um token de projeto JÁ GERADO (BRADAX_PROJECT_TOKEN) — não gera token
3. Rodar validate_connection() e invoke() pelo BradaxClient

NÃO faz chamadas REST manuais /auth/token ou /health. Toda interação passa pelo SDK.

Pré-requisitos que você precisa preparar fora do script:
- Broker rodando (ex: http://localhost:8000)
- Token JWT real exportado: BRADAX_PROJECT_TOKEN=<jwt_do_projeto>
    (Se não existir, o script falha e explica como obter.)

Uso:
    python scripts/real_sdk_invoke.py --prompt "Hello" [--model gpt-4.1-nano]

Opcionalmente o script lê data/projects.json apenas para sugerir modelo default
se você não passar --model (NÃO usa para autenticação).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

try:  # dotenv é opcional
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None

# Ajustar sys.path para permitir import local do SDK quando executado do repo
ROOT = Path(__file__).resolve().parents[1]
SDK_SRC = ROOT / "bradax-sdk" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from bradax.client import BradaxClient  # type: ignore


def ensure_env_file():
    """Garante .env com BRADAX_SDK_BROKER_URL se ausente (não grava tokens / JWT)."""
    env_path = ROOT / ".env"
    defaults = {"BRADAX_SDK_BROKER_URL": os.getenv("BRADAX_SDK_BROKER_URL", "http://localhost:8000")}

    # Carregar .env existente
    existing = {}
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()
        except Exception:
            pass

    changed = False
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    # Assegurar broker URL
    if "BRADAX_SDK_BROKER_URL" not in existing:
        lines.append(f"BRADAX_SDK_BROKER_URL={defaults['BRADAX_SDK_BROKER_URL']}")
        changed = True

    # Criar arquivo se não existe ou atualizar
    if not env_path.exists() or changed:
        header = [
            "# bradax SDK .env (gerado/ajustado automaticamente)",
            "# Ajuste BRADAX_SDK_BROKER_URL conforme necessário.",
            "# Opcional: BRADAX_PROJECT_TOKEN=<token_jwt_do_projeto> (não é gravado automaticamente)",
        ]
        content = "\n".join(header + lines) + "\n"
        env_path.write_text(content, encoding="utf-8")

    # Carregar variáveis
    if load_dotenv:
        load_dotenv(dotenv_path=env_path)


def read_projects():
    data_file = ROOT / "data" / "projects.json"
    if not data_file.exists():
        raise FileNotFoundError(f"Arquivo de projetos não encontrado: {data_file}")
    with data_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def choose_default_model() -> str:
    """Retorna primeiro modelo permitido do primeiro projeto ativo (fallback se --model ausente)."""
    try:
        projects = read_projects()
        for _, pdata in projects.items():
            if pdata.get("status") == "active":
                return (pdata.get("allowed_models") or ["gpt-4.1-nano"])[0]
    except Exception:
        pass
    return "gpt-4.1-nano"


def broker_url() -> str:
    return os.getenv("BRADAX_SDK_BROKER_URL", "http://localhost:8000").rstrip("/")


def require_project_token() -> str:
    token = os.getenv("BRADAX_PROJECT_TOKEN")
    if not token:
        raise SystemExit(
            "BRADAX_PROJECT_TOKEN ausente. Exporte um token JWT real antes de executar.\n"
            "Exemplo PowerShell:\n  $env:BRADAX_PROJECT_TOKEN='eyJhbGciOi...'\n"
            "(Token deve ser emitido previamente pelo fluxo corporativo — este script não gera.)"
        )
    return token


def main():
    parser = argparse.ArgumentParser(description="Invocar broker via SDK com projeto real")
    parser.add_argument("--prompt", required=True, help="Prompt para o modelo")
    parser.add_argument("--model", help="Modelo (default: primeiro permitido em projects.json)")
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--temperature", type=float, default=0.2)
    args = parser.parse_args()

    # .env básico
    ensure_env_file()

    url = broker_url()
    token = require_project_token()
    default_model = choose_default_model()
    model = args.model or default_model

    # Instanciar SDK (único ponto de integração HTTP)
    client = BradaxClient(project_token=token, broker_url=url, verbose=False)

    # Usa somente método do SDK para validar conectividade + auth
    try:
        info = client.validate_connection()
    except Exception as e:  # Captura para mensagem amigável
        raise SystemExit(f"Falha validate_connection(): {e}")
    print("Conexão OK ->", info)

    # Invoke via SDK
    try:
        result = client.invoke(
            args.prompt,
            model=model,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )
    except Exception as e:
        raise SystemExit(f"Falha invoke(): {e}")

    print("Resposta:")
    print(result.get("content", result))


if __name__ == "__main__":
    # Forçar UTF-8 para facilitar saída em Windows
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
