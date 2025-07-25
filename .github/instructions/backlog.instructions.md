---
applyTo: "**/*"
priority: 68
---
**GATILHO:** Usuário menciona "backlog", "pendências", ou "próximas tarefas"

**AÇÕES OBRIGATÓRIAS:**

1. **GARANTIR EXISTÊNCIA DO BACKLOG.MD:**
   - Se não existir, criar na raiz do projeto
   - Usar template estruturado por prioridade

2. **COMANDOS ACEITOS:**
   - "adicionar ao backlog: <descrição>"
   - "mover do backlog para todo: <item>"
   - "listar backlog"
   - "priorizar backlog"

3. **OPERAÇÕES:**
   - **ADICIONAR:** Inserir novo item na seção apropriada por prioridade
   - **MOVER PARA TODO:** Criar novo plano baseado no item do backlog
   - **LISTAR:** Mostrar conteúdo atual organizadamente
   - **PRIORIZAR:** Reorganizar itens por urgência/impacto

**TEMPLATE BACKLOG.MD (se não existir):**
```markdown
# Backlog do Projeto

## 🔥 Alta Prioridade
- [ ] Item urgente e importante

## 📋 Média Prioridade  
- [ ] Item importante mas não urgente

## 💡 Baixa Prioridade / Ideias
- [ ] Melhorias futuras
- [ ] Ideias para explorar

## ✅ Concluído (mover para CHANGELOG)
- [x] Item que virou plano de ação

---
*Atualizado automaticamente via sistema de instruções*
```

**SAÍDA:** `BACKLOG.md` atualizado conforme operação solicitada
