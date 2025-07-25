---
category: user-prompt
usage: usuario
priority: high
---

# Controle de Commit e Documentação

**USO:** Comandos para aprovar ou negar alterações críticas.

## Comandos de Commit:

### Aprovar Commit:
```
COMMIT APROVADO: [mensagem opcional do commit]
```

### Negar Commit:
```
COMMIT NEGADO: [motivo da negação]
```

### Commit Condicional:
```
COMMIT SE: [condições que devem ser atendidas primeiro]
```

## Comandos de Documentação:

### Aprovar Atualização:
```
DOC APROVADO: Atualizar [arquivo] conforme planejado
```

### Negar Atualização:
```
DOC NEGADO: Não atualizar [arquivo] - [motivo]
```

### Revisão Necessária:
```
DOC REVISAR: [arquivo] precisa de [ajustes específicos] antes da atualização
```

## Comandos de Arquivo:

### Aprovar Criação:
```
ARQUIVO APROVADO: Criar [nome do arquivo]
```

### Negar Criação:
```
ARQUIVO NEGADO: Não criar [nome do arquivo] - [motivo]
```

### Modificação Condicional:
```
ARQUIVO SE: Criar [nome] apenas se [condições]
```

**RESULTADO:** O assistente respeitará a decisão e só prosseguirá com aprovação explícita.
