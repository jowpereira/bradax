# Bradax SDK - Interface LangChain Corporativa

> **SDK Python com interface LangChain-compatível para integração segura com o Bradax Broker. Governança empresarial integrada.**

## 🎯 Interface Principal LangChain

O Bradax SDK agora oferece interface **100% compatível com LangChain** para máxima produtividade:

```python
from bradax import BradaxClient
from bradax.config import BradaxSDKConfig

# Configuração corporativa
config = BradaxSDKConfig.for_production(
    broker_url="https://api.bradax.com",
    project_id="seu-projeto",
    api_key="sua-chave-api"
)

client = BradaxClient(config)

# Interface LangChain padrão - MÉTODO PRINCIPAL
response = client.invoke("Analise este relatório financeiro")
print(response["content"])

# Interface assíncrona LangChain
response = await client.ainvoke("Gere resumo executivo") 
print(response["content"])
```

## 🏗️ Configurações por Ambiente

### 🛠️ Desenvolvimento (Recomendado para Desenvolvedores)
```python
# Para desenvolvimento local e testes
config = BradaxSDKConfig.for_development(
    broker_url="http://localhost:8000",    # Broker local
    project_id="dev-projeto",
    enable_telemetry=False,               # Reduz overhead
    enable_guardrails=False,              # Mais flexível
    timeout=30
)
```

### 🧪 Testes Unitários
```python
# Para testes automatizados
config = BradaxSDKConfig.for_testing(
    project_id="test-projeto",
    enable_telemetry=False,
    enable_guardrails=False
)
```

### ⚠️ Produção (Uso Interno - Deploy Automático)
```python
# ATENÇÃO: Esta configuração é usada apenas pela esteira de CI/CD
# Desenvolvedores NÃO devem usar esta configuração diretamente
# Testes em produção são executados pelo sistema de deploy
config = BradaxSDKConfig.for_production(
    broker_url="https://api.bradax.com",  # HTTPS obrigatório
    project_id="projeto-prod",
    api_key="prod-api-key",              # Obrigatório
    enable_telemetry=True,
    enable_guardrails=True,
    timeout=60
```

## 📦 Instalação Rápida

```bash
pip install bradax-sdk
```

## 🚀 Configuração Avançada

### Guardrails Personalizados
```python
from bradax import BradaxClient
from bradax.config import BradaxSDKConfig

# Configuração para desenvolvimento com guardrails customizados
config = BradaxSDKConfig.for_development(
    broker_url="http://localhost:8000",
    project_id="projeto-com-guardrails",
    enable_guardrails=True
)

client = BradaxClient(config)

# Adicionar regras de guardrail personalizadas
client.add_custom_guardrail_rule({
    "id": "content_safety",
    "pattern": "senha|cpf|cartão",
    "severity": "HIGH"
})
```

## 🛡️ Guardrails Personalizados

### Conceito Fundamental
- **Guardrails do Projeto:** Obrigatórios, definidos no broker (NÃO podem ser desabilitados)
- **Guardrails Personalizados:** Opcionais, adicionados pelo SDK (COMPLEMENTAM os defaults)

### Adicionar Guardrails Locais
```python
# Guardrail de segurança de dados
client.add_custom_guardrail_rule({
    "id": "data_security",
    "pattern": "confidencial|secreto|interno",
    "severity": "CRITICAL"
})

# Guardrail de compliance
client.add_custom_guardrail_rule({
    "id": "compliance_check", 
    "pattern": "dados pessoais|informação privada",
    "severity": "HIGH"
})

# Guardrail de qualidade de entrada
client.add_custom_guardrail_rule({
    "id": "input_quality",
    "pattern": "^.{0,5}$",  # Texto muito curto
    "severity": "MEDIUM"
})

# Verificar se conteúdo passa pelos guardrails
is_valid = client.validate_content("Este texto está seguro para processamento")
print(f"Conteúdo válido: {is_valid}")
```

## 📊 Uso LangChain-Compatible

### Exemplos Práticos com invoke()
```python
# Exemplo 1: String simples
response = client.invoke("Resuma este documento em 3 pontos principais")
print(response["content"])

# Exemplo 2: Lista de mensagens (formato LangChain)
messages = [
    {"role": "system", "content": "Você é um assistente especializado em análise de dados"},
    {"role": "user", "content": "Analise estas vendas: Q1: 100k, Q2: 120k, Q3: 95k"}
]
response = client.invoke(messages)
print(response["content"])

# Exemplo 3: Configuração avançada
response = client.invoke(
    "Explique machine learning",
    config={"model": "gpt-4", "temperature": 0.1},
    max_tokens=500
)
print(f"Modelo usado: {response['response_metadata']['model']}")

# Exemplo 4: Uso assíncrono
async def process_document(document_text):
    response = await client.ainvoke([
        {"role": "user", "content": f"Analise este documento: {document_text}"}
    ])
    return response["content"]
```

