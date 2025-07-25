---
applyTo: "**/*"
priority: 77
---
**GATILHO:** `done: true` detectado no front-matter (APENAS VALIDAÇÃO, NÃO EXECUÇÃO)

**FUNÇÃO:** Esta instrução apenas VALIDA. A execução fica com finalization.instructions.md

**AÇÕES DE VALIDAÇÃO:**

1. **VALIDAR ESTRUTURA DO PLANO:**
   - Verificar se existe seção "📌 Registro de Progresso" com pelo menos 1 entrada
   - Verificar se existe seção "☑️ Checklist de Subtarefas" com todas marcadas [x]
   - Verificar se existe timestamp válido no cabeçalho

2. **VALIDAR DEPENDÊNCIAS:**
   - Confirmar que `/docs/memory/index.md` existe
   - Confirmar que `/workspace-plans/completed/` existe
   - Confirmar que pasta debug `/workspace-debug/[alias]/` existe

3. **RESULTADO DA VALIDAÇÃO:**
   - SE VALIDAÇÃO PASSOU: Retornar `validation_status: "PASSED"`
   - SE VALIDAÇÃO FALHOU: Retornar `validation_status: "FAILED"` + lista de erros

**IMPORTANTE:** Esta instrução NÃO executa arquivamento. Apenas valida e informa o resultado.
