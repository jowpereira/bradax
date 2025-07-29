# 🚀 Bradax - AI Hub & SDK Empresarial

Sistema empresarial de IA de classe enterprise com arquitetura MVC completa, sistema robusto de exceções e zero hardcode.

## 📦 Arquitetura Empresarial

### 🔹 **bradax-sdk**
SDK Python para integração com o Hub de IA da empresa.
- **Destino**: Nexus da empresa para download pelos desenvolvedores
- **Propósito**: Interface padronizada para consumo de IA
- **Características**: Autossuficiente, zero hard-code, configurável via environment

### 🔹 **bradax-broker** ⭐ 
API/Hub central de validação e processamento de IA com arquitetura MVC completa.
- **Destino**: Deploy em produção como serviço
- **Propósito**: Validação, autenticação, rate limiting e processamento
- **Características**: Escalável, configurável, com observabilidade completa
- **Arquitetura**: MVC Controllers + Sistema robusto de exceções + Zero hardcode

## 🛠️ Estrutura Enterprise

```
bradax/
├── bradax-sdk/          # 📚 SDK para desenvolvedores
│   └── src/bradax/
│       ├── constants.py      # Configurações internas
│       ├── config/           # Sistema de configuração
│       ├── exceptions/       # Hierarquia de exceções
│       └── client/           # Clientes de integração
│
└── bradax-broker/       # 🚀 Hub/API de IA Enterprise
    └── src/broker/
        ├── constants.py      # ✅ ZERO HARDCODE - Configurações via env vars
        ├── exceptions/       # ✅ Sistema robusto de exceções hierárquicas
        ├── controllers/      # ✅ MVC Controllers (Base, LLM, Project, System)
        ├── api/              # Endpoints da API
        ├── auth/             # ✅ Autenticação empresarial (ProjectAuth)
        ├── middleware/       # Middlewares (CORS, rate limiting, security)
        ├── schemas/          # Modelos Pydantic
        └── services/         # Lógica de negócio
```

## ✨ Características Enterprise

### 🎯 **ZERO HARDCODE ✅**
- Todas as configurações via environment variables
- Constants centralizadas por domínio (Network, Security, LLM, Budget)
- Configuração específica por ambiente (dev/testing/staging/prod)
- Sistema de fallback eliminado

### 🏗️ **Arquitetura MVC Completa ✅**
- **BaseController**: Estrutura comum com logging e validação
- **LLMController**: Lógica de negócio para modelos de IA
- **ProjectController**: CRUD empresarial com autenticação
- **SystemController**: Health checks e métricas do sistema

### 🛡️ **Sistema Robusto de Exceções ✅**
- **BradaxException**: Base hierárquica com contexto rico
- **Categorização**: Authentication, Authorization, Validation, Business, Technical
- **Severidade**: Low, Medium, High, Critical
- **Mapeamento HTTP**: Códigos de status automáticos
- **Factory Functions**: Criação padronizada de exceções

### 🔐 **Autenticação Empresarial ✅**
- **ProjectAuth**: Sistema completo de autenticação de projetos
- **Sessões**: Gerenciamento de sessões com expiração
- **Permissões**: Controle granular baseado em roles
- **Orçamento**: Controle de custos por projeto
- **Auditoria**: Log completo de acessos e operações
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
