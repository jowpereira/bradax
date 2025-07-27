# bradax Broker - AI Generative Runtime

> **🤖 Broker corporativo Python para Large Language Models**  
> Runtime empresarial com autenticação, governança e integração OpenAI para ambientes containerizados.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://docker.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-Compatible-black)](https://openai.com/)

## 📋 Visão Geral

O **bradax Broker** é o runtime corporativo que conecta aplicações internas aos modelos de IA, oferecendo:

- **🔐 Autenticação Corporativa**: Sistema JWT com controle por projeto
- **🤖 Integração OpenAI**: Proxy inteligente com rate limiting e retry
- **📊 Governança Automática**: Controle de custos, modelos e compliance
- **🐳 Container-Ready**: Deployment via Docker/Kubernetes
- **📈 Observabilidade**: Métricas, logs e healthchecks completos

## 🏗️ Arquitetura

```mermaid
graph TD
    A[SDK Client] --> B[Load Balancer]
    B --> C[bradax Broker Instance 1]
    B --> D[bradax Broker Instance 2]
    B --> E[bradax Broker Instance N]
    
    C --> F[Project Auth]
    C --> G[Rate Limiting]
    C --> H[OpenAI Service]
    
    F --> I[PostgreSQL]
    G --> J[Redis]
    H --> K[OpenAI API]
    
    C --> L[Metrics]
    L --> M[Prometheus]
    
    C --> N[Logs]
    N --> O[Splunk/ELK]
```

## 🚀 Deploy Rápido

### Docker Compose (Desenvolvimento)

```bash
# Clonar e configurar
git clone https://git.bradesco.com.br/ai/bradax-broker.git
cd bradax-broker

# Configurar variáveis
cp .env.example .env
# Editar .env com suas configurações

# Subir stack completa
docker-compose up -d
```

### Docker Container (Produção)

```bash
# Build da imagem
docker build -t bradax-broker:latest .

# Executar container
docker run -d \
  --name bradax-broker \
  -p 8000:8000 \
  -e OPENAI_API_KEY="sk-proj-..." \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  -e REDIS_URL="redis://host:6379/0" \
  -e JWT_SECRET_KEY="your-secret-key" \
  bradax-broker:latest
```

### Kubernetes (Produção)

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bradax-broker
spec:
  replicas: 3
  selector:
    matchLabels:
      app: bradax-broker
  template:
    metadata:
      labels:
        app: bradax-broker
    spec:
      containers:
      - name: bradax-broker
        image: nexus.bradesco.com.br/bradax-broker:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-secret
              key: api-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: connection-string
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

## ⚙️ Configuração

### Variáveis de Ambiente

```bash
# OpenAI Integration
OPENAI_API_KEY=sk-proj-your-openai-api-key
OPENAI_TIMEOUT=120
OPENAI_MAX_RETRIES=3

# Database
DATABASE_URL=postgresql://bradax:password@postgres:5432/bradax_prod
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_TIMEOUT=30

# Security
JWT_SECRET_KEY=your-super-secret-jwt-key-256-bits
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=900
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4
LOG_LEVEL=INFO

# Features
RATE_LIMITING_ENABLED=true
METRICS_ENABLED=true
AUDIT_LOGGING_ENABLED=true
```

### Configuração de Projeto

```sql
-- Inserir projeto na base de dados
INSERT INTO projects (
    token,
    name,
    division,
    team,
    budget_monthly_usd,
    max_tokens_per_request,
    max_requests_per_hour,
    allowed_models,
    compliance_rules,
    created_at
) VALUES (
    'proj_inovacao_ia_chatbot_2025_a1b2c3d4',
    'Chatbot Atendimento',
    'inovacao',
    'ia',
    1000.00,
    4096,
    100,
    '["gpt-4.1-nano", "gpt-4.1-mini"]',
    '["lgpd", "pii_detection"]',
    NOW()
);
```

## 🔧 API Reference

### Autenticação

```http
POST /api/v1/auth/token
Content-Type: application/json

{
  "project_id": "proj_inovacao_ia_chatbot_2025_a1b2c3d4",
  "api_key": "bx_api_key_project_specific"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "expires_in": 900,
  "token_type": "Bearer",
  "scopes": ["invoke_llm", "read_metrics"]
}
```

