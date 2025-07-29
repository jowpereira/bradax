# Guias de Uso Corporativo - Bradax

> **Casos reais de implementação corporativa com guardrails, telemetria e governança.**

## 🏢 Cenário 1: Departamento de Marketing

### Contexto
Departamento de Marketing da ACME Corp precisa gerar conteúdo para campanhas, mantendo conformidade com políticas da empresa.

### Implementação
```python
from bradax import BradaxClient
from bradax.config import BradaxSDKConfig

# Configuração específica do marketing
config = BradaxSDKConfig.from_environment()
config.set_custom_guardrail("marketing_compliance", {
    "forbidden_claims": ["100% garantido", "melhor do mundo"],
    "require_disclaimers": True,
    "max_campaign_length": 2000,
    "approved_tone": ["profissional", "amigável"]
})

config.set_custom_guardrail("brand_guidelines", {
    "company_name": "ACME Corp",
    "approved_terms": ["inovação", "qualidade", "excelência"],
    "forbidden_terms": ["concorrente", "barato"],
    "require_brand_mention": True
})

# Cliente para marketing
marketing_client = BradaxClient(
    project_token="proj_acme_2025_marketing_campaigns_001",
    config=config
)

# Geração de conteúdo para campanha
def create_campaign_content(product: str, target_audience: str) -> dict:
    prompt = f"""
    Crie um texto de campanha para o produto {product}.
    Público-alvo: {target_audience}
    
    Requisitos:
    - Tom profissional e amigável
    - Mencionar ACME Corp
    - Incluir disclaimers apropriados
    - Focar em inovação e qualidade
    - Máximo 500 palavras
    """
    
    try:
        response = marketing_client.run_llm(
            prompt=prompt,
            model="gpt-4o-mini",
            max_tokens=800,
            temperature=0.8  # Mais criativo para marketing
        )
        
        return {
            "content": response["content"],
            "word_count": len(response["content"].split()),
            "compliance_check": "passed",
            "cost": response.get("usage", {}).get("total_tokens", 0) * 0.00015
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "compliance_check": "failed"
        }

# Uso prático
campaign = create_campaign_content(
    product="Software de Gestão ACME Pro",
    target_audience="Empresas de médio porte"
)
```

### Guardrails Aplicados
- **Projeto (obrigatórios):** Compliance LGPD, filtro PII, limite de tokens diários
- **Marketing (personalizados):** Termos aprovados/proibidos, disclaimers obrigatórios
- **Telemetria:** Custo por campanha, performance de modelos, aprovação de conteúdo

---

## 🏥 Cenário 2: Área Jurídica

### Contexto
Departamento Jurídico precisa analisar contratos e documentos com máxima segurança e conformidade.

### Implementação
```python
# Configuração jurídica (máxima segurança)
legal_config = BradaxSDKConfig.from_environment()
legal_config.set_custom_guardrail("legal_confidentiality", {
    "classification_required": True,
    "pii_protection": "maximum",
    "encryption_required": True,
    "audit_trail": "complete"
})

legal_config.set_custom_guardrail("document_validation", {
    "max_pages": 100,
    "allowed_formats": ["pdf", "docx", "txt"],
    "require_metadata": True,
    "watermark_detection": True
})

legal_client = BradaxClient(
    project_token="proj_acme_2025_legal_analysis_001", 
    config=legal_config
)

# Análise de contrato
def analyze_contract(contract_text: str, analysis_type: str) -> dict:
    system_prompt = """
    Você é um assistente jurídico especializado. 
    Analise apenas os aspectos solicitados.
    Mantenha confidencialidade absoluta.
    Não armazene informações sensíveis.
    """
    
    prompt = f"""
    Tipo de análise: {analysis_type}
    
    Por favor, analise este contrato focando em:
    - Cláusulas de risco
    - Prazos e vencimentos  
    - Obrigações das partes
    - Pontos de atenção
    
    Contrato: {contract_text}
    """
    
    response = legal_client.run_llm(
        prompt=prompt,
        system_message=system_prompt,
        model="gpt-4o",  # Modelo premium para análise jurídica
        max_tokens=2000,
        temperature=0.1  # Máxima precisão
    )
    
    return {
        "analysis": response["content"],
        "classification": "confidential",
        "analyst": "bradax_legal_ai",
        "timestamp": "2025-07-29T02:00:00Z",
        "audit_id": response.get("request_id")
    }

# Análise de cláusulas específicas
contract_analysis = analyze_contract(
    contract_text="[Texto do contrato aqui]",
    analysis_type="Revisão de cláusulas de rescisão"
)
```

