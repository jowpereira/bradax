# 🚀 Bradax - AI Hub & SDK

Sistema empresarial de IA composto por dois projetos independentes e autossuficientes.

## 📦 Arquitetura

### 🔹 **bradax-sdk**
SDK Python para integração com o Hub de IA da empresa.
- **Destino**: Nexus da empresa para download pelos desenvolvedores
- **Propósito**: Interface padronizada para consumo de IA
- **Características**: Autossuficiente, zero hard-code, configurável via environment

### 🔹 **bradax-broker** 
API/Hub central de validação e processamento de IA.
- **Destino**: Deploy em produção como serviço
- **Propósito**: Validação, autenticação, rate limiting e processamento
- **Características**: Escalável, configurável, com observabilidade completa

## 🛠️ Estrutura

```
bradax/
├── bradax-sdk/          # 📚 SDK para desenvolvedores
│   └── src/bradax/
│       ├── constants.py      # Configurações internas
│       ├── config/           # Sistema de configuração
│       ├── exceptions/       # Hierarquia de exceções
│       └── client/           # Clientes de integração
│
└── bradax-broker/       # 🚀 Hub/API de IA
    └── src/broker/
        ├── constants.py      # Configurações internas
        ├── config.py         # Sistema de configuração
        ├── api/              # Endpoints da API
        ├── auth/             # Autenticação e autorização
        ├── middleware/       # Middlewares (CORS, rate limiting)
        ├── schemas/          # Modelos Pydantic
        └── services/         # Lógica de negócio
```

## ✨ Características

### 🎯 **Zero Hard-Code**
- Todas as configurações externalizáveis via environment variables
- Constants internas organizadas por domínio
- Configuração específica por ambiente (dev/staging/prod)

### 🏗️ **Modular e Profissional**
- Projetos completamente independentes
- Sem dependências circulares ou externas desnecessárias
- Arquitetura limpa e extensível

### 🔒 **Enterprise-Ready**
- Sistema robusto de autenticação
- Rate limiting configurável
- Observabilidade e auditoria completas
- Validação rigorosa de dados

## 🚀 Deploy

### SDK
```bash
# Build para Nexus
cd bradax-sdk
python -m build
# Upload para Nexus da empresa
```

### Hub/API
```bash
# Deploy via Docker
cd bradax-broker
docker build -t bradax-hub .
docker run -p 8000:8000 bradax-hub
```

## 📋 Configuração

### Environment Variables

#### SDK
```bash
BRADAX_ENV=production
BRADAX_HUB_URL_PROD=https://api.bradax.com
BRADAX_SDK_TIMEOUT=30
```

#### Hub/API
```bash
BRADAX_ENV=production
BRADAX_HUB_PORT=8000
BRADAX_JWT_SECRET=your-secret-key
BRADAX_RATE_LIMIT_RPM=60
```

## 🎯 Uso

### SDK (Desenvolvedores)
```python
from bradax import BradaxCorporateClient

# Inicialização
client = BradaxCorporateClient(
    project_id="proj_meu_projeto",
    api_key="bradax_key_123..."
)

# Uso
response = await client.chat_completion([
    {"role": "user", "content": "Analise este documento..."}
])
```

### Hub/API (Endpoints)
```bash
# Health check
GET /health

# Chat completion
POST /v1/chat/completions

# Modelos disponíveis
GET /v1/models
```

---

**Bradax AI Solutions** - Sistema empresarial de IA robusto e escalável.
