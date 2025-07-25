---
applyTo: "**/*"
priority: 90
---
Quando o usuário pedir um **plano** (ou não existir plano ativo):

1. **DIÁLOGO COLABORATIVO OBRIGATÓRIO:**
   - Faça perguntas detalhadas para entender completamente a tarefa:
     * Qual o objetivo específico?
     * Há restrições técnicas ou de negócio?
     * Quais são os critérios de sucesso mensuráveis?
     * Há dependências ou pré-requisitos?
     * Qual a prioridade/urgência?
   - Continue o diálogo até ter clareza completa da tarefa

2. **CRIAÇÃO DO PLANO:**
   - Copie `.github/templates/plano-acao.md` → `/workspace-plans/active/YYYYMMDD-HHmmss-<slug>.md`
   - Preencha `<Título da Tarefa>`, `<resumo da solicitação>`, timestamps
   - Consulte o horário UTC atual da máquina local

3. **ESTRUTURAÇÃO DETALHADA:**
   - Gere automaticamente a seção **☑️ Checklist de Subtarefas** baseada no diálogo
   - Gere alias para debug: `[projeto]-[area]-debug`
   - Crie pasta debug: `/workspace-debug/[alias]/`
   - Crie arquivo `_PLANO_REF.md` na pasta debug com referência cruzada
   - Inclua métricas específicas e testes baseados nos critérios discutidos

4. **REGISTRO:**
   - Acrescente linha em `docs/memory/index.md`:

```

\| YYYY-MM-DD | \<Título da Tarefa> | PENDENTE | — |

```

5. **VALIDAÇÃO FINAL DO PLANO:**
   - Apresente o plano estruturado ao usuário para aprovação
   - Ajuste conforme feedback antes de marcar como ativo
