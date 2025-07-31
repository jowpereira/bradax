# 🚀 Bradax - Interface LangChain Corporativa

Sistema empresarial de IA com interface **100% compatível LangChain** para produtividade máxima.

## 📦 Componentes do Sistema

### 🔹 **bradax-sdk** - Interface LangChain
SDK Python com interface padrão LangChain para integração corporativa.
- **Interface**: `invoke()` e `ainvoke()` - compatível 100% LangChain
- **Configuração**: Factory methods por ambiente (`for_development`, `for_production`)
- **Governança**: Guardrails e telemetria integrados
- **Deploy**: Via Nexus da empresa para desenvolvedores

### 🔹 **bradax-broker** - Hub de IA ⭐ 
API central de processamento com arquitetura MVC empresarial.
- **Função**: Validação, autenticação, rate limiting e processamento
- **Arquitetura**: MVC Controllers + Sistema robusto de exceções
- **Deploy**: Produção como serviço escalável
- **Observabilidade**: Telemetria e auditoria completas

## 🛠️ Estrutura Enterprise

```
bradax/
├── bradax-sdk/          # 📚 Interface LangChain para desenvolvedores
│   └── src/bradax/
│       ├── client.py         # BradaxClient com invoke() e ainvoke()
│       ├── config/           # Factory methods por ambiente
│       ├── exceptions/       # Hierarquia de exceções
│       └── constants.py      # Configurações internas
│
└── bradax-broker/       # 🚀 Hub/API de IA Enterprise
    └── src/broker/
        ├── main.py           # FastAPI app principal
        ├── controllers/      # MVC Controllers (Base, LLM, Project, System)
        ├── middleware/       # CORS, rate limiting, security
        ├── services/         # Lógica de negócio (OpenAI, LangChain)
        └── auth/             # Autenticação empresarial
```

## ✨ Interface LangChain Moderna

### 🎯 **SDK com Padrão LangChain ✅**
```python
from bradax import BradaxClient
from bradax.config import BradaxSDKConfig

# Configuração para desenvolvimento
config = BradaxSDKConfig.for_development()
client = BradaxClient(config)

# Interface LangChain padrão
response = client.invoke("Analise este documento")
response = await client.ainvoke("Gere relatório")
```

### 🏗️ **Configurações por Ambiente ✅**
- `for_development()` - Desenvolvimento local
- `for_production()` - Deploy automático (não testes manuais)
- Testes em homologação/produção via esteira de deploy

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
from bradax import BradaxClient
from bradax.config import BradaxSDKConfig

# Configuração
config = BradaxSDKConfig.for_integration_tests(
    broker_url="https://api.bradax.com",
    project_id="proj_meu_projeto",
    api_key="bradax_key_123..."
)

# Inicialização
client = BradaxClient(config)

# Uso LangChain-compatible
response = client.invoke("Analise este documento...")

# Uso assíncrono
response = await client.ainvoke([
    {"role": "user", "content": "Resuma este relatório..."}
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