### Verificação de Saúde e Status
```python
# Verificar se broker está disponível
try:
    health = client.check_broker_health()
    print(f"Broker status: {health['status']}")
except Exception as e:
    print(f"Broker indisponível: {e}")
```

## 🔧 Configuração Centralizada

### Configuração por Ambiente
```python
from bradax.config import BradaxSDKConfig

# Configuração automática baseada no ambiente
config = BradaxSDKConfig.from_environment()

# Configuração para testes
test_config = BradaxSDKConfig.for_testing()

# Configuração manual
config = BradaxSDKConfig(
    broker_url="https://llm.empresa.com",
    timeout=30,
    api_key_prefix="bradax_",
    environment="production",
    debug=False,
    custom_guardrails={},
    local_telemetry_enabled=True,
    telemetry_buffer_size=100
)
```

### Variáveis de Ambiente Suportadas
```bash
# URLs e conectividade
BRADAX_BROKER_URL=https://llm.empresa.com
BRADAX_TIMEOUT=30

# Configuração de ambiente
BRADAX_ENVIRONMENT=production
BRADAX_DEBUG=false

# Telemetria local
BRADAX_LOCAL_TELEMETRY=true
BRADAX_TELEMETRY_BUFFER=100
```

## 🎭 Operações Avançadas

### Context Manager
```python
# Uso com context manager (recomendado)
with BradaxClient("proj_token_123") as client:
    response = client.run_llm(
        prompt="Gere um resumo executivo...",
        model="gpt-4o-mini"
    )
    print(response["content"])
# Cliente é automaticamente fechado
```

### Operações Batch
```python
# Processar múltiplas requisições
prompts = [
    "Analise documento 1",
    "Analise documento 2", 
    "Analise documento 3"
]

results = []
for prompt in prompts:
    response = client.run_llm(
        prompt=prompt,
        model="gpt-4o-mini",
        max_tokens=500
    )
    results.append(response)
```

### Streaming (quando suportado)
```python
# Stream de resposta em tempo real
for chunk in client.stream_llm(
    prompt="Escreva um relatório detalhado sobre...",
    model="gpt-4o",
    max_tokens=2000
):
    print(chunk, end="", flush=True)
```

## 🔒 Segurança e Autenticação

### Tokens de Projeto
```python
# Token de projeto corporativo (formato padrão)
project_token = "proj_acme_2025_ai_assistant_001"
#                ^^^^_^^^^_^^^^_^^^^^^^^^^^^_^^^
#                proj_org_year_project_name_seq

# Validação automática de formato
client = BradaxClient(project_token)  # Valida automaticamente
```

### Headers Automáticos
```python
# Headers adicionados automaticamente pelo SDK
{
    "Authorization": "Bearer proj_acme_2025_ai_assistant_001",
    "X-Project-Token": "proj_acme_2025_ai_assistant_001",
    "Content-Type": "application/json",
    "User-Agent": "bradax-sdk/1.0.0 (env:production)"
}
```

## 📋 Tratamento de Erros

### Hierarquia de Exceções
```python
from bradax.exceptions import (
    BradaxError,                  # Base exception
    BradaxAuthenticationError,    # Token inválido/expirado
    BradaxConnectionError,        # Problemas de rede
    BradaxConfigurationError,     # Configuração inválida
    BradaxValidationError,        # Dados de entrada inválidos
    BradaxBrokerError            # Erros do broker
)

try:
    response = client.run_llm(
        prompt="Analise estes dados...",
        model="modelo-inexistente"
    )
except BradaxValidationError as e:
    print(f"Dados inválidos: {e}")
except BradaxAuthenticationError as e:
    print(f"Problema de autenticação: {e}")
except BradaxBrokerError as e:
    print(f"Erro do broker: {e}")
except BradaxError as e:
    print(f"Erro geral: {e}")
```

### Tratamento Específico
```python
# Retry automático para erros de rede
client = BradaxClient(
    project_token="proj_token_123",
    max_retries=3  # Tentará até 3 vezes em caso de falha de rede
)

# Logs detalhados para debug
client = BradaxClient(
    project_token="proj_token_123",
    verbose=True  # Ativa logs detalhados
)
```

## 🏗️ Integração Corporativa

### Padrão Factory
```python
from bradax import create_client_for_project

# Factory method para projetos corporativos
client = create_client_for_project(
    project_name="ai_assistant",
    organization="acme",
    year=2025,
    environment="production"
)
# Gera automaticamente: proj_acme_2025_ai_assistant_001
```

