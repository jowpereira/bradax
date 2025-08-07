# Bradax Broker - Hub Corporativo LangChain

> **Broker empresarial para SDK LangChain com autenticação por projeto, guardrails automáticos e telemetria integrada.**

## 🏗️ Visão Geral Arquitetural

O Bradax Broker é um proxy corporativo que centraliza o acesso a modelos LLM através de interface LangChain, aplicando políticas de governança, autenticação baseada em projetos e coleta de telemetria em tempo real.

```mermaid
graph TB
    SDK[Bradax SDK - Interface LangChain] -->|invoke/ainvoke| AUTH[Autenticação]
    AUTH --> GUARD[Guardrails]
    GUARD --> LLM[Serviço LLM]
    LLM --> PROVIDER[Provider LangChain]
    PROVIDER --> OPENAI[OpenAI API]
    
    AUTH --> TELEM[Telemetria]
    GUARD --> TELEM
    LLM --> TELEM
    TELEM --> STORAGE[Storage JSON]
    
    subgraph "Middleware Stack"
        SECURITY[Security]
        CORS[CORS]
        LOGGING[Logging]
        RATE[Rate Limiting]
    end
```

## 🎯 Casos de Uso Corporativos

### 1. Interface LangChain Padronizada
```python
# SDK LangChain-compatível se autentica com broker
config = BradaxSDKConfig.for_development(
    broker_url="http://localhost:8000",
    project_id="acme-ai-assistant"
)
client = BradaxClient(config)

# Interface LangChain padrão
response = client.invoke("Analise este documento corporativo...")
print(response["content"])
```

### 2. Guardrails Automáticos por Projeto
```python
# Política aplicada automaticamente por projeto
{
    "content_filters": ["pii", "confidential"],
    "max_tokens": 2000,
    "allowed_domains": ["empresa.com"],
    "compliance": "LGPD"
}
```

### 3. Telemetria e Auditoria
```python
# Coleta automática de métricas
{
    "request_id": "req_789xyz",
    "project": "acme_ai_assistant", 
    "model": "gpt-4o-mini",
    "tokens_used": 1250,
    "cost": 0.15,
    "timestamp": "2025-07-29T01:15:30Z",
    "user_department": "marketing"
}
```

## ⚙️ Configuração de Environment

### Variáveis Obrigatórias

```bash
# JWT Secret (OBRIGATÓRIO para segurança)
export BRADAX_JWT_SECRET="$(openssl rand -base64 32)"

# OpenAI API Key (OBRIGATÓRIO para LLM)
export OPENAI_API_KEY="sk-your-openai-key-here"
```

### Variáveis Opcionais

```bash
# Environment  
export BRADAX_ENV="production"  # development|testing|staging|production

# JWT Configuration
export BRADAX_JWT_EXPIRE_MINUTES="15"  # Token expiration (default: 15min)

# Rate Limiting
export BRADAX_RATE_LIMIT_RPM="60"      # Requests per minute (default: 60)
export BRADAX_RATE_LIMIT_RPH="1000"    # Requests per hour (default: 1000)
export BRADAX_MAX_CONCURRENT="10"      # Max concurrent requests (default: 10)

# Network Timeouts
export BRADAX_HUB_LLM_TIMEOUT="180"    # LLM timeout in seconds (default: 180)
```

### Setup Rápido para Desenvolvimento

```bash
# Gerar JWT secret seguro
export BRADAX_JWT_SECRET="$(openssl rand -base64 32)"

# Configurar OpenAI  
export OPENAI_API_KEY="sk-your-key-here"

# Executar broker
cd bradax-broker
python -m uvicorn broker.main:app --reload --port 8080
```

### Setup para Produção

```bash
# JWT secret gerado com alta entropia
export BRADAX_JWT_SECRET="$(openssl rand -base64 48)"

# Environment de produção
export BRADAX_ENV="production"

# Rate limiting mais restritivo
export BRADAX_RATE_LIMIT_RPM="30"
export BRADAX_MAX_CONCURRENT="5"

# Executar com bind específico
python -m uvicorn broker.main:app --host 0.0.0.0 --port 8080
```

