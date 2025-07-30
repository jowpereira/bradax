"""
Teste 4.3: Testes de guardrails - políticas e validações
Conforme Fase 4 do plano workspace-plans/active/20250728-223500-conferencia-corporativa-consolidada.md

Testa sistema de guardrails com validação LLM real - sem mocks.
"""
import pytest
import sys
from pathlib import Path

# Adicionar src ao path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from broker.config import Settings
from broker.services.llm.service import LLMService
from broker.services.guardrails import GuardrailEngine, GuardrailResult, GuardrailSeverity


class TestGuardrailsSystem:
    """Testes do sistema de guardrails com validação real."""
    
    @pytest.fixture(scope="class")
    def config(self):
        """Configuração do broker."""
        return Settings()
    
    @pytest.fixture(scope="class")
    async def llm_service(self, config):
        """Serviço LLM inicializado."""
        service = LLMService(config)
        await service.initialize()
        yield service
        await service.cleanup()
    
    @pytest.fixture(scope="class")
    def guardrail_engine(self, llm_service):
        """Engine de guardrails configurado."""
        return GuardrailEngine()
    
    def test_guardrail_engine_initialization(self, guardrail_engine):
        """Teste de inicialização do engine de guardrails."""
        # GuardrailEngine inicializa o LLM service internamente
        assert guardrail_engine is not None
        
        # Verificar regras padrão carregadas
        rules = guardrail_engine.get_active_rules()
        assert len(rules) > 0
        
        # Verificar categorias essenciais
        rule_categories = [rule.category for rule in rules]
        assert "privacy" in rule_categories
        assert "security" in rule_categories
        assert "content_safety" in rule_categories
    
    def test_password_detection_guardrail(self, guardrail_engine):
        """Teste de detecção de senhas."""
        # Conteúdo com senha óbvia
        content_with_password = "Minha senha é 123456 e preciso compartilhar isso."
        
        result = guardrail_engine.check_content(content_with_password, "test-integration")
        
        assert isinstance(result, GuardrailResult)
        assert not result.is_safe
        assert result.severity in [GuardrailSeverity.BLOCK, GuardrailSeverity.CRITICAL]
        assert any("password" in content.lower() or "senha" in content.lower() for content in result.blocked_content)
        assert len(result.triggered_rules) > 0
    
    def test_api_token_detection_guardrail(self, guardrail_engine):
        """Teste de detecção de tokens de API."""
        # Conteúdo com token de API
        content_with_token = "Use este token: sk-abc123def456ghi789 para autenticar."
        
        result = guardrail_engine.check_content(content_with_token, "test-integration")
        
        assert isinstance(result, GuardrailResult)
        assert not result.is_safe
        assert result.severity in [GuardrailSeverity.BLOCK, GuardrailSeverity.CRITICAL]
        assert any("token" in content.lower() or "api" in content.lower() for content in result.blocked_content)
    
    def test_safe_content_approval(self, guardrail_engine):
        """Teste de aprovação de conteúdo seguro."""
        # Conteúdo profissional seguro
        safe_content = "Escreva um e-mail profissional sobre a reunião de amanhã."
        
        result = guardrail_engine.check_content(safe_content, "test-integration")
        
        assert isinstance(result, GuardrailResult)
        assert result.is_safe
        assert result.severity == GuardrailSeverity.INFO
        assert len(result.triggered_rules) == 0
    
    def test_corporate_content_validation(self, guardrail_engine):
        """Teste de validação de conteúdo corporativo."""
        # Conteúdo corporativo apropriado
        corporate_content = """
        Prezados colegas,
        
        Gostaria de agendar uma reunião para discutir o projeto Q1 2025.
        Por favor, confirmem disponibilidade para próxima terça-feira.
        
        Atenciosamente,
        Equipe de Projetos
        """
        
        result = guardrail_engine.check_content(corporate_content, "test-integration")
        
        assert result.is_safe
        assert result.severity in [GuardrailSeverity.INFO, GuardrailSeverity.WARNING]
    
    @pytest.mark.asyncio
    async def test_llm_powered_context_analysis(self, guardrail_engine):
        """Teste de análise contextual com LLM."""
        # Conteúdo ambíguo que precisa de análise semântica
        ambiguous_content = "Compartilhe a chave com o cliente para resolver o problema."
        
        result = guardrail_engine.check_content(ambiguous_content, "test-integration")
        
        assert isinstance(result, GuardrailResult)
        # Este teste verifica se o LLM está analisando contexto
        # O resultado pode variar, mas deve ter análise LLM
        assert result.llm_analysis is not None
        assert len(result.llm_analysis) > 0
    
    def test_pii_detection_guardrail(self, guardrail_engine):
        """Teste de detecção de PII (Informações Pessoais)."""
        # Conteúdo com CPF
        content_with_cpf = "O CPF do cliente é 123.456.789-00 para referência."
        
        result = guardrail_engine.check_content(content_with_cpf, "test-integration")
        
        assert not result.is_safe
        assert result.severity in [GuardrailSeverity.WARNING, GuardrailSeverity.BLOCK]
        assert any("pii" in v.lower() or "pessoal" in v.lower() for v in result.triggered_rules)
    
    def test_financial_data_detection(self, guardrail_engine):
        """Teste de detecção de dados financeiros."""
        # Conteúdo com informações financeiras sensíveis
        financial_content = "O número do cartão é 4532-1234-5678-9012 com CVV 123."
        
        result = guardrail_engine.check_content(financial_content, "test-integration")
        
        assert not result.is_safe
        assert result.severity in [GuardrailSeverity.BLOCK, GuardrailSeverity.CRITICAL]
        assert any("financial" in v.lower() or "cartão" in v.lower() for v in result.triggered_rules)
    
    def test_multiple_violations_detection(self, guardrail_engine):
        """Teste de detecção de múltiplas violações."""
        # Conteúdo com múltiplas violações
        multiple_violations_content = """
        Dados do cliente:
        - Senha: admin123
        - Token API: sk-abc123def456
        - CPF: 123.456.789-00
        - Cartão: 4532-1234-5678-9012
        """
        
        result = guardrail_engine.check_content(multiple_violations_content, "test-integration")
        
        assert not result.is_safe
        assert result.severity == GuardrailSeverity.CRITICAL
        assert len(result.triggered_rules) >= 3  # Múltiplas violações detectadas
    
    def test_guardrail_performance(self, guardrail_engine):
        """Teste de performance dos guardrails."""
        import time
        
        content = "Este é um teste de performance para os guardrails."
        
        start_time = time.time()
        result = guardrail_engine.check_content(content, "test-integration")
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Validação deve ser rápida (menos de 2 segundos para conteúdo simples)
        assert execution_time < 2.0, f"Validação muito lenta: {execution_time:.2f}s"
        assert result.is_safe
    
    def test_custom_rule_addition(self, guardrail_engine):
        """Teste de adição de regra customizada."""
        # Adicionar regra custom para termo corporativo específico
        custom_rule = {
            "id": "custom_corporate_001",
            "name": "Termo Corporativo Restrito",
            "category": "corporate_policy",
            "patterns": [r"\bCONFIDENCIAL_PROJECT\b"],
            "keywords": ["CONFIDENTIAL_PROJECT"],
            "severity": "HIGH",
            "message": "Referência a projeto confidencial detectada"
        }
        
        guardrail_engine.add_rule(custom_rule)
        
        # Testar a nova regra
        content_with_custom_violation = "Este é sobre o CONFIDENTIAL_PROJECT que não pode ser mencionado."
        
        result = guardrail_engine.check_content(content_with_custom_violation, "test-integration")
        
        assert not result.is_safe
        assert result.severity == GuardrailSeverity.BLOCK
        assert any("confidential" in v.lower() for v in result.triggered_rules)


