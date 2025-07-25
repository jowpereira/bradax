---
applyTo: "**/*"
priority: 85
---
**GATILHO:** Atualização de progresso detectada em plano ativo

**AÇÕES OBRIGATÓRIAS:**

1. **DETECTAR PLANO ATIVO:**
   - Buscar arquivo em `/workspace-plans/active/` que corresponde ao contexto atual
   - Verificar se há atualização no "Registro de Progresso"

2. **AVALIAR STATUS DO CHECKLIST:**
   - Contar subtarefas marcadas [x] vs total de subtarefas
   - Se 100% concluído → EXECUTAR FINALIZAÇÃO IMEDIATA

3. **FINALIZAÇÃO ATÔMICA SIMPLIFICADA (se aplicável):**
   ```
   ETAPA 1: Marcar como done + validated
   ETAPA 2: MOVER para /workspace-plans/completed/
   ETAPA 3: Atualizar docs/memory/index.md (PENDENTE → CONCLUÍDO)
   ETAPA 4: Adicionar entrada no CHANGELOG.md
   ETAPA 5: Confirmar sucesso
   ```

4. **EXECUÇÃO EM BLOCO:**
   - Todas as 5 etapas devem ser executadas sequencialmente
   - Não parar entre etapas
   - Debug mantido em /workspace-debug/[alias]/ para decisão futura do usuário
   - Reportar status final consolidado

**REGRA CRÍTICA:** Esta instrução tem prioridade mais alta que archive/validation para garantir execução imediata.

**SAÍDA:** Operação completa executada em uma única interação