### Invocação LLM

```http
POST /api/v1/llm/invoke
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "model": "gpt-4.1-nano",
  "messages": [
    {"role": "user", "content": "Explique seguros de vida"}
  ],
  "parameters": {
    "max_tokens": 500,
    "temperature": 0.3
  }
}
```

**Response:**
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Seguros de vida são produtos financeiros..."
      }
    }
  ],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 128,
    "total_tokens": 143
  },
  "model": "gpt-4.1-nano",
  "request_id": "req_20250727_154500_abc123"
}
```

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-27T15:45:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy", 
    "openai": "healthy"
  },
  "version": "1.0.0"
}
```

### Métricas

```http
GET /metrics
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "total_requests": 1523,
  "successful_requests": 1489,
  "failed_requests": 34,
  "average_latency_ms": 1247,
  "total_cost_usd": 15.67,
  "models_usage": {
    "gpt-4.1-nano": 1200,
    "gpt-4.1-mini": 323
  }
}
```

## 📊 Monitoramento

### Prometheus Metrics

```bash
# Acessar métricas Prometheus
curl http://localhost:8000/prometheus

# Principais métricas expostas:
# - bradax_requests_total{method, endpoint, status}
# - bradax_request_duration_seconds{method, endpoint}
# - bradax_openai_requests_total{model, status}
# - bradax_openai_cost_usd_total{model}
# - bradax_active_connections
# - bradax_database_connections{state}
```

### Health Checks

```bash
# Health check básico
curl http://localhost:8000/health

# Health check detalhado
curl http://localhost:8000/health/detailed

# Ready check (Kubernetes)
curl http://localhost:8000/ready

# Live check (Kubernetes)
curl http://localhost:8000/live
```

### Logs Estruturados

```json
{
  "timestamp": "2025-07-27T15:45:00Z",
  "level": "INFO",
  "logger": "bradax.broker",
  "message": "LLM request completed",
  "extra": {
    "request_id": "req_20250727_154500_abc123",
    "project_token": "proj_...c3d4",
    "model": "gpt-4.1-nano",
    "tokens_used": 143,
    "cost_usd": 0.000025,
    "latency_ms": 1247,
    "status": "success"
  }
}
```

## 🐳 Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY src/ ./src/

