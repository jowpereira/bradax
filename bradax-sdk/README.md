# Bradax SDK - Cliente Python Corporativo

> **SDK Python profissional para integração segura com o Bradax Broker. Inclui autenticação por projeto, guardrails personalizados e telemetria local.**

## 🎯 Visão Geral

O Bradax SDK é o cliente oficial para comunicação com o Bradax Broker, projetado para ambientes corporativos que exigem controle total sobre operações de LLM.

```mermaid
graph LR
    APP[Aplicação] --> SDK[Bradax SDK]
    SDK --> AUTH[Autenticação]
    SDK --> GUARD[Guardrails Locais]
    SDK --> TELEM[Telemetria Local]
    SDK -->|HTTPS| BROKER[Bradax Broker]
    
    subgraph "SDK Components"
        CLIENT[BradaxClient]
        CONFIG[Configuração]
        EXCEPT[Exceções]
    end
```

## 🚀 Uso Básico

### Inicialização Simples
```python
from bradax import BradaxClient

# Cliente básico
client = BradaxClient(
    project_token="proj_acme_2025_ai_assistant_001",
    broker_url="https://llm.empresa.com"
)

# Execução de LLM
response = client.run_llm(
    prompt="Analise este relatório de vendas...",
    model="gpt-4o-mini",
    max_tokens=1000
)

print(response["content"])
```

### Configuração Avançada
```python
from bradax import BradaxClient
from bradax.config import BradaxSDKConfig

# Configuração personalizada
config = BradaxSDKConfig.from_environment()
config.set_custom_guardrail("content_safety", {
    "max_chars": 5000,
    "forbidden_patterns": ["senha", "cpf"],
    "check_encoding": "utf-8"
})

# Cliente com configuração
client = BradaxClient(
    project_token="proj_acme_2025_ai_assistant_001",
    config=config
)
```

## 🛡️ Guardrails Personalizados

### Conceito Fundamental
- **Guardrails do Projeto:** Obrigatórios, definidos no broker (NÃO podem ser desabilitados)
- **Guardrails Personalizados:** Opcionais, adicionados pelo SDK (COMPLEMENTAM os defaults)

### Adicionar Guardrails Locais
```python
# Guardrail de tamanho de conteúdo
client.add_custom_guardrail("content_length", {
    "max_chars": 10000,
    "min_chars": 10,
    "check_empty": True
})

# Guardrail de filtro de conteúdo
client.add_custom_guardrail("content_filter", {
    "forbidden_words": ["confidencial", "secreto"],
    "case_sensitive": False,
    "action": "block"  # ou "warn"
})

# Guardrail de validação de entrada
client.add_custom_guardrail("input_validation", {
    "require_question_mark": True,
    "max_sentences": 5,
    "language": "pt-BR"
})

# Listar guardrails ativos
guardrails = client.list_custom_guardrails()
print(f"Guardrails personalizados: {len(guardrails)}")
```

### Gerenciar Guardrails
```python
# Remover guardrail específico
removed = client.remove_custom_guardrail("content_length")
if removed:
    print("Guardrail removido com sucesso")

# Verificar guardrails ativos
active_guards = client.list_custom_guardrails()
for name, config in active_guards.items():
    print(f"- {name}: {config}")
```

## 📊 Telemetria Local

### Configuração de Telemetria
```python
# A telemetria do PROJETO é sempre obrigatória (definida no broker)
# Esta é apenas a telemetria ADICIONAL local do SDK

# Verificar configuração atual
telem_config = client.get_telemetry_config()
print(f"Telemetria local: {telem_config['local_enabled']}")
print(f"Buffer size: {telem_config['buffer_size']}")
print(f"Ambiente: {telem_config['environment']}")

# Telemetria local coleta métricas adicionais:
# - Latência de rede
# - Tentativas de reconexão  
# - Guardrails locais acionados
# - Cache hits/misses
```

### Dados Coletados Localmente
```python
# Exemplo de telemetria local adicional
{
    "sdk_version": "1.0.0",
    "local_latency_ms": 45,
    "guardrails_triggered": ["content_length"],
    "retry_attempts": 0,
    "local_cache_hit": False,
    "request_timestamp": "2025-07-29T01:30:00Z"
}
```

## 🔧 Configuração Centralizada

