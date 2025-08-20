# Guia: Setup Rápido com Token Sintético e Execução do SDK

Este guia mostra como preparar o ambiente local, gerar um token JWT sintético (válido para o fluxo atual) e executar uma chamada real via SDK ao broker já rodando.

## 1. Pré-requisitos

- Python instalado
- Dependências instaladas (`pip install -r bradax-broker/requirements.txt` se ainda não fez)
- Chave OpenAI válida exportada localmente (não commitada):
  - PowerShell:

    ```powershell
    $env:OPENAI_API_KEY = "sk-..."
    ```

- (Opcional) `python-dotenv` já presente pela requirements do broker.

## 2. Estrutura Relevante

```text
/scripts
  setup_env_synthetic_token.py   # Gera API key sintética, obtém JWT e ajusta .env
  sdk_full_flow.py               # Fluxo completo: gera API key, obtém token e invoca (tudo em 1)
  real_sdk_invoke.py             # Usa SOMENTE o SDK (token já existente)
  sdk_invoke_joke.py             # Versão mínima: usa token e pede uma piada real
/data/projects.json              # Fonte dos projetos ativos (api_key_hash)
```

## 3. Iniciar o Broker

Abra um terminal dedicado:

```powershell
cd bradax-broker
# (Opcional) definir secret se quiser fixo
$env:BRADAX_JWT_SECRET = (New-Guid).Guid
python .\run.py
```

Deixe rodando. Verifique se não há erros críticos (providers / guardrails).

## 4. Gerar Token Sintético

Em outro terminal na raiz do projeto:

```powershell
# Caso ainda não tenha .env ou queira gerar automaticamente
python scripts\setup_env_synthetic_token.py --project-id proj_real_001 --write-token
```

Explicação rápida:

- Detecta/gera `.env` com `BRADAX_SDK_BROKER_URL` e `BRADAX_JWT_SECRET` (se ausentes)
- Lê `data/projects.json` para pegar `api_key_hash`
- Monta API key sintética contendo o hash
- Chama `/api/v1/auth/token` para obter JWT
- Se `--write-token`, adiciona `BRADAX_PROJECT_TOKEN` no `.env`

Sem gravar o token (apenas mostrar export):

```powershell
python scripts\setup_env_synthetic_token.py --project-id proj_real_001 --print-only
```

Iniciando broker automaticamente (caso não esteja rodando) + gravando token:

```powershell
python scripts\setup_env_synthetic_token.py --start-broker --write-token
```

## 5. Regra Estrita SEM Fallback

O backend agora valida API keys sintéticas com regra rígida:

```text
random_part.startswith(stored_hash)
```

Formato: `bradax_<project_id>_<org>_<stored_hash + randomSuffix>_<timestamp>`

Sem substrings parciais, sem tolerância. Se o hash não for o prefixo imediato do penúltimo componente, a autenticação falha.

### (Novo) Multi-Auth JWT por Projeto (v1)

Agora cada token é assinado com segredo derivado do `project_id` (HMAC-SHA256) e inclui `kid` no header (`p:<project_id>:v1`). Tokens antigos antes de 2025-08-19 devem ser regenerados. Scripts já exibem o `kid` obtido.

## 6. Usar o SDK para Invocar

Se gravou o token no `.env`, basta:

```powershell
python scripts\real_sdk_invoke.py --prompt "Return only number 42." --model gpt-4.1-nano
```

Se usou `--print-only`, exporte primeiro:

```powershell
$env:BRADAX_PROJECT_TOKEN = "<TOKEN_AQUI>"
python scripts\real_sdk_invoke.py --prompt "Return only number 42." --model gpt-4.1-nano
```

Opcional (piada rápida real):

```powershell
python scripts\sdk_invoke_joke.py --prompt "Conte uma piada curta sobre vetores."
```

Saída esperada (exemplo simplificado):

```text
Conexão OK -> {"valid": true, "project_id": "proj_real_001", ...}
Resposta:
42
```

## 7. Flags Importantes (setup_env_synthetic_token.py)

| Flag | Descrição |
|------|-----------|
| `--project-id` | Força um projeto específico (senão usa o primeiro ativo) |
| `--start-broker` | Sobe o broker em subprocess se não estiver rodando |
| `--write-token` | Grava BRADAX_PROJECT_TOKEN no `.env` |
| `--print-only` | Exibe comando de export e não altera `.env` |

## 8. Flags (Outros Scripts)

| Script | Flags Principais | Observação |
|--------|------------------|------------|
| `sdk_full_flow.py` | `--project-id`, `--org-id`, `--prompt`, `--write-token`, `--start-broker` | Faz tudo (gera API key estrita, token e invoca) |
| `real_sdk_invoke.py` | `--prompt`, `--model`, `--max-tokens`, `--temperature` | Requer token já exportado |
| `sdk_invoke_joke.py` | `--prompt`, `--model` | Foco em invocar uma piada real |

## 9. Boas Práticas de Segurança

- Não commitar `.env` com tokens reais.
- Prefira `--print-only` em ambientes compartilhados.
- Regere a API key sintética sempre que necessário; ela só precisa conter o hash para passar na verificação.

## 10. Troubleshooting

| Problema | Causa Provável | Ação |
|----------|----------------|------|
| Broker não sobe / fica fechando | Falta OPENAI_API_KEY ou BRADAX_JWT_SECRET | Verifique variáveis antes de iniciar |
| 401 no validate_connection | Token expirado ou inválido | Gere novo token com o script |
| Erro de modelo não suportado | Modelo passado não listado no projeto | Use primeiro da lista `allowed_models` do projeto |
| Resposta vazia | Provider indisponível ou falha OpenAI | Checar logs do broker e variável de chave |

## 11. Fluxo Resumido

1. Exportar OPENAI_API_KEY
2. Rodar broker (`run.py`) ou usar `sdk_full_flow.py --start-broker`
3. Gerar token sintético (`setup_env_synthetic_token.py --write-token`) ou usar fluxo tudo-em-um
4. Invocar via SDK (`real_sdk_invoke.py` / `sdk_invoke_joke.py` / parte final do full flow)

---

*Documento gerado automaticamente para auxiliar operação local com token sintético.*