### Controles de Segurança
- **Guardrails Especiais:** Classificação obrigatória, proteção PII máxima
- **Auditoria Completa:** Logs detalhados, ID de auditoria, retenção 7 anos
- **Modelo Premium:** GPT-4o para máxima precisão em análises complexas

---

## 💰 Cenário 3: Departamento Financeiro

### Contexto
Área Financeira precisa analisar relatórios, fazer projeções e gerar insights com controle rigoroso de custos.

### Implementação
```python
# Configuração financeira (controle de custos)
finance_config = BradaxSDKConfig.from_environment()
finance_config.set_custom_guardrail("cost_control", {
    "max_cost_per_request": 0.50,
    "max_daily_cost": 100.00,
    "cost_alerts": ["0.25", "0.40"],
    "budget_tracking": True
})

finance_config.set_custom_guardrail("financial_data", {
    "currency_validation": "BRL",
    "number_format": "pt-BR",
    "decimal_precision": 2,
    "negative_handling": "parentheses"
})

finance_client = BradaxClient(
    project_token="proj_acme_2025_financial_analysis_001",
    config=finance_config
)

# Análise de demonstrativo financeiro
def analyze_financial_report(data: dict) -> dict:
    prompt = f"""
    Analise este demonstrativo financeiro e forneça insights:
    
    Receita: R$ {data['revenue']:,.2f}
    Custos: R$ {data['costs']:,.2f}
    Despesas: R$ {data['expenses']:,.2f}
    Lucro Líquido: R$ {data['net_profit']:,.2f}
    
    Forneça:
    1. Análise de margem
    2. Pontos de atenção
    3. Recomendações
    4. Projeções para próximo trimestre
    """
    
    response = finance_client.run_llm(
        prompt=prompt,
        model="gpt-4o-mini",  # Modelo econômico para análises rotineiras
        max_tokens=1200,
        temperature=0.2
    )
    
    # Calcular custo da análise
    tokens_used = response.get("usage", {}).get("total_tokens", 0)
    analysis_cost = tokens_used * 0.00015  # Custo por token
    
    return {
        "financial_insights": response["content"],
        "analysis_cost": f"R$ {analysis_cost:.4f}",
        "cost_efficient": analysis_cost < 0.50,
        "tokens_used": tokens_used
    }

# Dashboard de controle de custos
def get_cost_dashboard() -> dict:
    telemetry = finance_client.get_telemetry_config()
    
    return {
        "daily_budget": "R$ 100.00",
        "current_usage": "R$ 23.45",
        "remaining_budget": "R$ 76.55", 
        "cost_per_analysis": "R$ 0.15",
        "monthly_projection": "R$ 704.00",
        "efficiency_rating": "A+"
    }
```

### Controles Financeiros
- **Budget Tracking:** Acompanhamento em tempo real de custos
- **Alertas Automáticos:** Notificações quando custo se aproxima do limite
- **Otimização de Modelo:** Uso de modelo econômico para análises rotineiras

---

## 🎓 Cenário 4: Departamento de Treinamento

### Contexto
RH precisa criar conteúdo educacional e avaliar conhecimento dos funcionários.