### Configuração por Ambiente
```python
from bradax.config import BradaxSDKConfig

# Configuração automática baseada no ambiente
config = BradaxSDKConfig.from_environment()

# Configuração para testes
test_config = BradaxSDKConfig.for_testing()

# Configuração manual
config = BradaxSDKConfig(
    broker_url="https://llm.empresa.com",
    timeout=30,
    api_key_prefix="bradax_",
    environment="production",
    debug=False,
    custom_guardrails={},
    local_telemetry_enabled=True,
    telemetry_buffer_size=100
)
```

### Variáveis de Ambiente Suportadas
```bash
# URLs e conectividade
BRADAX_BROKER_URL=https://llm.empresa.com
BRADAX_TIMEOUT=30

# Configuração de ambiente
BRADAX_ENVIRONMENT=production
BRADAX_DEBUG=false

# Telemetria local
BRADAX_LOCAL_TELEMETRY=true
BRADAX_TELEMETRY_BUFFER=100
```

## 🎭 Operações Avançadas

### Context Manager
```python
# Uso com context manager (recomendado)
with BradaxClient("proj_token_123") as client:
    response = client.run_llm(
        prompt="Gere um resumo executivo...",
        model="gpt-4o-mini"
    )
    print(response["content"])
# Cliente é automaticamente fechado
```

### Operações Batch
```python
# Processar múltiplas requisições
prompts = [
    "Analise documento 1",
    "Analise documento 2", 
    "Analise documento 3"
]

results = []
for prompt in prompts:
    response = client.run_llm(
        prompt=prompt,
        model="gpt-4o-mini",
        max_tokens=500
    )
    results.append(response)
```

### Streaming (quando suportado)
```python
# Stream de resposta em tempo real
for chunk in client.stream_llm(
    prompt="Escreva um relatório detalhado sobre...",
    model="gpt-4o",
    max_tokens=2000
):
    print(chunk, end="", flush=True)
```

## 🔒 Segurança e Autenticação

### Tokens de Projeto
```python
# Token de projeto corporativo (formato padrão)
project_token = "proj_acme_2025_ai_assistant_001"
#                ^^^^_^^^^_^^^^_^^^^^^^^^^^^_^^^
#                proj_org_year_project_name_seq

# Validação automática de formato
client = BradaxClient(project_token)  # Valida automaticamente
```

### Headers Automáticos
```python
# Headers adicionados automaticamente pelo SDK
{
    "Authorization": "Bearer proj_acme_2025_ai_assistant_001",
    "X-Project-Token": "proj_acme_2025_ai_assistant_001",
    "Content-Type": "application/json",
    "User-Agent": "bradax-sdk/1.0.0 (env:production)"
}
```

## 📋 Tratamento de Erros

### Hierarquia de Exceções
```python
from bradax.exceptions import (
    BradaxError,                  # Base exception
    BradaxAuthenticationError,    # Token inválido/expirado
    BradaxConnectionError,        # Problemas de rede
    BradaxConfigurationError,     # Configuração inválida
    BradaxValidationError,        # Dados de entrada inválidos
    BradaxBrokerError            # Erros do broker
)

try:
    response = client.run_llm(
        prompt="Analise estes dados...",
        model="modelo-inexistente"
    )
except BradaxValidationError as e:
    print(f"Dados inválidos: {e}")
except BradaxAuthenticationError as e:
    print(f"Problema de autenticação: {e}")
except BradaxBrokerError as e:
    print(f"Erro do broker: {e}")
except BradaxError as e:
    print(f"Erro geral: {e}")
```

### Tratamento Específico
```python
# Retry automático para erros de rede
client = BradaxClient(
    project_token="proj_token_123",
    max_retries=3  # Tentará até 3 vezes em caso de falha de rede
)

# Logs detalhados para debug
client = BradaxClient(
    project_token="proj_token_123",
    verbose=True  # Ativa logs detalhados
)
```

## 🏗️ Integração Corporativa

### Padrão Factory
```python
from bradax import create_client_for_project

# Factory method para projetos corporativos
client = create_client_for_project(
    project_name="ai_assistant",
    organization="acme",
    year=2025,
    environment="production"
)
# Gera automaticamente: proj_acme_2025_ai_assistant_001
```

### Configuração de Projeto
```python
from bradax.config import ProjectConfig

# Configuração específica do projeto
project_config = ProjectConfig(
    project_id="proj_acme_2025_ai_assistant_001",
    api_key="bradax_secret_key_here",
    organization="ACME Corp",
    department="TI",
    budget_limit=5000.00,
    allowed_models=["gpt-4o-mini", "gpt-3.5-turbo"]
)

# Cliente com configuração de projeto
client = BradaxClient(
    project_token=project_config.api_key,
    project_config=project_config
)
```