## 🛠️ Endpoints Principais

### Autenticação e Projetos
```http
POST /api/v1/auth/validate
Authorization: Bearer proj_token_here
```

### Operações LLM
```http
# Execução de modelo - Formato LangChain (padrão)
POST /api/v1/llm/invoke
{
    "operation": "chat",
    "model": "gpt-4o-mini", 
    "payload": {
        "messages": [
            {"role": "user", "content": "Sua pergunta aqui"}
        ],
        "max_tokens": 1000,
        "temperature": 0.7
    },
    "project_id": "acme_ai_assistant"
}

# Também suporta formato legado (compatibilidade)
POST /api/v1/llm/invoke
{
    "operation": "chat",
    "model": "gpt-4o-mini", 
    "payload": {
        "prompt": "Sua pergunta aqui",
        "max_tokens": 1000
    },
    "project_id": "acme_ai_assistant"
}

# Listar modelos disponíveis
GET /api/v1/llm/models?project_id=acme_ai_assistant
```

### Sistema e Telemetria
```http
# Status do sistema
GET /api/v1/system/health

# Métricas do projeto
GET /api/v1/system/metrics?project_id=acme_ai_assistant

# Telemetria em tempo real
GET /api/v1/system/telemetry?period=1d
```

### Gerenciamento de Projetos
```http
# Informações do projeto
GET /api/v1/management/projects/{project_id}

# Configurar guardrails
PUT /api/v1/management/projects/{project_id}/guardrails
{
    "content_filters": ["pii"],
    "max_daily_tokens": 50000,
    "allowed_models": ["gpt-4o-mini", "gpt-3.5-turbo"]
}
```

## 🔐 Segurança e Autenticação

### Modelo de Autenticação
- **Por Projeto:** Cada projeto corporativo tem token único
- **Validação Contínua:** Tokens validados a cada requisição
- **Escopo Limitado:** Projetos só acessam seus recursos autorizados

### Headers Obrigatórios
```http
Authorization: Bearer proj_acme_2025_ai_assistant_001
Content-Type: application/json
X-Project-Token: proj_acme_2025_ai_assistant_001
```

### Middleware de Segurança
1. **SecurityMiddleware:** Headers de segurança, rate limiting
2. **AuthenticationMiddleware:** Validação de tokens
3. **LoggingMiddleware:** Auditoria completa de requisições
4. **CORSMiddleware:** Controle de origens permitidas

## 📊 Sistema de Telemetria

### Coleta Automática
- **Requisições:** Todas as chamadas são registradas
- **Performance:** Latência, throughput, errors
- **Custos:** Tokens consumidos por projeto/modelo
- **Compliance:** Logs para auditoria corporativa

### Métricas Disponíveis
```json
{
    "project_metrics": {
        "total_requests": 15420,
        "total_tokens": 2500000,
        "total_cost": 375.50,
        "avg_latency_ms": 850,
        "error_rate": 0.02
    },
    "model_usage": {
        "gpt-4o-mini": {
            "requests": 12000,
            "tokens": 1800000,
            "cost": 270.00
        },
        "gpt-3.5-turbo": {
            "requests": 3420,
            "tokens": 700000,
            "cost": 105.50
        }
    }
}
```

## 🛡️ Sistema de Guardrails

### Guardrails Automáticos
- **Validação de Conteúdo:** Filtros de PII, conteúdo impróprio
- **Limites de Uso:** Tokens por período, requisições por minuto
- **Compliance:** LGPD, GDPR, políticas corporativas
- **Modelo Apropriado:** Validação de modelo vs projeto

### Configuração por Projeto
```json
{
    "guardrails": {
        "content_policy": {
            "filter_pii": true,
            "filter_confidential": true,
            "max_content_length": 10000
        },
        "usage_limits": {
            "max_tokens_per_day": 100000,
            "max_requests_per_minute": 50,
            "max_cost_per_month": 1000.00
        },
        "compliance": {
            "data_residency": "BR",
            "audit_level": "full",
            "retention_days": 90
        }
    }
}
```