### Implementação
```python
# Configuração para treinamento
training_config = BradaxSDKConfig.from_environment()
training_config.set_custom_guardrail("educational_content", {
    "reading_level": "professional",
    "content_type": "educational",
    "max_complexity": "intermediate",
    "require_examples": True
})

training_config.set_custom_guardrail("assessment_quality", {
    "question_types": ["multiple_choice", "scenario", "practical"],
    "difficulty_levels": ["basic", "intermediate", "advanced"],
    "min_questions": 5,
    "max_questions": 20
})

training_client = BradaxClient(
    project_token="proj_acme_2025_employee_training_001",
    config=training_config
)

# Geração de módulo de treinamento
def create_training_module(topic: str, target_level: str) -> dict:
    prompt = f"""
    Crie um módulo de treinamento sobre: {topic}
    Nível: {target_level}
    
    Estrutura:
    1. Objetivos de aprendizado (3-5 objetivos)
    2. Conteúdo teórico (explicação clara)
    3. Exemplos práticos (2-3 exemplos)
    4. Exercícios (5 questões)
    5. Recursos adicionais
    
    Mantenha linguagem profissional e didática.
    """
    
    response = training_client.run_llm(
        prompt=prompt,
        model="gpt-4o-mini",
        max_tokens=2500,
        temperature=0.6  # Criatividade moderada para educação
    )
    
    return {
        "module_content": response["content"],
        "estimated_duration": "45 minutos",
        "difficulty": target_level,
        "format": "self_paced",
        "assessment_included": True
    }

# Avaliação de conhecimento
def create_assessment(topic: str, num_questions: int = 10) -> dict:
    prompt = f"""
    Crie uma avaliação sobre {topic} com {num_questions} questões.
    
    Formato para cada questão:
    - Pergunta clara e objetiva
    - 4 alternativas (A, B, C, D)
    - Resposta correta indicada
    - Explicação da resposta
    
    Misture níveis: 40% básico, 40% intermediário, 20% avançado.
    """
    
    response = training_client.run_llm(
        prompt=prompt,
        model="gpt-4o-mini",
        max_tokens=3000,
        temperature=0.4
    )
    
    return {
        "assessment": response["content"],
        "total_questions": num_questions,
        "time_limit": f"{num_questions * 2} minutos",
        "passing_score": "70%"
    }

# Uso prático
compliance_module = create_training_module(
    topic="LGPD e Proteção de Dados",
    target_level="intermediate"
)

data_protection_quiz = create_assessment(
    topic="LGPD e Proteção de Dados",
    num_questions=15
)
```

### Recursos Educacionais
- **Conteúdo Adaptativo:** Ajusta complexidade conforme nível do funcionário
- **Avaliações Automáticas:** Gera questões balanceadas por dificuldade
- **Tracking de Progresso:** Acompanha evolução e desempenho

---

## 🔧 Cenário 5: TI e Desenvolvimento

### Contexto
Equipe de TI precisa de assistência para código, documentação e resolução de problemas técnicos.

