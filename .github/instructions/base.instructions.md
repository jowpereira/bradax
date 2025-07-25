---
applyTo: "**/*"
priority: 100
---
**Antes de responder:**

1. **VERIFICAÇÃO OBRIGATÓRIA DE PLANO ATIVO:**
   - Abra `docs/memory/index.md` e identifique se há plano PENDENTE
   - Se não houver plano ativo, PARE e proponha criar novo plano detalhado
   - Se houver plano ativo, abra o arquivo correspondente em `/workspace-plans/active/`

2. **GARANTIR INFRAESTRUTURA:**
   - Garanta a existência das pastas `/workspace-plans/active/`, `docs/memory/`, `/workspace-debug/`
   - Se plano ativo, verificar pasta debug `/workspace-debug/[alias]/`
   
3. **REGISTRAR PROGRESSO (apenas se plano ativo):**
   - Adicione nova linha em **Registro de Progresso**:

```

\| <ISO-datetime> | \<ação resumida> | \<observações> |
```

```

_Isso deve acionar a atualização automática do Checklist._

4. **VALIDAÇÃO COLABORATIVA:**
   - Para execução de subtarefas, sempre confirme com usuário antes de implementar
   - Para commits/documentação, solicite consentimento explícito
```