## 📊 Monitoramento e Debug

### Health Check
```python
# Verificar status do broker
health = client.get_health()
print(f"Status: {health['status']}")
print(f"Serviços: {health['services']}")
```

### Logs e Debug
```python
import logging

# Configurar logging do SDK
logging.getLogger("bradax").setLevel(logging.DEBUG)

# Cliente com debug ativo
client = BradaxClient(
    project_token="proj_token_123",
    verbose=True
)

# Logs automáticos incluem:
# - Requisições enviadas
# - Respostas recebidas
# - Guardrails acionados
# - Métricas de performance
```

### Métricas Locais
```python
# Coletar métricas da sessão atual
metrics = client.get_session_metrics()
print(f"Requisições: {metrics['total_requests']}")
print(f"Tempo total: {metrics['total_time_ms']}ms")
print(f"Guardrails acionados: {metrics['guardrails_triggered']}")
```

## 🔄 Casos de Uso Reais

### 1. Análise de Documentos
```python
def analyze_document(file_path: str) -> dict:
    with open(file_path, 'r') as f:
        content = f.read()
    
    with BradaxClient("proj_acme_2025_document_analyzer_001") as client:
        # Adicionar guardrail específico para documentos
        client.add_custom_guardrail("document_validation", {
            "max_size_mb": 10,
            "allowed_formats": ["txt", "md", "docx"],
            "require_content": True
        })
        
        response = client.run_llm(
            prompt=f"Analise este documento e forneça um resumo: {content}",
            model="gpt-4o-mini",
            max_tokens=1000
        )
        
        return {
            "summary": response["content"],
            "word_count": len(content.split()),
            "analysis_tokens": response.get("usage", {}).get("total_tokens", 0)
        }
```

### 2. Chatbot Corporativo
```python
class CorporateChatbot:
    def __init__(self, project_token: str):
        self.client = BradaxClient(project_token)
        
        # Configurar guardrails para chat
        self.client.add_custom_guardrail("chat_safety", {
            "max_message_length": 2000,
            "require_politeness": True,
            "corporate_context": True
        })
    
    def chat(self, user_message: str, context: str = "") -> str:
        prompt = f"""
        Contexto corporativo: {context}
        Pergunta do usuário: {user_message}
        
        Responda de forma profissional e precisa.
        """
        
        response = self.client.run_llm(
            prompt=prompt,
            model="gpt-4o-mini",
            max_tokens=500,
            temperature=0.7
        )
        
        return response["content"]
```

### 3. Processamento em Lote
```python
def process_customer_feedback(feedback_list: list) -> dict:
    results = {
        "positive": [],
        "negative": [],
        "neutral": [],
        "total_processed": 0
    }
    
    with BradaxClient("proj_acme_2025_feedback_analyzer_001") as client:
        for feedback in feedback_list:
            try:
                response = client.run_llm(
                    prompt=f"Classifique este feedback como positivo, negativo ou neutro: {feedback}",
                    model="gpt-3.5-turbo",
                    max_tokens=50
                )
                
                sentiment = response["content"].lower().strip()
                if "positivo" in sentiment:
                    results["positive"].append(feedback)
                elif "negativo" in sentiment:
                    results["negative"].append(feedback)
                else:
                    results["neutral"].append(feedback)
                    
                results["total_processed"] += 1
                
            except Exception as e:
                print(f"Erro processando feedback: {e}")
    
    return results
```

## 🏢 Conformidade Corporativa

### Práticas Recomendadas
1. **Sempre usar context managers** para garantir fechamento de recursos
2. **Configurar guardrails apropriados** para cada caso de uso
3. **Monitorar telemetria local** para otimização
4. **Tratar exceções específicas** para melhor experiência
5. **Usar configuração centralizada** para ambientes

### Auditoria e Compliance
```python
# Todas as operações são automaticamente auditadas
# Dados incluem:
# - Timestamp da requisição
# - Token do projeto usado
# - Modelo e parâmetros
# - Conteúdo (se configurado)
# - Guardrails acionados
# - Métricas de performance
```

---

> **💼 Nota Corporativa:** Este SDK foi projetado para ambientes empresariais que exigem controle total, auditoria completa e conformidade com políticas corporativas. Todas as operações são transparentes e auditáveis.
