# Bradax Broker - Hub Corporativo de LLM

> **Sistema empresarial de orquestração de LLM com autenticação por projeto, guardrails automáticos e telemetria completa.**

## 🏗️ Visão Geral Arquitetural

O Bradax Broker é um proxy corporativo que centraliza o acesso a modelos de LLM, aplicando políticas de governança, autenticação baseada em projetos e coleta de telemetria em tempo real.

```mermaid
graph TB
    SDK[bradax SDK] -->|Token de Projeto| AUTH[Autenticação]
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

### 1. Integração por Projetos
```python
# SDK se autentica com token do projeto
client = BradaxClient(
    project_token="proj_acme_2025_ai_assistant_001",
    broker_url="https://llm.empresa.com"
)

# Cada projeto tem seus modelos permitidos
response = client.run_llm(
    prompt="Analise este documento corporativo...",
    model="gpt-4o-mini"  # Deve estar na lista do projeto
)
```

### 2. Guardrails Automáticos
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

## 🛠️ Endpoints Principais

### Autenticação e Projetos
```http
POST /api/v1/auth/validate
Authorization: Bearer proj_token_here
```

### Operações LLM
```http
# Execução de modelo
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

## 🚀 Casos de Uso Avançados

### 1. Batch Processing
```python
# Processar múltiplos documentos
results = client.batch_process([
    {"prompt": "Analise documento 1", "model": "gpt-4o-mini"},
    {"prompt": "Analise documento 2", "model": "gpt-4o-mini"},
    {"prompt": "Analise documento 3", "model": "gpt-4o-mini"}
])
```

### 2. Streaming Responses
```python
# Resposta em tempo real
for chunk in client.stream_llm(
    prompt="Escreva um relatório detalhado...",
    model="gpt-4o"
):
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
