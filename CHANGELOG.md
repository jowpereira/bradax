# CHANGELOG

## 2025-08-20 - Suporte Multi-Auth JWT por Projeto

### ✅ Concluído

- Implementada derivação determinística de segredo por projeto (v1) usando HMAC-SHA256(master,"bradax-jwt-v1::"+project_id)
- Inclusão de `kid` (p:<project_id>:v1) em tokens e validação estrita sem fallback
- Atualização de scripts para exibir `kid` e compatibilidade preservada
- Ajuste de `projects.json` para assegurar `budget_remaining` em projetos reais
- Logs estruturados `jwt_issue` e `jwt_validate` com `signing_strategy=derived_v1` sem vazamento de segredos
- Documentação atualizada (README, guia sintético) refletindo multi-auth e migração

---