### Configuração de Projeto
```python
from bradax.config import ProjectConfig

# Configuração específica do projeto
project_config = ProjectConfig(
    project_id="proj_acme_2025_ai_assistant_001",
    api_key="bradax_secret_key_here",
    organization="ACME Corp",
    department="TI",
    budget_limit=5000.00,
    allowed_models=["gpt-4o-mini", "gpt-3.5-turbo"]
)

# Cliente com configuração de projeto
client = BradaxClient(
    project_token=project_config.api_key,
    project_config=project_config
)
```

## 📊 Monitoramento e Debug

### Health Check
```python
# Verificar status do broker
health = client.get_health()
print(f"Status: {health['status']}")
print(f"Serviços: {health['services']}")
```

### Logs e Debug
```python
import logging

# Configurar logging do SDK
logging.getLogger("bradax").setLevel(logging.DEBUG)

# Cliente com debug ativo
client = BradaxClient(
    project_token="proj_token_123",
    verbose=True
)

# Logs automáticos incluem:
# - Requisições enviadas
# - Respostas recebidas
# - Guardrails acionados
# - Métricas de performance
```

### Métricas Locais
```python
# Coletar métricas da sessão atual
metrics = client.get_session_metrics()
print(f"Requisições: {metrics['total_requests']}")
print(f"Tempo total: {metrics['total_time_ms']}ms")
print(f"Guardrails acionados: {metrics['guardrails_triggered']}")
```

## 🔄 Casos de Uso Reais

### 1. Análise de Documentos
```python
def analyze_document(file_path: str) -> dict:
    with open(file_path, 'r') as f:
        content = f.read()
    
    with BradaxClient("proj_acme_2025_document_analyzer_001") as client:
        # Adicionar guardrail específico para documentos
        client.add_custom_guardrail("document_validation", {
            "max_size_mb": 10,
            "allowed_formats": ["txt", "md", "docx"],
            "require_content": True
        })
        
        response = client.run_llm(
            prompt=f"Analise este documento e forneça um resumo: {content}",
            model="gpt-4o-mini",
            max_tokens=1000
        )
        
        return {
            "summary": response["content"],
            "word_count": len(content.split()),
            "analysis_tokens": response.get("usage", {}).get("total_tokens", 0)
        }
```

### 2. Chatbot Corporativo
```python
class CorporateChatbot:
    def __init__(self, project_token: str):
        self.client = BradaxClient(project_token)
        
        # Configurar guardrails para chat
        self.client.add_custom_guardrail("chat_safety", {
            "max_message_length": 2000,
            "require_politeness": True,
            "corporate_context": True
        })
    
    def chat(self, user_message: str, context: str = "") -> str:
        prompt = f"""
        Contexto corporativo: {context}
        Pergunta do usuário: {user_message}
        
        Responda de forma profissional e precisa.
        """
        
        response = self.client.run_llm(
            prompt=prompt,
            model="gpt-4o-mini",
            max_tokens=500,
            temperature=0.7
        )
        
        return response["content"]
```

### 3. Processamento em Lote
```python
def process_customer_feedback(feedback_list: list) -> dict:
    results = {
        "positive": [],
        "negative": [],
        "neutral": [],
        "total_processed": 0
    }
    
    with BradaxClient("proj_acme_2025_feedback_analyzer_001") as client:
        for feedback in feedback_list:
            try:
                response = client.run_llm(
                    prompt=f"Classifique este feedback como positivo, negativo ou neutro: {feedback}",
                    model="gpt-3.5-turbo",
                    max_tokens=50
                )
                
                sentiment = response["content"].lower().strip()
                if "positivo" in sentiment:
                    results["positive"].append(feedback)
                elif "negativo" in sentiment:
                    results["negative"].append(feedback)
                else:
                    results["neutral"].append(feedback)
                    
                results["total_processed"] += 1
                
            except Exception as e:
                print(f"Erro processando feedback: {e}")
    
    return results
```

## 🏢 Conformidade Corporativa

### Práticas Recomendadas
1. **Sempre usar context managers** para garantir fechamento de recursos
2. **Configurar guardrails apropriados** para cada caso de uso
3. **Monitorar telemetria local** para otimização
4. **Tratar exceções específicas** para melhor experiência
5. **Usar configuração centralizada** para ambientes

### Auditoria e Compliance
```python
# Todas as operações são automaticamente auditadas
# Dados incluem:
# - Timestamp da requisição
# - Token do projeto usado
# - Modelo e parâmetros
# - Conteúdo (se configurado)
# - Guardrails acionados
# - Métricas de performance
```

---

> **💼 Nota Corporativa:** Este SDK foi projetado para ambientes empresariais que exigem controle total, auditoria completa e conformidade com políticas corporativas. Todas as operações são transparentes e auditáveis.
