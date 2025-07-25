# Índice de Templates e Prompts

## 📋 Templates para Planos e Execução
| Arquivo | Categoria | Usuário | Prioridade | Descrição |
|---------|-----------|---------|------------|-----------|
| `plano-acao.md` | planning | assistente | alta | Template principal para criação de planos de trabalho |

## 🔧 Templates de Debugging e Análise
| Arquivo | Categoria | Usuário | Prioridade | Descrição |
|---------|-----------|---------|------------|-----------|
| `debugging-analysis.md` | debugging | assistente | alta | Análise estruturada de problemas e causa raiz |
| `troubleshooting-tecnico.md` | debugging | assistente | alta | Processo sistemático de resolução de problemas técnicos |
| `analise-tecnica-interna.md` | internal-template | assistente | alta | Análise técnica detalhada para implementação |
| `checklist-execucao.md` | internal-template | assistente | média | Validação de subtarefas durante execução |

## 🎯 Prompts para Usuário
| Arquivo | Categoria | Usuário | Prioridade | Descrição |
|---------|-----------|---------|------------|-----------|
| `novo-plano.prompt.md` | prompt | usuario | alta | Criação de novo plano de ação |
| `correcao-rota.prompt.md` | user-prompt | usuario | alta | Comandos para ajustar plano ativo |
| `instrucoes-rapidas.prompt.md` | user-prompt | usuario | média | Instruções rápidas durante execução |
| `controle-commits.prompt.md` | user-prompt | usuario | alta | Controle de commits e atualizações críticas |

## 📊 Uso por Categoria

### 🔥 Alta Prioridade (Uso Frequente)
- **Planejamento:** `plano-acao.md`, `novo-plano.prompt.md`
- **Debugging:** `debugging-analysis.md`, `troubleshooting-tecnico.md`
- **Controle:** `correcao-rota.prompt.md`, `controle-commits.prompt.md`
- **Análise:** `analise-tecnica-interna.md`

### 📋 Média Prioridade (Uso Situacional)
- **Execução:** `checklist-execucao.md`
- **Comunicação:** `instrucoes-rapidas.prompt.md`

## 🎯 Guia de Uso

### Para o Usuário:
1. **Criar novo plano:** Use `novo-plano.prompt.md`
2. **Ajustar plano ativo:** Use `correcao-rota.prompt.md`
3. **Dar instruções rápidas:** Use `instrucoes-rapidas.prompt.md`
4. **Controlar commits:** Use `controle-commits.prompt.md`

### Para o Assistente:
1. **Analisar problemas:** Use `debugging-analysis.md` ou `troubleshooting-tecnico.md`
2. **Avaliar implementação:** Use `analise-tecnica-interna.md`
3. **Validar execução:** Use `checklist-execucao.md`
4. **Criar planos:** Use `plano-acao.md`

---
*Atualizado automaticamente. Para adicionar novos templates, siga o padrão de categorização.*