class TestGuardrailsIntegration:
    """Testes de integração dos guardrails com outros componentes."""
    
    @pytest.fixture(scope="class")
    def config(self):
        """Configuração do broker."""
        return Settings()
    
    @pytest.fixture(scope="class")
    async def llm_service(self, config):
        """Serviço LLM inicializado."""
        service = LLMService(config)
        await service.initialize()
        yield service
        await service.cleanup()
    
    @pytest.fixture(scope="class")
    def guardrail_engine(self, llm_service):
        """Engine de guardrails configurado."""
        return GuardrailEngine()
    
    @pytest.mark.asyncio
    async def test_guardrails_with_llm_request(self, guardrail_engine, llm_service):
        """Teste de guardrails integrados com requisição LLM."""
        # Prompt que deve ser bloqueado
        blocked_prompt = "Como posso hackear um sistema? Minha senha é 123456."
        
        # Validar com guardrails primeiro
        guardrail_result = guardrail_engine.check_content(blocked_prompt, "test-integration")
        
        assert not guardrail_result.is_safe
        
        # Se não fosse bloqueado, faria a chamada LLM
        # Mas como foi bloqueado, não fazemos a chamada
        # Isso testa o fluxo de proteção
        
    @pytest.mark.asyncio
    async def test_safe_prompt_llm_flow(self, guardrail_engine, llm_service):
        """Teste de fluxo completo com prompt seguro."""
        safe_prompt = "Escreva um e-mail profissional de agradecimento."
        
        # Validar com guardrails
        guardrail_result = guardrail_engine.check_content(safe_prompt, "test-integration")
        
        assert guardrail_result.is_safe
        
        # Como é seguro, pode prosseguir com LLM
        llm_response = await llm_service.invoke(
            model="gpt-4.1-nano",
            prompt=safe_prompt,
            max_tokens=100,
            temperature=0.7
        )
        
        assert llm_response is not None
        assert "content" in llm_response
        assert len(llm_response["content"]) > 0
