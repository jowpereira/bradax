# Testes do Sistema Bradax

Testes organizados e detalhados do sistema Bradax com **dados reais da OpenAI**.

## 🎯 Filosofia dos Testes

- **SEM MOCKS**: Todos os testes usam dados reais
- **SEM FALLBACKS**: Falhas são tratadas como falhas reais
- **DADOS REAIS**: Integração real com OpenAI via chave de API
- **ORGANIZADOS**: Estrutura clara e lógica de execução

## 📁 Estrutura de Testes

```
tests/
├── __init__.py
├── conftest.py                 # Configurações compartilhadas
├── unit/                       # Testes unitários
│   ├── __init__.py
│   └── test_endpoints.py       # Endpoints básicos e validações
├── integration/                # Testes de integração
│   ├── __init__.py
│   ├── test_langchain_real.py  # LangChain + OpenAI real
│   ├── test_guardrails_real.py # Guardrails + LLM validation
│   └── test_telemetry_real.py  # Sistema de telemetria
└── end_to_end/                 # Testes E2E completos
    ├── __init__.py
    ├── test_sdk_integration.py # Integração SDK-Broker
    └── test_complete_system.py # Sistema completo
```

## ⚙️ Pré-requisitos

### 1. Chave OpenAI Configurada

```bash
# No arquivo .env do bradax-broker:
OPENAI_API_KEY=sk-your-real-openai-key-here
```

### 2. Dependências Instaladas

```bash
pip install pytest pytest-asyncio fastapi httpx
```

### 3. Broker Funcionando (para testes E2E)

```bash
cd bradax-broker
python run_server.py
```

## 🚀 Executando os Testes

### Execução Completa Organizada

```bash
cd bradax-broker
python run_tests.py
```

### Testes Específicos

```bash
# Endpoints básicos
python run_tests.py endpoints

# Integração LangChain
python run_tests.py langchain

# Sistema de guardrails
python run_tests.py guardrails

# Telemetria
python run_tests.py telemetry

# Integração SDK
python run_tests.py sdk

# Sistema completo E2E
python run_tests.py e2e
```

### Execução Manual com Pytest

```bash
# Todos os testes
pytest tests/ -v

# Categoria específica
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/end_to_end/ -v

# Arquivo específico
pytest tests/integration/test_langchain_real.py -v

# Teste específico
pytest tests/unit/test_endpoints.py::TestEndpoints::test_health_endpoint -v
```

## 📊 Tipos de Teste

### 🔧 Unit Tests (tests/unit/)

**Objetivo**: Validar componentes básicos do sistema
- Endpoints de saúde e informações
- Validação de configuração
- Persistência de dados básica

**Duração**: ~30 segundos
**Dependências**: Aplicação rodando

### 🔗 Integration Tests (tests/integration/)

**Objetivo**: Validar integração com serviços externos reais

#### LangChain Real (test_langchain_real.py)
- Chamadas reais para OpenAI
- Validação de tokens e usage
- Teste de modelos disponíveis
- Rate limiting e error handling

#### Guardrails Real (test_guardrails_real.py)  
- Validação LLM híbrida (regex + IA)
- Detecção de senhas, tokens, PII
- Análise contextual inteligente
- Performance e custom rules

#### Telemetria Real (test_telemetry_real.py)
- Coleta automática de métricas
- Persistência de dados de uso
- Integração com componentes
- Monitoramento em tempo real

**Duração**: ~2-5 minutos
**Dependências**: OPENAI_API_KEY válida

### 🎯 End-to-End Tests (tests/end_to_end/)

**Objetivo**: Validar fluxos completos do sistema

#### SDK Integration (test_sdk_integration.py)
- Fluxo completo SDK → Broker
- Guardrails locais vs remotos
- Telemetria integrada
- Gerenciamento de projetos

#### Complete System (test_complete_system.py)
- Workflow completo: Guardrails → LLM → Resposta
- Ciclo de vida de projetos
- Performance sob carga
- Estabilidade extended
- Persistência confiável

**Duração**: ~5-10 minutos
**Dependências**: Sistema completo funcionando

## 🔍 Monitoramento e Debug

### Logs de Teste

```bash
# Logs detalhados salvos em:
test_results_*.xml  # Resultados JUnit
```

### Verificação de Ambiente

```bash
# O script run_tests.py automaticamente verifica:
# ✅ OPENAI_API_KEY configurada e válida
# ✅ Estrutura de testes presente
# ✅ Dependências instaladas
# ✅ Sem variáveis de fallback ativas
```

### Debug de Falhas

```bash
# Executar com verbose máximo
pytest tests/integration/test_langchain_real.py -vvv -s

# Capturar stdout
pytest tests/ -v -s --capture=no

# Parar no primeiro erro
pytest tests/ -x
```

## 📈 Métricas Esperadas

### ✅ Critérios de Sucesso

- **Taxa de sucesso**: ≥ 95% dos testes passando
- **Performance**: Endpoints < 2s, LLM calls < 10s  
- **Integração**: OpenAI responding, Guardrails blocking
- **Persistência**: Dados salvos corretamente
- **Estabilidade**: Sistema funciona por 30s+ contínuos

### 📊 Métricas Coletadas

- Tempo de resposta por endpoint
- Usage de tokens OpenAI
- Eficácia dos guardrails (bloqueios vs aprovações)
- Métricas de sistema (CPU, RAM, Disk)
- Eventos de telemetria por categoria

## ⚠️ Limitações e Considerações

### Custos da OpenAI
- Testes fazem chamadas reais → custos pequenos mas reais
- Estimativa: ~$0.01-0.05 por execução completa
- Use max_tokens baixos para economizar

### Rate Limits
- OpenAI tem rate limits por minuto
- Testes respeitam limites automaticamente
- Se exceder: aguarda ou falha graciosamente

### Dependências Externas
- Requer conectividade com internet
- OpenAI API deve estar funcionando
- Falhas na OpenAI = falhas nos testes (by design)

### Dados Sensíveis
- Testes NÃO usam dados sensíveis reais
- Senhas/tokens nos testes são fictícios
- Guardrails testados com dados simulados seguros

## 🎭 Exemplos de Uso

### Desenvolvimento Local
```bash
# Durante desenvolvimento, teste componente específico
python run_tests.py guardrails

# Para CI/CD, execução completa
python run_tests.py
```

### Validação de Deploy
```bash
# Após deploy, validar sistema completo
python run_tests.py e2e
```

### Debug de Issues
```bash
# Se guardrails com problema
pytest tests/integration/test_guardrails_real.py::TestGuardrailsSystem::test_password_detection_guardrail -vvv
```

---

## 🏆 Status de Implementação

**Conforme Fase 4 do plano workspace-plans/active/20250728-223500-conferencia-corporativa-consolidada.md**

- ✅ **4.1** Testes de endpoints - funcionalidade e validações
- ✅ **4.2** Testes de integração LangChain - chamadas reais  
- ✅ **4.3** Testes de guardrails - políticas e validações
- ✅ **4.4** Testes de telemetria e logging - coleta de dados
- ✅ **4.5** Testes de integração SDK-Broker - fluxo completo

**Sistema de testes 100% funcional com dados reais da OpenAI.**
