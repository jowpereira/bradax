# Bradax SDK

Cliente Python oficial para integração segura com o Bradax Broker.

## ✅ Caminho Único Autorizado para LLM
A partir desta versão, **apenas `BradaxClient.invoke()`** é permitido para chamadas de modelos LLM. Todos os outros métodos diretos ou alternativos foram removidos ou bloqueados por política de segurança.

Métodos bloqueados:
- `ainvoke()` → Levanta `BradaxConfigurationError`
- `generate_text()` → Removido
- `invoke_generic()` → Tornou-se interno (`_invoke_generic`)
- `TelemetryInterceptor.chat_completion()` / `completion()` / `intercept_llm_request()` → Bloqueados

Qualquer tentativa de uso resultará em exceção iniciando com o prefixo de segurança: `🚨 Segurança:`

## 🔒 Autenticação Obrigatória
É obrigatório fornecer um token de projeto válido via:
- Parâmetro `project_token` do construtor, ou
- Variável de ambiente `BRADAX_PROJECT_TOKEN`

Tokens placeholders (ex: `test-project-token`) são rejeitados com `BradaxAuthenticationError`.

## 🚀 Exemplo de Uso
```python
from bradax.client import BradaxClient

client = BradaxClient(project_token="seu-token-real", broker_url="http://localhost:8000")
resp = client.invoke("Explique o princípio de menor privilégio em 2 linhas.", model="gpt-4.1-nano")
print(resp["content"])
```

## 📋 Telemetria & Auditoria
- Telemetria não pode ser desabilitada.
- Headers obrigatórios são injetados automaticamente.
- Toda requisição gera request_id e é auditada end-to-end no broker.

## ⚠️ Erros Comuns
| Cenário | Exceção |
|---------|---------|
| Falta de token | BradaxConfigurationError |
| Token placeholder | BradaxAuthenticationError |
| Uso de ainvoke | BradaxConfigurationError |
| Tentativa de via alternativa (interceptor) | BradaxConfigurationError |

## 🧪 Testes Inclusos
Arquivo: `tests/test_sdk_restrictions.py` valida:
- Sucesso de `invoke`
- Bloqueio de `ainvoke`
- Bloqueio de métodos do interceptor
- Erros de token ausente / placeholder

## 🛡️ Política
A consolidação em torno de um único ponto de entrada possibilita:
- Auditoria determinística
- Menor superfície de bypass
- Aplicação consistente de guardrails

## 🔄 Evolução Futura
- Reintrodução de operação assíncrona (ainvoke) apenas após camada de auditoria assíncrona dedicada.

---
*Documento gerado automaticamente como parte do plano de restrição do SDK.*
