# API Contracts - bradax SDK & Broker

## Contratos de Interface

### 1. HTTP REST API Specification

#### Base
- **Base URL**: `https://bradax-broker.seguros.bradesco.com.br/api/v1`
- **Content-Type**: `application/json`
- **Authentication**: `Bearer <jwt_token>`

#### Error Format
```json
{
  "error": "authentication_failed",
  "message": "Token JWT inválido ou expirado",
  "details": [
    {
      "code": "TOKEN_EXPIRED",
      "message": "Token expirou em 2025-07-25T15:30:00Z"
    }
  ],
  "request_id": "uuid-here",
  "timestamp": "2025-07-25T15:45:00Z"
}
```

### 2. Authentication Endpoints

#### POST /auth/token
**Request:**
```json
{
  "project_id": "fraude-claims",
  "api_key": "bx_live_abc123...",
  "scopes": ["invoke_llm", "read_vector"]
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAi...",
  "refresh_token": "eyJ0eXAi...",
  "expires_in": 900,
  "token_type": "Bearer",
  "scopes": ["invoke_llm", "read_vector"],
  "timestamp": "2025-07-25T15:45:00Z"
}
```

#### POST /auth/refresh
**Request:**
```json
{
  "refresh_token": "eyJ0eXAi..."
}
```

### 3. LLM Endpoints

#### POST /llm/invoke
**Request:**
```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {
      "role": "system",
      "content": "Você é um perito em sinistros de seguros."
    },
    {
      "role": "user", 
      "content": "Meu carro foi roubado, o que devo fazer?"
    }
  ],
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

**Response:**
```json
{
  "content": "Para casos de roubo de veículo, você deve...",
  "model": "gpt-4o-mini",
  "usage": {
    "prompt_tokens": 45,
    "completion_tokens": 150,
    "total_tokens": 195,
    "cost_usd": 0.001
  },
  "timestamp": "2025-07-25T15:45:00Z"
}
```

#### POST /llm/stream
**Request:** (mesmo formato de `/llm/invoke` com `"stream": true`)

**Response:** (Server-Sent Events)
```
data: {"delta": "Para", "finished": false}
data: {"delta": " casos", "finished": false}
data: {"delta": " de", "finished": false}
...
data: {"delta": "", "finished": true, "usage": {...}}
```

### 4. Vector Database Endpoints

#### POST /vectors/{collection}/query
**Request:**
```json
{
  "query_text": "roubo de veículo",
  "top_k": 5,
  "threshold": 0.7,
  "filters": {
    "category": "sinistros"
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "doc_123",
      "score": 0.95,
      "metadata": {
        "title": "Procedimentos para Roubo",
        "category": "sinistros"
      },
      "text": "Em casos de roubo de veículo..."
    }
  ],
  "timestamp": "2025-07-25T15:45:00Z"
}
```

#### POST /vectors/{collection}/upsert
**Request:**
```json
{
  "documents": [
    {
      "id": "doc_new_123",
      "vector": [0.1, 0.2, 0.3, ...],
      "metadata": {
        "title": "Novo Documento",
        "category": "sinistros"
      },
      "text": "Conteúdo do documento..."
    }
  ]
}
```

### 5. Graph Management Endpoints

#### POST /graphs/deploy
**Request:**
```json
{
  "name": "pipeline_fraude",
  "definition": "name: classify_claims\nnodes:\n  - id: embed...",
  "format": "yaml"
}
```

**Response:**
```json
{
  "graph_id": "graph_abc123",
  "version": "1.0.0",
  "success": true,
  "timestamp": "2025-07-25T15:45:00Z"
}
```

#### POST /graphs/{graph_id}/execute
**Request:**
```json
{
  "inputs": {
    "claim_text": "Meu carro foi roubado ontem...",
    "policy_number": "POL123456"
  },
  "stream": false
}
```

### 6. Observability Endpoints

#### GET /metrics?project_id=fraude-claims&start_time=...
**Response:**
```json
{
  "metrics": [
    {
      "name": "llm_requests_total",
      "type": "counter",
      "value": 1250,
      "labels": {
        "project": "fraude-claims",
        "model": "gpt-4o-mini"
      },
      "timestamp": "2025-07-25T15:45:00Z"
    }
  ]
}
```

#### GET /health
**Response:**
```json
{
  "status": "healthy",
  "checks": {
    "database": "healthy",
    "vault": "healthy", 
    "llm_providers": "healthy",
    "vector_db": "degraded"
  },
  "timestamp": "2025-07-25T15:45:00Z"
}
```

## Rate Limiting

### Headers de Rate Limit
```http
X-RateLimit-Limit: 500
X-RateLimit-Remaining: 485
X-RateLimit-Reset: 1643723400
X-RateLimit-Window: 60
```

### Response quando Rate Limit Excedido (429)
```json
{
  "error": "rate_limit_exceeded",
  "message": "Limite de 500 requisições por minuto excedido",
  "details": [
    {
      "code": "RATE_LIMIT_EXCEEDED",
      "message": "Tente novamente em 15 segundos"
    }
  ]
}
```

## WebSocket Endpoints (Futuro)

### /ws/graphs/{graph_id}/stream
Para execução de grafos com streaming em tempo real

### /ws/llm/stream  
Para streaming de LLM via WebSocket (alternativa ao SSE)

## SDK Python Interface Contract

### Classe Full
```python
from bradax import Full

sdk = Full(token="eyJ0eXAi...")

# LLM
response = sdk.llm(model="gpt-4o-mini").invoke(messages=[...])

# Vector
results = sdk.vectorstore("claims").query("roubo veículo", top_k=5)

# Graph
graph = sdk.graph("pipeline_fraude")
result = graph.run(inputs={"claim_text": "..."})
```

### Classe Student (com limitações)
```python
from bradax import Student

sdk = Student(token="eyJ0eXAi...")
# Mesma interface, mas com limites de rate e funcionalidades
```
