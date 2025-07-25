---
category: user-prompt
usage: usuario
priority: medium
---

# Instruções Rápidas Durante Execução

**USO:** Comandos rápidos durante execução de tarefas.

## Comandos de Contexto:

### Adicionar Informação:
```
CONTEXTO: [informação adicional relevante para a tarefa atual]
```

### Restrição Adicional:
```
RESTRICAO: [nova restrição que deve ser considerada]
```

### Validação Específica:
```
VALIDAR: [aspecto específico] antes de prosseguir
```

## Comandos de Controle:

### Checkpoint Manual:
```
CHECKPOINT: Parar aqui e mostrar resultado parcial
```

### Aprovação Rápida:
```
APROVADO: Continuar com a próxima subtarefa
```

### Solicitar Detalhes:
```
DETALHAR: [aspecto específico da tarefa atual]
```

## Comandos de Debug:

### Arquivo de Debug:
```
DEBUG: Criar arquivo [nome] na pasta de debug com [conteúdo]
```

### Log de Processo:
```
LOG: [observação para registrar no debug]
```

### Análise Técnica:
```
ANALISAR: [componente/código] para identificar [aspecto]
```

**RESULTADO:** O assistente executará o comando e continuará a tarefa incorporando a instrução.
