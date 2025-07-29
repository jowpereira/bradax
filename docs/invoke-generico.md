# Método invoke_generic - Wrapper LangChain Bradax

## Visão Geral

O método `invoke_generic()` é o ponto central de integração entre o SDK bradax e o wrapper LangChain. Ele fornece uma interface única e flexível para executar diferentes tipos de operações LLM, mantendo todos os guardrails, telemetria e governança centralizados no hub.

## Características Principais

### 🔧 **Flexibilidade Total**
- Suporte a múltiplas operações: `chat`, `completion`, `batch`, `stream`, `embedding`
- Payload completamente customizável para diferentes necessidades
- Compatibilidade com qualquer formato de entrada do LangChain

### 🛡️ **Governança Centralizada**
- Guardrails aplicados automaticamente pelo hub (não contornáveis)
- Telemetria extensiva e obrigatória
- Autenticação e autorização por projeto
- Auditoria completa de todas as operações

### 📊 **Telemetria Automática**
- Rastreamento de tempo de resposta
- Contagem de tokens utilizados
- Logs estruturados de erros e sucessos
- Métricas de performance por projeto

## Interface do Método

### SDK (Cliente)

```python
def invoke_generic(
    self,
    operation: str,          # Tipo de operação
    model_id: str,          # ID do modelo
    payload: Dict[str, Any], # Payload flexível
    request_id: Optional[str] = None  # ID opcional
) -> Dict[str, Any]:
```

### Broker (Serviço)

```python
async def invoke_generic(
    self,
    operation: str,
    model_id: str,
    payload: Dict[str, Any],
    project_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
```

### Provider (LangChain)

```python
async def invoke_generic(
    self, 
    operation: str,
    model_id: str,
    payload: Dict[str, any],
    request_id: Optional[str] = None
) -> Dict[str, any]:
```

## Operações Suportadas

### 1. **Chat/Completion**
```python
payload = {
    "prompt": "Sua pergunta aqui",
    "system_prompt": "Contexto do sistema",
    "max_tokens": 1000,
    "temperature": 0.7
}

result = client.invoke_generic("chat", "gpt-3.5-turbo", payload)
```

### 2. **Batch Processing**
```python
payload = {
    "batch_requests": [
        {"prompt": "Pergunta 1", "max_tokens": 50},
        {"prompt": "Pergunta 2", "max_tokens": 50},
        {"prompt": "Pergunta 3", "max_tokens": 50}
    ]
}

result = client.invoke_generic("batch", "gpt-3.5-turbo", payload)
```

### 3. **Stream (Simulado)**
```python
payload = {
    "prompt": "Conte uma história longa",
    "stream_config": {"chunk_size": 100}
}

result = client.invoke_generic("stream", "gpt-3.5-turbo", payload)
```

### 4. **Custom/Advanced**
```python
payload = {
    "messages": [
        {"role": "system", "content": "Você é um especialista"},
        {"role": "user", "content": "Pergunta complexa"}
    ],
    "parameters": {
        "temperature": 0.3,
        "top_p": 0.9,
        "frequency_penalty": 0.1
    },
    "metadata": {
        "experiment_id": "exp_001",
        "research_area": "NLP"
    }
}

result = client.invoke_generic("completion", "gpt-4", payload)
```

## Formato de Resposta

```python
{
    "success": True,
    "request_id": "12345-abcde-67890",
    "operation": "chat",
    "model_used": "gpt-3.5-turbo",
    "provider": "openai",
    "response_time_ms": 1250,
    "langchain_used": True,
    "service_timestamp": "2025-07-28T15:30:45Z",
    "project_id": "proj_marketing_001",
    "broker_version": "1.0.0",
    
    # Dados específicos da operação
    "response_text": "Resposta do modelo...",
    "finish_reason": "stop",
    "usage": {
        "total_tokens": 150,
        "prompt_tokens": 100,
        "completion_tokens": 50
    },
    
    # Para batch operations
    "batch_results": [...],
    "total_requests": 3,
    "successful_requests": 3
}
```

## Fluxo de Execução

