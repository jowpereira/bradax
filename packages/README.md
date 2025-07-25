# bradax Monorepo

Este repositório contém dois projetos principais:

## 📦 Estrutura do Projeto

```
bradax/
├── packages/
│   ├── bradax-sdk/          # SDK Python para desenvolvedores
│   └── bradax-broker/       # Broker de execução (container Linux)
├── shared/
│   ├── proto/              # Definições gRPC compartilhadas
│   └── schemas/            # Schemas JSON/Pydantic compartilhados
├── tools/                  # Scripts de build e desenvolvimento
├── docs/
│   ├── api/               # Documentação de APIs
│   ├── guides/           # Guias de uso
│   └── memory/           # Memória do projeto (não versionada)
└── workspace-plans/       # Planos de trabalho (não versionados)
```

## 🚀 Desenvolvimento

Para começar o desenvolvimento:

```bash
# Instalar dependências de desenvolvimento
./tools/setup-dev.sh

# Executar testes
./tools/test.sh

# Build completo
./tools/build.sh
```

## 📋 Projetos

### bradax-sdk
- Pacote Python para desenvolvedores
- Modos Full() e Student()
- Biblioteca de agentes (RAG, CRAG, SQL, etc.)
- Graph Builder API

### bradax-broker  
- Servidor FastAPI + gRPC
- Cofre de chaves integrado
- Roteamento de LLMs
- Sistema de autenticação JWT

## 🔗 Comunicação

- **HTTP REST**: Interface pública do SDK
- **gRPC**: Comunicação interna de alta performance
- **JWT RS256**: Autenticação e autorização