# Criar usuário não-root
RUN useradd --create-home --shell /bin/bash bradax
USER bradax

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Comando padrão
CMD ["uvicorn", "src.broker.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose Produção

```yaml
version: "3.8"

services:
  bradax-broker:
    image: nexus.bradesco.com.br/bradax-broker:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://bradax:${DB_PASSWORD}@postgres:5432/bradax_prod
      - REDIS_URL=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - LOG_LEVEL=INFO
    depends_on:
      - postgres
      - redis
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 1G
          cpus: "1.0"
        reservations:
          memory: 512M
          cpus: "0.5"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=bradax_prod
      - POSTGRES_USER=bradax
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - bradax-broker

volumes:
  postgres_data:
  redis_data:
```

## 🔐 Segurança

### TLS/SSL

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name bradax.bradesco.com.br;
    
    ssl_certificate /etc/nginx/ssl/bradax.crt;
    ssl_certificate_key /etc/nginx/ssl/bradax.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
    
    location / {
        proxy_pass http://bradax-broker:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Rate Limiting

```python
# Configuração automática via Redis
# - Por projeto: 100 req/hour padrão
# - Por IP: 1000 req/hour máximo
# - Por endpoint: Limites específicos
# - Burst protection: 10 req/second máximo
```

### Secrets Management

```bash
# Kubernetes secrets
kubectl create secret generic openai-secret \
  --from-literal=api-key="sk-proj-..."

kubectl create secret generic postgres-secret \
  --from-literal=connection-string="postgresql://..."

kubectl create secret generic jwt-secret \
  --from-literal=secret-key="your-256-bit-secret"
```

## 📈 Performance

### Benchmarks

```bash
# Load test com Apache Bench
ab -n 1000 -c 10 -H "Authorization: Bearer {token}" \
   -T "application/json" \
   -p request.json \
   http://localhost:8000/api/v1/llm/invoke

# Resultados típicos:
# - Requests per second: 50-100 RPS
# - Latência média: 1000-2000ms (dependente da OpenAI)
# - 99th percentile: <5000ms
# - Erro rate: <0.1%
```

### Otimizações

```python
# Connection pooling
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis caching  
REDIS_CACHE_TTL=300

# HTTP timeouts
OPENAI_TIMEOUT=120
HTTP_CLIENT_TIMEOUT=60

# Worker processes
WORKERS=4  # 1 por CPU core
```

## 🛠️ Desenvolvimento

### Setup Local

```bash
# Clonar repositório
git clone https://git.bradesco.com.br/ai/bradax-broker.git
cd bradax-broker

# Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate    # Windows

# Instalar dependências
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configurar banco local
docker run -d --name postgres-dev \
  -e POSTGRES_DB=bradax_dev \
  -e POSTGRES_USER=bradax \
  -e POSTGRES_PASSWORD=dev123 \
  -p 5432:5432 \
  postgres:15-alpine

# Executar migrações
alembic upgrade head

# Rodar broker
uvicorn src.broker.main:app --reload --port 8000
```

### Estrutura do Projeto

```
bradax-broker/
├── src/broker/
│   ├── main.py                  # FastAPI app principal
│   ├── config.py               # Configurações
│   ├── api/
│   │   └── routes/             # Endpoints REST
│   ├── auth/
│   │   └── project_auth.py     # Autenticação por projeto
│   ├── services/
│   │   └── openai_service.py   # Integração OpenAI
│   ├── middleware/             # CORS, logging, rate limiting
│   └── schemas/                # Modelos Pydantic
├── tests/                      # Testes unitários e integração
├── docker-compose.yml          # Stack desenvolvimento
├── Dockerfile                  # Imagem produção
├── requirements.txt            # Dependências
└── README.md                   # Esta documentação
```

### Testes

```bash
# Executar todos os testes
pytest tests/ -v

# Testes com cobertura
pytest tests/ --cov=src --cov-report=html

# Testes de integração
pytest tests/integration/ -v

# Testes específicos
pytest tests/test_auth.py::test_token_validation -v
```

## 📞 Suporte

### Troubleshooting

#### Broker não inicia

```bash
# Verificar logs
docker logs bradax-broker

# Problemas comuns:
# 1. OPENAI_API_KEY não configurada
# 2. DATABASE_URL inválida
# 3. Porta já em uso
# 4. Dependências não instaladas
```

#### Erro de autenticação

```bash
# Verificar token no banco
SELECT * FROM projects WHERE token = 'proj_...';

# Verificar logs de autenticação
grep "auth" /var/log/bradax/broker.log
```

#### Performance degradada

```bash
# Verificar métricas
curl http://localhost:8000/metrics

# Verificar conexões DB
curl http://localhost:8000/health/detailed

# Verificar Redis
redis-cli ping
```

### Contatos

- **🎫 Service Now**: Categoria "AI Generativa - Broker"
- **📧 Email**: ai-generativa-infra@bradesco.com.br
- **📱 Teams**: Canal "AI Generativa - Infraestrutura"
- **🔧 On-call**: +55 11 9999-8888 (emergências)

## 📜 Licença

**Uso Corporativo Interno - Bradesco Seguros**

Este broker é propriedade exclusiva do Bradesco Seguros e destina-se apenas ao uso interno corporativo. Redistribuição ou uso externo não autorizado é proibido.

---

## 🚀 Conclusão

O **bradax Broker** oferece runtime empresarial robusto com:

- **🔐 Autenticação segura** por projeto com JWT
- **🤖 Integração OpenAI** com retry e rate limiting
- **📊 Observabilidade completa** com métricas e logs
- **🐳 Deploy containerizado** para Kubernetes
- **📈 Performance otimizada** para alta concorrência

**Pronto para produção** com monitoramento e alta disponibilidade.

---
*Documentação atualizada em: 27/07/2025*