### 1. **SDK → Broker**
```
Cliente SDK              Broker API
     |                        |
     | POST /api/v1/llm/invoke |
     |----------------------->|
     |                        | ✓ Validar token
     |                        | ✓ Aplicar guardrails
     |                        | ✓ Registrar telemetria
     |                        |
```

### 2. **Broker → LangChain**
```
Broker Service           LangChain Provider
     |                        |
     | invoke_generic()       |
     |----------------------->|
     |                        | ✓ Validar modelo
     |                        | ✓ Executar operação
     |                        | ✓ Retornar resultado
     |                        |
```

### 3. **Resposta Completa**
```
     |<-----------------------|
     | ✓ Adicionar metadados   |
     | ✓ Registrar telemetria  |
     | ✓ Formatar resposta     |
     |<-----------------------|
```

## Vantagens da Arquitetura

### 🎯 **Para Desenvolvedores**
- Interface única e consistente
- Flexibilidade total de payload
- Tratamento automático de erros
- Não precisam se preocupar com governança

### 🛡️ **Para Governança**
- Controle centralizado de todas as operações
- Telemetria obrigatória e não contornável
- Auditoria completa de uso de LLMs
- Aplicação consistente de políticas

### 🔧 **Para Integração LangChain**
- Compatibilidade nativa com todas as features
- Suporte a operações batch e streaming
- Flexibilidade para novos tipos de operação
- Wrapper transparente sem overhead

## Casos de Uso

### 1. **Desenvolvimento RAG**
```python
# Embedding de documentos
payload = {"documents": [...], "chunk_size": 1000}
embeddings = client.invoke_generic("embedding", "text-embedding-ada-002", payload)

# Consulta com contexto
payload = {
    "query": "Pergunta do usuário",
    "context_docs": [...],
    "system_prompt": "Use apenas o contexto fornecido"
}
response = client.invoke_generic("chat", "gpt-4", payload)
```

### 2. **Processamento em Lote**
```python
# Análise de sentimentos em massa
documents = ["Doc 1", "Doc 2", ..., "Doc N"]
payload = {
    "batch_requests": [
        {"prompt": f"Analise o sentimento: {doc}", "max_tokens": 10}
        for doc in documents
    ]
}
results = client.invoke_generic("batch", "gpt-3.5-turbo", payload)
```

### 3. **Chains Complexas**
```python
# Chain customizada com múltiplas etapas
payload = {
    "chain_type": "custom",
    "steps": [
        {"operation": "summarize", "input": "documento_longo.txt"},
        {"operation": "translate", "target_language": "en"},
        {"operation": "sentiment", "output_format": "json"}
    ]
}
result = client.invoke_generic("chain", "gpt-4", payload)
```

## Implementação Técnica

### Validação de Entrada
```python
# SDK
if not operation or not model_id:
    raise BradaxValidationError("Parâmetros obrigatórios")

if not isinstance(payload, dict):
    raise BradaxValidationError("Payload deve ser dict")
```

### Tratamento de Erros
```python
# Broker
try:
    result = await provider.invoke_generic(...)
    await self._log_telemetry(result)
    return result
except Exception as e:
    error_result = self._create_error_result(str(e))
    await self._log_telemetry(error_result)
    return error_result
```

### Telemetria Automática
```python
telemetry_data = {
    "operation_type": "invoke_generic",
    "langchain_operation": operation,
    "project_id": project_id,
    "timestamp": datetime.utcnow().isoformat(),
    "success": result.get("success"),
    "response_time_ms": result.get("response_time_ms"),
    "tokens_used": result.get("usage", {}).get("total_tokens", 0)
}
```

## Próximos Passos

1. **Implementar operações de embedding**
2. **Adicionar suporte a streaming real**
3. **Implementar chains customizadas**
4. **Adicionar cache de respostas**
5. **Implementar rate limiting por operação**

## Conclusão

O método `invoke_generic()` representa a evolução natural da integração LangChain no ecosistema bradax, oferecendo:

- **Flexibilidade máxima** para desenvolvedores
- **Governança robusta** para administradores
- **Compatibilidade total** com LangChain
- **Telemetria extensiva** para monitoramento
- **Escalabilidade** para operações complexas

É o wrapper ideal para uso corporativo de LLMs com controle centralizado.
