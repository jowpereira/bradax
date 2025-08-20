# FAQ Arquitetural

## 1. Por que fail-soft (200 + success=false) em vez de 4xx em bloqueios de guardrail?
Para não quebrar integrações iniciais e permitir instrumentação consistente; modo estrito planejado.

## 2. Como adicionar nova regra de guardrail?
Editar `data/guardrails.json` adicionando objeto com `rule_id` único; recarregar engine (`reload_rules`).

## 3. Há dependência em um único provedor de LLM?
Não; adapter atual é abstraído e governança futura permitirá múltiplos.

## 4. O que acontece se o arquivo de guardrails corromper?
Startup falha explicitamente (fail-fast) evitando execução sem proteção.

## 5. Como diferenciar falso positivo de bloqueio legítimo?
Whitelist por regra e futura segunda camada inteligente (opcional) para override.

## 6. Quais metadados mínimos para rastreabilidade?
project_id, client_version, user-agent padronizado; roadmap inclui interaction_id e correlation_id.

## 7. Por que JSON files em vez de banco de dados?
Velocidade de iteração inicial e auditabilidade simples; roadmap inclui storage estruturado.

## 8. Posso trocar o modelo sem redeploy do hub?
Futuro catálogo + policy DSL permitirá; hoje troca exige ajuste no adapter.

## 9. Como medir eficácia dos guardrails?
Taxa de bloqueio, taxa de falso positivo estimada e impacto de sanitizações nas respostas.

## 10. Existe versionamento de regras?
Ainda não; planejado snapshot incremental com diff e rollback.

## 11. Como funcionará fallback de modelo?
Policy engine avaliará métricas recentes; se degradação, alterna para modelo resiliente.

## 12. Como prevenir lock-in tecnológico?
Camada adapter isolada + neutralidade no README e docs (sem nomes explícitos).

---
*Documento gerado automaticamente (FAQ arquitetural)*