## 🔧 Integração com LangChain

### Providers Suportados
- **OpenAI:** GPT-4o, GPT-4o-mini, GPT-3.5-turbo
- **Anthropic:** Claude (futuro)
- **Google:** Gemini (futuro)

### Configuração de Modelos
```python
# Configuração no projeto
{
    "allowed_models": [
        {
            "model_id": "gpt-4o-mini",
            "max_tokens": 4096,
            "cost_per_token": 0.00015,
            "enabled": true
        }
    ]
}
```

## 📈 Monitoramento e Observabilidade

### Health Checks
```http
GET /health
{
    "status": "healthy",
    "timestamp": "2025-07-29T01:15:30Z",
    "services": {
        "llm_service": "up",
        "storage": "up", 
        "auth": "up"
    }
}
```

### Logs Estruturados
```json
{
    "timestamp": "2025-07-29T01:15:30Z",
    "level": "INFO",
    "service": "llm_controller",
    "request_id": "req_789xyz",
    "project_id": "acme_ai_assistant",
    "action": "llm_invoke",
    "model": "gpt-4o-mini",
    "tokens": 1250,
    "latency_ms": 850,
    "status": "success"
}
```

## 🚀 Integração SDK-Broker

### 1. Configuração e Uso Básico
```python
from bradax import BradaxClient
from bradax.config import BradaxSDKConfig

# Configuração para o broker
config = BradaxSDKConfig.for_integration_tests(
    broker_url="https://llm.empresa.com",
    project_id="acme_ai_assistant",
    api_key="your_api_key"
)

client = BradaxClient(config)

# Uso LangChain-compatible
response = client.invoke("Analise este documento...")
print(response["content"])
```

### 2. Processamento com Mensagens Estruturadas  
```python
# Formato LangChain com roles
messages = [
    {"role": "system", "content": "Você é um assistente especializado"},
    {"role": "user", "content": "Resuma este relatório"}
]

response = client.invoke(messages, config={"model": "gpt-4o"})
```

### 3. Processamento Assíncrono
```python
# Uso assíncrono para operações longas
async def process_document(text):
    response = await client.ainvoke(
        f"Analise este documento: {text}",
        config={"temperature": 0.1}
    )
    return response["content"]
```
    print(chunk, end="")
```

### 3. Função Calling
```python
# Execução de funções
response = client.run_llm(
    prompt="Qual a previsão do tempo em São Paulo?",
    model="gpt-4o",
    functions=[{
        "name": "get_weather",
        "description": "Obter previsão do tempo",
        "parameters": {"city": "string"}
    }]
)
```

## 🔄 Arquitetura de Dados

### Fluxo de Dados
```
Cliente → Auth → Guardrails → LLM → Provider → Response
    ↓        ↓         ↓        ↓
  Telemetria ← Storage ← Logs ← Metrics
```

### Persistência
- **Projetos:** `data/projects.json`
- **Guardrails:** `data/guardrails.json` 
- **Telemetria:** `data/telemetry.json`
- **Sistema:** `data/system_info.json`

## 🏢 Governança Corporativa

### Políticas Implementadas
- **Autenticação Obrigatória:** Nenhuma requisição sem token
- **Auditoria Completa:** Logs de todas as operações
- **Controle de Custos:** Limites por projeto e período
- **Compliance Automático:** Filtros e validações obrigatórias

### Relatórios Executivos
- **Dashboard de Uso:** Métricas por departamento
- **Análise de Custos:** ROI por projeto
- **Compliance Reports:** Auditoria para certificações
- **Performance Analytics:** Otimização de uso

---

> **💡 Nota:** Este broker foi projetado para ambientes corporativos que exigem controle total sobre o uso de LLM, com foco em segurança, auditoria e governança.