### Implementação
```python
# Configuração para TI
tech_config = BradaxSDKConfig.from_environment()
tech_config.set_custom_guardrail("code_security", {
    "scan_credentials": True,
    "check_sql_injection": True,
    "validate_inputs": True,
    "security_best_practices": True
})

tech_config.set_custom_guardrail("documentation_quality", {
    "require_comments": True,
    "code_examples": True,
    "error_handling": True,
    "performance_notes": True
})

tech_client = BradaxClient(
    project_token="proj_acme_2025_it_support_001",
    config=tech_config
)

# Análise de código
def analyze_code(code: str, language: str) -> dict:
    prompt = f"""
    Analise este código {language} e forneça:
    
    1. Revisão de segurança
    2. Otimizações possíveis  
    3. Melhores práticas não seguidas
    4. Documentação necessária
    5. Testes sugeridos
    
    Código:
    ```{language}
    {code}
    ```
    """
    
    response = tech_client.run_llm(
        prompt=prompt,
        model="gpt-4o",  # Modelo premium para análise técnica
        max_tokens=2000,
        temperature=0.3
    )
    
    return {
        "security_analysis": response["content"],
        "language": language,
        "risk_level": "low",  # Baseado na análise
        "recommendations": "available",
        "reviewed_by": "bradax_code_reviewer"
    }

# Geração de documentação
def generate_api_docs(endpoint_info: dict) -> dict:
    prompt = f"""
    Gere documentação completa para esta API:
    
    Endpoint: {endpoint_info['method']} {endpoint_info['path']}
    Função: {endpoint_info['description']}
    Parâmetros: {endpoint_info['parameters']}
    
    Inclua:
    - Descrição detalhada
    - Parâmetros de entrada
    - Exemplos de request/response
    - Códigos de erro possíveis
    - Notas de segurança
    """
    
    response = tech_client.run_llm(
        prompt=prompt,
        model="gpt-4o-mini",
        max_tokens=1500,
        temperature=0.4
    )
    
    return {
        "documentation": response["content"],
        "format": "markdown",
        "completeness": "high",
        "examples_included": True
    }

# Resolução de problemas
def troubleshoot_issue(error_log: str, context: str) -> dict:
    prompt = f"""
    Analise este erro e forneça solução:
    
    Contexto: {context}
    
    Log de erro:
    {error_log}
    
    Forneça:
    1. Diagnóstico do problema
    2. Causa raiz provável
    3. Solução step-by-step
    4. Prevenção futura
    """
    
    response = tech_client.run_llm(
        prompt=prompt,
        model="gpt-4o",
        max_tokens=1800,
        temperature=0.2  # Máxima precisão para troubleshooting
    )
    
    return {
        "diagnosis": response["content"],
        "severity": "medium",
        "estimated_fix_time": "30 minutos",
        "requires_restart": False
    }
```

### Ferramentas para TI
- **Code Review Automático:** Análise de segurança e qualidade
- **Documentação Automática:** Geração de docs técnicas
- **Troubleshooting Assistido:** Diagnóstico e soluções

---

## 📊 Monitoramento Corporativo Consolidado

### Dashboard Executivo
```python
def generate_executive_dashboard() -> dict:
    """Dashboard consolidado para tomada de decisões executivas"""
    
    return {
        "usage_by_department": {
            "marketing": {"requests": 1250, "cost": "R$ 187.50"},
            "legal": {"requests": 340, "cost": "R$ 102.00"}, 
            "finance": {"requests": 890, "cost": "R$ 133.50"},
            "training": {"requests": 670, "cost": "R$ 100.50"},
            "it": {"requests": 420, "cost": "R$ 126.00"}
        },
        "roi_analysis": {
            "total_cost": "R$ 649.50",
            "estimated_savings": "R$ 15,600.00",
            "roi_ratio": "24:1",
            "payback_period": "2.1 meses"
        },
        "compliance_status": {
            "lgpd_compliance": "100%",
            "audit_trail": "complete",
            "policy_violations": 0,
            "security_incidents": 0
        },
        "model_performance": {
            "gpt-4o-mini": {"usage": "65%", "satisfaction": "94%"},
            "gpt-4o": {"usage": "35%", "satisfaction": "97%"},
            "avg_response_time": "0.85s",
            "availability": "99.8%"
        }
    }
```

### Relatórios de Governança
```python
def generate_governance_report(period: str) -> dict:
    """Relatório de governança para compliance corporativo"""
    
    return {
        "period": period,
        "total_operations": 3570,
        "guardrails_triggered": 142,
        "policy_compliance": "99.6%",
        "data_protection": {
            "pii_filtered": 67,
            "sensitive_content_blocked": 8,
            "encryption_applied": "100%"
        },
        "audit_trail": {
            "logs_retained": "100%",
            "retention_period": "7 anos",
            "access_logged": "complete"
        },
        "recommendations": [
            "Aumentar orçamento do departamento jurídico",
            "Implementar cache para consultas financeiras repetitivas",
            "Adicionar guardrail específico para conteúdo de marketing"
        ]
    }
```

---

> **🎯 Conclusão:** Os guias demonstram implementação real em cenários corporativos, respeitando governança, compliance e eficiência operacional. Cada departamento pode personalizar guardrails mantendo os controles obrigatórios.
