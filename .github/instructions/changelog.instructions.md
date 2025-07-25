---
applyTo: "**/*"
priority: 60
mode: utility
---
**FUNÇÃO:** Utilitário para atualização do CHANGELOG (chamado por finalization.instructions.md)

**GATILHO:** Chamado programaticamente durante finalização de plano

**TEMPLATE PARA EXECUÇÃO:**

1. **EXTRAIR DADOS DO PLANO:**
   - Título da tarefa (linha após "# Plano de Ação —")
   - Data de criação (timestamp do cabeçalho)  
   - Data de conclusão (último timestamp do Registro de Progresso)

2. **FORMATAR ENTRADA:**
   ```
   ## [YYYY-MM-DD] - <Título da Tarefa>
   ### ✅ Concluído
   - <Resumo simplificado da tarefa>
   ```

3. **ATUALIZAR CHANGELOG.MD:**
   - Inserir no TOPO (após cabeçalho)
   - Manter ordem cronológica reversa

**IMPORTANTE:** Esta instrução não executa automaticamente. É chamada por finalization.instructions.md
