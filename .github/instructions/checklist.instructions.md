---
applyTo: "**/*"
priority: 80
---
**GATILHO:** Sempre que atualizar **Registro de Progresso**

**AÇÕES OBRIGATÓRIAS:**

1. **VALIDAÇÃO PRÉ-MARCAÇÃO:**
   - Use template `checklist-execucao.md` para validar subtarefa
   - Confirme que todos os critérios foram atendidos
   - Obtenha aprovação explícita do usuário antes de marcar [x]

2. **ATUALIZAR CHECKLIST:**
   - Abrir seção **☑️ Checklist de Subtarefas**
   - Marcar `[x]` nas subtarefas correspondentes à ação realizada
   - Registrar observações importantes no progresso

3. **CHECKPOINT INCREMENTAL:**
   - Para cada subtarefa marcada, criar checkpoint no debug
   - Documentar decisões técnicas tomadas
   - Validar que não há efeitos colaterais

4. **SE TODAS AS SUBTAREFAS ESTÃO MARCADAS [x]:**
   - Adicionar ao front-matter: `done: true`
   - Criar ou atualizar seção:
     ```md
     ## ✅ Conclusão
     - Todas as subtarefas concluídas em <ISO-datetime>.
     ```

5. **EXECUTAR FLUXO SIMPLIFICADO DE FINALIZAÇÃO:**
   - **VALIDAR PLANO:** Verificar estrutura e dependências
   - **SE VALIDAÇÃO OK:** Adicionar `validated: true` + `validation_date`
   - **ARQUIVAMENTO ÚNICO:** MOVER para /workspace-plans/completed/ (não copiar)
   - **ATUALIZAR ÍNDICE:** docs/memory/index.md: PENDENTE → CONCLUÍDO
   - **MANTER DEBUG:** Preservar /workspace-debug/[alias]/ para decisão futura
4. **VERIFICAÇÃO FINAL:**

   - Confirmar que todas as operações foram executadas com sucesso
   - Reportar status completo das operações

**REGRA:** NÃO cole o checklist inteiro no chat; execute e salve apenas nos arquivos.

**SAÍDA:** Plano completamente processado e arquivado em uma única operação
