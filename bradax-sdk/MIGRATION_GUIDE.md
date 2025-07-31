# 🔄 Guia de Migração - Bradax SDK v2.0

## ⚠️ Métodos Deprecados (Funcionam com Warnings)

### Factory Method - Configuração

```python
# ❌ DEPRECADO (ainda funciona com warning)
config = BradaxSDKConfig.for_integration_tests(...)

# ✅ RECOMENDADO - Nome mais apropriado
config = BradaxSDKConfig.for_testing(...)
```

## ❌ Métodos Removidos (Substituições)

### Execução de LLM

```python
# ❌ REMOVIDO: run_llm()
response = client.run_llm("prompt", model="gpt-4")

# ✅ USE: invoke() - Interface LangChain
response = client.invoke("prompt", config={"model": "gpt-4"})
```

### Compatibilidade LangChain

```python
# ❌ REMOVIDO: run_langchain()
response = client.run_langchain("chat", inputs={"prompt": "..."})

# ✅ USE: invoke() ou ainvoke() - Padrão LangChain
response = client.invoke("...")
response = await client.ainvoke("...")
```

### Métodos Duplicados

```python
# ❌ REMOVIDOS: Duplicatas consolidadas
# invoke_generic() duplicado
# generate_text() duplicado

# ✅ USE: Versões originais mantidas
client.invoke_generic(operation="chat", model="gpt-4", payload={...})
client.generate_text("prompt", model="gpt-4")
```

## 🎯 Interface Recomendada (v2.0)

### Principal - LangChain Compatível
```python
# Método principal síncrono
response = client.invoke("Seu prompt aqui")

# Método principal assíncrono  
response = await client.ainvoke("Seu prompt aqui")
```

### Utilitários Mantidos
```python
# Para operações avançadas
client.invoke_generic(operation="batch", model="gpt-4", payload={...})

# Para geração simples de texto
client.generate_text("prompt", model="gpt-4", temperature=0.7)

# Para verificação de saúde
client.check_broker_health()
```

## 🏗️ Configuração Moderna

```python
# Produção - Validações rigorosas
config = BradaxSDKConfig.for_production(
    broker_url="https://api.bradax.com",  # HTTPS obrigatório
    project_id="seu-projeto",
    api_key="sua-api-key"                 # Obrigatório
)

# Desenvolvimento - Flexível
config = BradaxSDKConfig.for_development(
    broker_url="http://localhost:8000"
)

# Testes - Nome apropriado
config = BradaxSDKConfig.for_testing(
    broker_url="http://localhost:8000",
    project_id="test-projeto"
)
```

## 📈 Benefícios da Migração

### ✅ Interface Limpa
- **50% menos métodos** (consolidação de duplicatas)
- Interface focada em `invoke()` e `ainvoke()`
- Compatibilidade 100% LangChain

### ✅ Nomenclaturas Profissionais
- `for_testing()` em vez de `for_integration_tests()`
- Métodos específicos por ambiente
- Validações adequadas para produção

### ✅ Compatibilidade Mantida
- Métodos deprecados funcionam com warnings
- Migração gradual possível
- Zero breaking changes imediatos

## 🚀 Próximos Passos

1. **Atualize imports**: Use novos factory methods
2. **Substitua métodos**: `run_llm()` → `invoke()`
3. **Teste interface**: Valide compatibilidade LangChain
4. **Remove warnings**: Migre métodos deprecados

**Resultado**: Interface moderna, limpa e 100% LangChain-compatível! 🎉
