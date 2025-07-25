# Arquitetura de Comunicação bradax

## Visão Geral

A comunicação entre o SDK e o Broker utiliza duas interfaces principais:

1. **HTTP REST API** - Interface pública para operações síncronas
2. **gRPC** - Interface interna para comunicação de alta performance

## HTTP REST API

### Base URL
```
https://bradax-broker.seguros.bradesco.com.br/api/v1
```

### Endpoints Principais

#### Autenticação
```http
POST /auth/token
POST /auth/refresh
GET  /auth/validate
```

#### LLM Operations
```http
POST /llm/invoke
POST /llm/stream
```

#### Vector Database
```http
POST /vectors/{collection}/query
POST /vectors/{collection}/upsert
GET  /vectors/{collection}/stats
```

#### Graph Management
```http
POST /graphs/deploy
POST /graphs/{graph_id}/execute
GET  /graphs/{graph_id}/status
```

#### Observabilidade
```http
GET /metrics
GET /health
```

## gRPC Interface

### Serviços Definidos

- **BrokerService** - Serviço principal (ver `shared/proto/broker.proto`)

### Características

- **Performance**: Comunicação binária otimizada
- **Streaming**: Suporte nativo para streaming de tokens LLM
- **Type Safety**: Schemas fortemente tipados
- **Multiplexing**: Múltiplas requisições simultâneas

## Autenticação

### Fluxo JWT RS256

1. **Initial Auth**: API Key → JWT Access Token (15 min TTL)
2. **Refresh**: Refresh Token → New Access Token
3. **Validation**: Token validation em cada requisição

### Headers HTTP
```http
Authorization: Bearer <jwt_access_token>
X-Project-ID: <project_id>
X-Request-ID: <uuid>
```

### gRPC Metadata
```
authorization: Bearer <jwt_access_token>
project-id: <project_id>
request-id: <uuid>
```

## Segurança

### TLS 1.3
- Todas as comunicações HTTP/gRPC são criptografadas
- Certificados gerenciados automaticamente

### Rate Limiting
- **Full Mode**: 500 RPS por projeto
- **Student Mode**: 30 RPS por projeto

### RBAC Scopes
- `invoke_llm` - Chamadas de LLM
- `read_vector` - Leitura de vector DB
- `write_vector` - Escrita em vector DB
- `manage_graph` - Deploy e execução de grafos
- `view_metrics` - Acesso a métricas
- `admin` - Operações administrativas

## Error Handling

### HTTP Status Codes
```
200 - Success
400 - Bad Request
401 - Unauthorized
403 - Forbidden
429 - Rate Limited
500 - Internal Server Error
503 - Service Unavailable
```

### gRPC Status Codes
```
OK - Success
INVALID_ARGUMENT - Bad Request
UNAUTHENTICATED - Authentication failure
PERMISSION_DENIED - Authorization failure
RESOURCE_EXHAUSTED - Rate limit exceeded
INTERNAL - Server error
UNAVAILABLE - Service unavailable
```

## Observabilidade

### Tracing
- OpenTelemetry com Jaeger
- Trace ID propagation HTTP ↔ gRPC

### Metrics
- Prometheus metrics
- Custom business metrics
- Cost tracking per project

### Logging
- Structured logging (JSON)
- Correlation IDs
- Security audit logs
