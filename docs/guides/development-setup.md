# bradax Development Environment

## Requisitos do Sistema

- **Python**: 3.10+ (recomendado 3.12)
- **Docker**: 20.10+ com Docker Compose
- **Git**: 2.30+
- **Make**: Para automação de builds

## Setup Rápido

### 1. Clonar e Configurar
```bash
git clone https://github.com/jowpereira/bradax.git
cd bradax
./tools/setup-dev.sh
```

### 2. Ativar Ambiente Virtual
```bash
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate.bat  # Windows
```

### 3. Instalar Dependências
```bash
# SDK
cd packages/bradax-sdk
pip install -e ".[dev,agents]"

# Broker  
cd ../bradax-broker
pip install -e ".[dev]"
```

### 4. Configurar Variáveis de Ambiente
```bash
cp .env.example .env
# Editar .env com suas configurações
```

## Docker Development

### Broker Local
```bash
cd packages/bradax-broker
docker-compose -f docker-compose.dev.yml up -d
```

### Dependências (Redis, PostgreSQL)
```bash
docker-compose -f docker/docker-compose.deps.yml up -d
```

## Comandos Úteis

```bash
# Testes completos
./tools/test.sh

# Testes apenas do SDK
./tools/test-sdk.sh

# Testes apenas do Broker
./tools/test-broker.sh

# Linting e formatação
./tools/lint.sh

# Build completo
./tools/build.sh

# Gerar código gRPC
./tools/generate-proto.sh
```

## Estrutura de Desenvolvimento

```
bradax/
├── .env                    # Variáveis de ambiente locais
├── .env.example           # Template de configuração
├── docker-compose.yml     # Ambiente completo
├── Makefile              # Automação principal
├── tools/                # Scripts de desenvolvimento
├── packages/
│   ├── bradax-sdk/       # Desenvolvimento do SDK
│   └── bradax-broker/    # Desenvolvimento do Broker
└── shared/               # Código compartilhado
```

## IDEs Recomendadas

### VS Code
Extensões essenciais instaladas automaticamente via `.vscode/extensions.json`:
- Python
- Pylance
- Black Formatter
- Protocol Buffers
- Docker

### PyCharm
Configuração no `.idea/` (incluída no repo)

## Debugging

### SDK
```bash
cd packages/bradax-sdk
python -m pytest tests/ -v --pdb
```

### Broker
```bash
cd packages/bradax-broker  
uvicorn broker.main:app --reload --port 8000
```

### gRPC
```bash
# Teste manual de gRPC
grpcurl -plaintext localhost:9000 list
grpcurl -plaintext localhost:9000 bradax.v1.BrokerService/HealthCheck
```

## Base de Dados Local

### PostgreSQL (via Docker)
```bash
# Conectar ao banco
docker exec -it bradax_postgres psql -U bradax -d bradax_dev

# Migrations
cd packages/bradax-broker
alembic upgrade head
```

### Redis (cache/sessions)
```bash
# Conectar ao Redis
docker exec -it bradax_redis redis-cli
```

## Variáveis de Ambiente

### .env Example
```bash
# Database
DATABASE_URL=postgresql://bradax:password@localhost:5432/bradax_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-super-secret-key-here
JWT_ALGORITHM=RS256

# LLM Providers (para testes)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Observability
JAEGER_ENDPOINT=http://localhost:14268/api/traces

# Development
DEBUG=true
LOG_LEVEL=DEBUG
```

## CI/CD Local

### Pre-commit Hooks
```bash
pre-commit install
pre-commit run --all-files
```

### GitHub Actions Local
```bash
act -W .github/workflows/test.yml
```

## Troubleshooting

### Problemas Comuns

#### 1. Erro de Import gRPC
```bash
# Regenerar arquivos gRPC
./tools/generate-proto.sh
```

#### 2. Conflitos de Dependências
```bash
# Reset completo do ambiente
rm -rf .venv
./tools/setup-dev.sh
```

#### 3. Broker não conecta
```bash
# Verificar se dependências estão rodando
docker-compose -f docker/docker-compose.deps.yml ps
```

#### 4. Testes falhando
```bash
# Executar apenas testes unitários
pytest packages/bradax-sdk/tests/unit/ -v
```

## Performance Tips

### 1. Cache de Dependências
```bash
export PIP_CACHE_DIR=$HOME/.cache/pip
export PIPENV_CACHE_DIR=$HOME/.cache/pipenv
```

### 2. Paralelização de Testes
```bash
pytest -n auto  # Usa todos os cores disponíveis
```

### 3. Build Docker Otimizado
```bash
# Usar BuildKit
export DOCKER_BUILDKIT=1
docker build --cache-from bradax-broker:latest .
```
