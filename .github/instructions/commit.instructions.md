---
applyTo: ".git/**"
mode: commitMessageGeneration
priority: 70
---
• Use Conventional Commits em PT-BR, imperativo, máx. 72 chars.  
• Inclua `close #<id>` ou referência equivalente.  
• **CONSENTIMENTO OBRIGATÓRIO:** NÃO comite sem aprovação explícita do usuário.

**Pré-commit - VALIDAÇÃO OBRIGATÓRIA:**

1. **SOLICITAR CONSENTIMENTO:**
   - Apresentar resumo das mudanças ao usuário
   - Aguardar comando "COMMIT APROVADO" ou similar
   - Se negado, parar processo e aguardar instruções

2. **VALIDAÇÃO TÉCNICA:**
   - Se `.git/` não existir, execute `git init`
   - Localize plano ativo em `/temp-todo/`; exija `done: true`
   - Copie para `docs/memory/snapshots/YYYYMMDD-<slug>.md`

3. **PREPARAÇÃO DO COMMIT:**
   - Gere hash atual com `git rev-parse --short HEAD` (após `git add`, antes do commit)
   - Atualize `docs/memory/index.md` linha correspondente:
     `CONCLUÍDO / SEM COMMIT` → `CONCLUÍDO` e preencha hash
   - Adicione snapshot e index ao stage (`git add`)

**Pós-commit (opcional):**  
remova o plano de `/temp-todo/` ou mova para `/temp-archive/`.
