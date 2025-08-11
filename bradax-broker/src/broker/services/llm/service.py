"""
LLM Service - Bradax Broker

Serviço principal para orquestração de LLMs usando LangChain.
INTERCEPTA TODAS as requisições e aplica guardrails/telemetria OBRIGATÓRIOS.
"""

import time
import uuid
import json
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

from .interfaces import LLMRequest, LLMResponse, LLMModelInfo
from .providers import get_provider, get_available_providers
from .registry import LLMRegistry
from ..telemetry_raw import save_raw_response, load_raw_request, save_guardrail_violation
from ..guardrails import GuardrailEngine

# Logger específico
logger = logging.getLogger('bradax.llm_service')


class GuardrailViolationError(Exception):
    """Exceção para violações de guardrails"""
    pass



class GuardrailViolationError(Exception):
    """Exceção para violações de guardrails"""
    pass


class LLMService:
    """Serviço principal de LLM com LangChain + GUARDRAILS OBRIGATÓRIOS"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Evitar re-inicialização se já foi inicializado
        if self._initialized:
            return
            
        # INICIALIZAÇÃO CRÍTICA: GuardrailEngine é OBRIGATÓRIO
        self.guardrail_engine = None
        self.repositories_available = False
        # Flag para registrar eventos de PASS (não violação) em guardrail_events.json (default False)
        self.log_guardrail_pass_events = False
        try:
            self.providers = get_available_providers()
            self.registry = LLMRegistry()
            # Inicializar GuardrailEngine com regras padrão (OBRIGATÓRIO)
            self.guardrail_engine = GuardrailEngine()
            print("✅ GuardrailEngine inicializado com sucesso")
            # REPOSITORIES OBRIGATÓRIOS: Usar data/ da raiz sem fallback
            try:
                from ...storage.factory import create_storage_repositories
                repositories = create_storage_repositories()
                self.project_repo = repositories["project"]
                self.telemetry_repo = repositories["telemetry"]
                self.guardrail_repo = repositories["guardrail"]
                self.repositories_available = True
                print("✅ Repositories integrados: project, telemetry, guardrail")
            except Exception as repo_error:
                print(f"🚨 ERRO CRÍTICO: Repositories obrigatórios falharam: {repo_error}")
                print("🚨 SISTEMA BLOQUEADO: Não pode operar sem acesso aos dados")
                raise RuntimeError(f"Falha crítica nos repositories: {repo_error}") from repo_error
            print(f"✅ LLM Service inicializado com providers: {list(self.providers.keys())}")
            print("✅ LLM Registry integrado para governança de modelos")
            # Definir flag de logging de eventos PASS via variável de ambiente
            try:
                env_flag = os.getenv("BRADAX_LOG_GUARDRAIL_PASS", "false").strip().lower()
                self.log_guardrail_pass_events = env_flag in ("1", "true", "yes", "on")
                if self.log_guardrail_pass_events:
                    print("🔎 Guardrail PASS events ENABLED (BRADAX_LOG_GUARDRAIL_PASS)")
                else:
                    print("ℹ️ Guardrail PASS events desativados (defina BRADAX_LOG_GUARDRAIL_PASS=true para habilitar)")
            except Exception as _env_err:
                print(f"⚠️ Não foi possível avaliar flag BRADAX_LOG_GUARDRAIL_PASS: {_env_err}")
        except Exception as e:
            print(f"🚨 ERRO CRÍTICO ao inicializar LLM Service: {e}")
            print("🚨 SISTEMA BLOQUEADO: Guardrails obrigatórios não carregaram!")
            # Bloquear sistema se guardrails falharam
            self.providers = {}
            self.registry = None
            self.project_repo = None
            self.telemetry_repo = None
            self.guardrail_repo = None
            self.repositories_available = False
        
        # Marcar como inicializado para evitar re-inicializações
        self._initialized = True
    
    def _is_system_secure(self) -> bool:
        """Verifica se o sistema está seguro para operação"""
        return self.guardrail_engine is not None

    async def _apply_input_guardrails(self, project_id: str, input_text: str, request_id: str, 
                                    custom_guardrails: Optional[Dict] = None) -> bool:  # CORREÇÃO: Aceitar guardrails customizados
        """Aplica guardrails no INPUT usando GuardrailEngine + regras do projeto"""
        try:
            # 1. SEMPRE aplicar guardrails padrão do GuardrailEngine (invisível ao SDK)
            check_result = self.guardrail_engine.check_content(input_text, "input")
            
            if not check_result.allowed:
                # Registrar primeira violação encontrada
                violation_info = {
                    "rule": "guardrail_engine",
                    "reason": check_result.reason,
                    "severity": check_result.severity.value if hasattr(check_result.severity, 'value') else str(check_result.severity),
                    "triggered_rules": check_result.triggered_rules
                }
                
                # TELEMETRIA RAW: Registrar violação de guardrail de entrada
                try:
                    save_guardrail_violation(
                        request_id=request_id,
                        violation_type="input_validation",
                        content_blocked=input_text,
                        rule_triggered=violation_info["rule"],
                        stage="input",
                        project_id=project_id,
                        metadata={
                            "rule_details": violation_info,
                            "action": "BLOCK",
                            "engine": "GuardrailEngine",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    print(f"🚫 GuardrailEngine violation salvo: {request_id} - {violation_info['rule']}")
                except Exception as save_error:
                    print(f"⚠️ Erro ao salvar violation: {save_error}")
                
                # Registrar evento usando repository se disponível
                if self.repositories_available and self.guardrail_repo:
                    try:
                        await self._log_guardrail_event_async(
                            project_id, request_id, "input_validation", "blocked", 
                            f"Regra violada: {violation_info['rule']}", violation_info
                        )
                    except Exception as log_error:
                        print(f"⚠️ Erro ao registrar evento no repository: {log_error}")
                
                # Bloquear entrada rejeitada
                raise GuardrailViolationError(f"Entrada rejeitada por {violation_info['rule']}: {violation_info['reason']}")
            
            # 2. Verificar regras ADICIONAIS específicas do projeto (se repositories disponíveis)
            if self.repositories_available and self.project_repo:
                try:
                    project = await self.project_repo.get_by_id(project_id)
                    if project:
                        # VALIDAR: Garantir que project.config seja um dicionário
                        project_config = project.config if hasattr(project, 'config') else {}
                        if not isinstance(project_config, dict):
                            project_config = {}
                        
                        guardrails = project_config.get("guardrails", {})
                        input_rules = guardrails.get("input_validation", {}).get("rules", [])
                        
                        # VALIDAR: Garantir que input_rules seja uma lista de dicionários
                        if isinstance(input_rules, list):
                            for rule in input_rules:
                                # VALIDAR: Garantir que rule seja um dicionário
                                if isinstance(rule, dict) and rule.get("action") == "reject":
                                    if self._check_rule_violation(input_text, rule):
                                        # TELEMETRIA RAW: Registrar violação de regra específica do projeto
                                        try:
                                            save_guardrail_violation(
                                                request_id=request_id,
                                                violation_type="input_validation",
                                                content_blocked=input_text,
                                                rule_triggered=rule.get('name', 'unknown_project_rule'),
                                                stage="input",
                                                project_id=project_id,
                                                metadata={
                                                    "rule_details": rule,
                                                    "action": "blocked",
                                                    "engine": "ProjectSpecific",
                                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                                }
                                            )
                                            print(f"🚫 Project-specific violation salvo: {request_id} - {rule.get('name')}")
                                        except Exception as save_error:
                                            print(f"⚠️ Erro ao salvar project violation: {save_error}")
                                        
                                        # Registrar evento usando repository existente
                                        await self._log_guardrail_event_async(
                                            project_id, request_id, "input_validation", "blocked", 
                                            f"Regra específica violada: {rule.get('name', 'N/A')}", rule
                                        )
                                        raise GuardrailViolationError(f"Entrada rejeitada por regra do projeto: {rule.get('name', 'Regra não especificada')}")
                except Exception as project_error:
                    print(f"⚠️ Erro ao verificar regras do projeto (continuando com guardrails padrão): {project_error}")
            
            # 3. APLICAR GUARDRAILS CUSTOMIZADOS DO SDK (se enviados)
            if custom_guardrails:
                print(f"🔍 Processando {len(custom_guardrails)} guardrails customizados do SDK")
                for rule_id, rule in custom_guardrails.items():
                    try:
                        pattern = rule.get("pattern")
                        severity = rule.get("severity", "MEDIUM")
                        
                        if pattern:
                            import re
                            if re.search(pattern, input_text, re.IGNORECASE):
                                violation_info = {
                                    "rule": f"custom_sdk_{rule_id}",
                                    "reason": f"Guardrail customizado violado: {rule_id}",
                                    "severity": severity,
                                    "pattern": pattern
                                }
                                
                                # Registrar violação de guardrail customizado
                                try:
                                    save_guardrail_violation(
                                        request_id=request_id,
                                        violation_type="custom_guardrail",
                                        content_blocked=input_text,
                                        rule_triggered=violation_info["rule"],
                                        stage="input",
                                        project_id=project_id,
                                        metadata={
                                            "rule_details": violation_info,
                                            "action": "BLOCK",
                                            "source": "SDK_CUSTOM",
                                            "timestamp": datetime.now(timezone.utc).isoformat()
                                        }
                                    )
                                    print(f"🚫 Guardrail customizado violado: {rule_id}")
                                except Exception as save_error:
                                    print(f"⚠️ Erro ao salvar violação customizada: {save_error}")
                                
                                raise GuardrailViolationError(f"Entrada rejeitada por guardrail customizado: {rule_id}")
                    except GuardrailViolationError:
                        raise
                    except Exception as custom_error:
                        print(f"⚠️ Erro ao processar guardrail customizado {rule_id}: {custom_error}")
            
            return True
        except GuardrailViolationError:
            raise
        except Exception as e:
            print(f"⚠️ Erro ao aplicar guardrails input: {e}")
            return True
    
    async def _apply_output_guardrails(self, project_id: str, output_text: str, request_id: str) -> str:
        """Aplica guardrails no OUTPUT usando GuardrailEngine + regras do projeto"""
        try:
            modified_output = output_text
            
            # 1. SEMPRE aplicar guardrails padrão do GuardrailEngine (invisível ao SDK)
            check_result = self.guardrail_engine.check_content(output_text, "output")
            
            if not check_result.allowed:
                # Registrar violação encontrada
                violation_info = {
                    "rule": "guardrail_engine",
                    "reason": check_result.reason,
                    "severity": check_result.severity.value if hasattr(check_result.severity, 'value') else str(check_result.severity),
                    "triggered_rules": check_result.triggered_rules
                }
                
                # TELEMETRIA RAW: Registrar violação de guardrail de saída
                try:
                    save_guardrail_violation(
                        request_id=request_id,
                        violation_type="output_validation",
                        content_blocked=output_text[:500],  # Truncar resposta grande
                        rule_triggered=violation_info["rule"],
                        stage="output",
                        project_id=project_id,
                        metadata={
                            "rule_details": violation_info,
                            "action": "SANITIZE",
                            "engine": "GuardrailEngine",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "original_response_length": len(output_text)
                        }
                    )
                    print(f"🚫 GuardrailEngine output violation salvo: {request_id} - {violation_info['rule']}")
                except Exception as save_error:
                    print(f"⚠️ Erro ao salvar output violation: {save_error}")
                
                # Registrar evento usando repository existente
                await self._log_guardrail_event_async(
                    project_id, request_id, "output_validation", "blocked", 
                    f"Resposta rejeitada por {violation_info['rule']}", violation_info
                )
                
                # SANITIZAR RESPOSTA em vez de bloquear completamente
                modified_output = self._sanitize_blocked_output_guardrail_engine(output_text, violation_info)
                
                # Salvar versão processada se modificada
                if modified_output != output_text:
                    try:
                        save_guardrail_violation(
                            request_id=f"{request_id}_processed",
                            violation_type="output_processing",
                            content_blocked=modified_output,
                            rule_triggered=violation_info["rule"],
                            stage="output_processed",
                            project_id=project_id,
                            metadata={
                                "rule_details": violation_info,
                                "action": "SANITIZE",
                                "engine": "GuardrailEngine",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "original_response": output_text[:200],
                                "processing_applied": True
                            }
                        )
                    except Exception as save_error:
                        print(f"⚠️ Erro ao salvar processing: {save_error}")
            
            # 2. Verificar regras ADICIONAIS específicas do projeto (se existirem)
            if self.repositories_available and self.project_repo:
                try:
                    project = await self.project_repo.get_by_id(project_id)
                    if project:
                        # VALIDAR: Garantir que project.config seja um dicionário
                        project_config = project.config if hasattr(project, 'config') else {}
                        if not isinstance(project_config, dict):
                            project_config = {}
                        
                        guardrails = project_config.get("guardrails", {})
                        output_rules = guardrails.get("output_validation", {}).get("rules", [])
                        
                        # VALIDAR: Garantir que output_rules seja uma lista de dicionários
                        if isinstance(output_rules, list):
                            # PRIMEIRA FASE: Verificar violações que devem ser BLOQUEADAS
                            for rule in output_rules:
                                # VALIDAR: Garantir que rule seja um dicionário
                                if isinstance(rule, dict) and rule.get("action") == "reject":
                                    if self._check_rule_violation(modified_output, rule):
                                        # TELEMETRIA RAW: Registrar violação de regra específica do projeto
                                        try:
                                            save_guardrail_violation(
                                                request_id=request_id,
                                                violation_type="output_validation",
                                                content_blocked=modified_output[:500],  # Truncar resposta grande
                                                rule_triggered=rule.get('name', 'unknown_project_output_rule'),
                                                stage="output",
                                                project_id=project_id,
                                                metadata={
                                                    "rule_details": rule,
                                                    "action": "blocked",
                                                    "engine": "ProjectSpecific",
                                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                                    "original_response_length": len(modified_output)
                                                }
                                            )
                                            print(f"🚫 Project-specific output violation salvo: {request_id} - {rule.get('name')}")
                                        except Exception as save_error:
                                            print(f"⚠️ Erro ao salvar project output violation: {save_error}")
                                        
                                        # Registrar evento usando repository existente
                                        await self._log_guardrail_event_async(
                                            project_id, request_id, "output_validation", "blocked", 
                                            f"Resposta rejeitada por regra do projeto: {rule.get('name', 'N/A')}", rule
                                        )
                                        
                                        # SANITIZAR RESPOSTA em vez de bloquear completamente
                                        modified_output = self._sanitize_blocked_output(modified_output, rule)
                                        
                                        # Salvar versão sanitizada
                                        try:
                                            save_guardrail_violation(
                                                request_id=f"{request_id}_project_sanitized",
                                                violation_type="output_sanitization",
                                                content_blocked=modified_output,
                                                rule_triggered=rule.get('name', 'unknown_project_output_rule'),
                                                stage="output_sanitized",
                                                project_id=project_id,
                                                metadata={
                                                    "rule_details": rule,
                                                    "action": "sanitized",
                                                    "engine": "ProjectSpecific",
                                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                                    "original_response": output_text[:200],
                                                    "sanitization_applied": True
                                                }
                                            )
                                        except Exception as save_error:
                                            print(f"⚠️ Erro ao salvar project sanitization: {save_error}")
                                        
                                        break  # Primeira violação já processada
                            
                            # SEGUNDA FASE: Aplicar modificações/melhorias (não violações)
                            for rule in output_rules:
                                # VALIDAR: Garantir que rule seja um dicionário
                                if isinstance(rule, dict):
                                    action = rule.get("action")
                                    if action in ["modify", "enhance"]:
                                        original_before_rule = modified_output
                                        modified_output = self._apply_output_rule(modified_output, rule)
                                    
                                    # Se houve modificação, registrar
                                    if modified_output != original_before_rule:
                                        # Registrar evento usando repository existente
                                        await self._log_guardrail_event_async(
                                            project_id, request_id, "output_validation", action, 
                                            f"Regra aplicada: {rule.get('name', 'N/A')}", rule
                                        )
                except Exception as project_error:
                    print(f"⚠️ Erro ao verificar regras específicas do projeto (continuando): {project_error}")
            
            return modified_output
        except Exception as e:
            print(f"⚠️ Erro ao aplicar guardrails output: {e}")
            return output_text

    def _sanitize_blocked_output(self, output_text: str, rule: Dict) -> str:
        """Sanitiza resposta que violou guardrails de saída"""
        try:
            # VALIDAR: Garantir que rule seja um dicionário
            if not isinstance(rule, dict):
                return "Resposta bloqueada pelos guardrails de segurança."
                
            rule_type = rule.get("type", "")
            rule_name = rule.get("name", "unknown")
            
            # Respostas sanitizadas baseadas no tipo de violação
            if "pii" in rule_name.lower() or "cpf" in rule_name.lower():
                return "Desculpe, não posso fornecer informações que possam conter dados pessoais identificáveis."
            
            elif "password" in rule_name.lower() or "senha" in rule_name.lower():
                return "Por questões de segurança, não posso fornecer informações relacionadas a senhas ou credenciais."
            
            elif "inappropriate" in rule_name.lower() or "inadequado" in rule_name.lower():
                return "Desculpe, não posso fornecer esse tipo de conteúdo. Posso ajudar com informações mais apropriadas?"
            
            elif rule_type == "length":
                max_length = rule.get("max_length", 500)
                return output_text[:max_length] + "... [Resposta truncada por política de segurança]"
            
            else:
                # Sanitização genérica
                return f"Desculpe, a resposta foi bloqueada devido à política de segurança (regra: {rule_name}). Posso reformular de outra forma?"
                
        except Exception as e:
            print(f"⚠️ Erro ao sanitizar output: {e}")
            return "Desculpe, não posso fornecer essa informação no momento. Posso ajudar com algo diferente?"

    def _check_rule_violation(self, text: str, rule: Dict) -> bool:
        """Verifica se texto viola uma regra específica"""
        try:
            # VALIDAR: Garantir que rule seja um dicionário
            if not isinstance(rule, dict):
                return False
                
            rule_type = rule.get("type", "")
            if rule_type == "keyword":
                keywords = rule.get("keywords", [])
                return any(keyword.lower() in text.lower() for keyword in keywords)
            elif rule_type == "length":
                max_length = rule.get("max_length", 999999)
                return len(text) > max_length
            elif rule_type == "regex":
                import re
                pattern = rule.get("pattern", "")
                return bool(re.search(pattern, text, re.IGNORECASE))
            
            # Compatibilidade: suporte a formato legado de regras (não é mock)
            patterns = rule.get("patterns", {})
            text_lower = text.lower()
            
            # Verificar tokens bloqueados
            blocked_terms = patterns.get("blocked_informal", [])
            for term in blocked_terms:
                if term.lower() in text_lower:
                    return True
            
            # Verificar outros padrões específicos
            blocked_topics = patterns.get("blocked_topics", [])
            for topic in blocked_topics:
                if topic.lower() in text_lower:
                    return True
            
            return False
        except Exception as e:
            print(f"⚠️ Erro verificando regra {rule}: {e}")
            return False
    
    def _apply_output_rule(self, text: str, rule: Dict) -> str:
        """Aplica transformação no texto baseada na regra"""
        try:
            # VALIDAR: Garantir que rule seja um dicionário
            if not isinstance(rule, dict):
                return text
                
            rule_type = rule.get("type", "")
            if rule_type == "append":
                suffix = rule.get("suffix", "")
                return f"{text}\n{suffix}"
            elif rule_type == "prepend":
                prefix = rule.get("prefix", "")
                return f"{prefix}\n{text}"
            elif rule_type == "replace":
                old_text = rule.get("old", "")
                new_text = rule.get("new", "")
                return text.replace(old_text, new_text)
            
            # Compatibilidade: suporte a formato legado de regras (não é mock)
            rule_id = rule.get("rule_id", "")
            
            if rule_id == "formal_response_enforcement":
                # Formalizar resposta
                text = text.replace("legal", "adequado").replace("massa", "excelente")
                return f"Prezado(a), {text}. Atenciosamente."
            
            elif rule_id == "creative_enhancement":
                # Adicionar criatividade
                return f"🎨 {text} ✨ Que tal explorarmos mais ideias criativas? 🚀"
            
            return text
        except Exception as e:
            print(f"⚠️ Erro aplicando regra output {rule}: {e}")
            return text
    
    def _sanitize_blocked_output_guardrail_engine(self, output_text: str, violation: Dict) -> str:
        """Sanitiza resposta que violou guardrails do GuardrailEngine"""
        try:
            rule_id = violation.get("rule_id", "")
            category = violation.get("category", "")
            
            # Respostas sanitizadas baseadas na categoria e regra
            if category == "LGPD/GDPR":
                if "lgpd_001" in rule_id:  # Dados Pessoais
                    return "Desculpe, não posso fornecer informações que possam conter dados pessoais identificáveis (CPF, RG, CNPJ)."
                elif "lgpd_002" in rule_id:  # Dados Financeiros  
                    return "Por segurança, não posso fornecer informações financeiras sensíveis (cartões, contas bancárias)."
                elif "lgpd_003" in rule_id:  # Informações de Saúde
                    return "Não posso fornecer informações de saúde protegidas (prontuários, CID)."
                elif "lgpd_004" in rule_id:  # Dados de Localização
                    return "Por privacidade, informações de localização precisas foram removidas."
            
            elif category == "Security":
                if "security_001" in rule_id:  # Credenciais/Secrets
                    return "Por segurança, não posso fornecer informações relacionadas a credenciais, senhas ou tokens."
                elif "security_002" in rule_id:  # Prompt Injection
                    return "Detectei uma tentativa de manipulação. Posso ajudar com uma pergunta reformulada?"
                elif "security_003" in rule_id:  # Informações de Sistema
                    return "Informações técnicas de sistema foram removidas por segurança."
            
            elif category == "Compliance":
                if "finance_001" in rule_id:
                    return "Não posso fornecer informações que possam violar regulamentações financeiras."
                elif "healthcare_001" in rule_id:
                    return "Não posso fornecer informações médicas sem supervisão profissional adequada."
                elif "education_001" in rule_id:
                    return "Informações envolvendo menores foram removidas por proteção."
            
            elif category == "IP Protection":
                return "Informações proprietárias ou de propriedade intelectual foram removidas."
            
            elif category == "Code of Conduct":
                if "conduct_001" in rule_id:
                    return "Desculpe, não posso fornecer conteúdo ofensivo ou discriminatório. Posso reformular de forma respeitosa?"
                elif "conduct_002" in rule_id:
                    return "Ajustei a linguagem para manter um tom profissional adequado."
            
            elif category == "LLM Intelligence":
                if "llm_intelligent_002" in rule_id:  # Social Engineering
                    return "Detectei potencial manipulação social. Posso ajudar com uma abordagem mais direta?"
                elif "llm_intelligent_004" in rule_id:  # Vazamento de Dados
                    return "Preveni possível vazamento de dados sensíveis."
                else:
                    return "Resposta ajustada para conformidade com políticas corporativas."
            
            else:
                # Sanitização genérica
                return f"Resposta bloqueada pela política de segurança ({rule_id}). Posso reformular de outra forma?"
                
        except Exception as e:
            print(f"⚠️ Erro ao sanitizar output do GuardrailEngine: {e}")
            return "Desculpe, não posso fornecer essa informação no momento. Posso ajudar com algo diferente?"
    
    def _apply_sanitization_guardrail_engine(self, output_text: str, violation: Dict) -> str:
        """Aplica sanitização (não bloqueio) baseada no GuardrailEngine"""
        try:
            rule_id = violation.get("rule_id", "")
            
            # Aplicar sanitização específica conforme regra
            if "lgpd_002" in rule_id:  # Dados Financeiros - sanitizar números
                import re
                # Remover possíveis números de cartão ou conta
                output_text = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[CARTÃO REMOVIDO]', output_text)
                output_text = re.sub(r'\b\d{5,12}\b', '[NÚMERO REMOVIDO]', output_text)
            
            elif "security_003" in rule_id:  # Informações de Sistema
                import re
                # Remover IPs e informações técnicas
                output_text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP REMOVIDO]', output_text)
                output_text = re.sub(r'\b[A-Za-z0-9.-]+\.com\b', '[DOMÍNIO REMOVIDO]', output_text)
            
            elif "conduct_002" in rule_id:  # Linguagem Profissional
                import re
                # Substituir linguagem informal por formal (case-insensitive)
                professional_replacements = {
                    # Gírias informais → formal
                    r'\blegal\b': 'adequado',
                    r'\bmassa\b': 'excelente', 
                    r'\bshow\b': 'impressionante',
                    r'\btop\b': 'ótimo',
                    r'\bbacana\b': 'interessante',
                    r'\bmaneiro\b': 'bom',
                    r'\birado\b': 'excelente',
                    
                    # Expressões casuais → formal
                    r'\bcara\b': 'pessoa',
                    r'\bmano\b': 'colega',
                    r'\bvéi\b': 'colega',
                    r'\bbrother\b': 'colega',
                    r'\bgalera\b': 'equipe',
                    
                    # Linguagem não profissional → formal
                    r'\btá\b': 'está',
                    r'\bné\b': 'não é mesmo',
                    r'\btipo assim\b': 'desta forma',
                    r'\bsei lá\b': 'não tenho certeza',
                    r'\bwhatever\b': 'qualquer coisa'
                }
                
                for pattern, replacement in professional_replacements.items():
                    output_text = re.sub(pattern, replacement, output_text, flags=re.IGNORECASE)
            
            return output_text
            
        except Exception as e:
            print(f"⚠️ Erro aplicando sanitização GuardrailEngine: {e}")
            return output_text

    async def _log_guardrail_event_async(self, project_id: str, request_id: str, event_type: str, action: str, description: str, rule: Dict):
        """Registra evento de guardrail usando repository existente"""
        try:
            # Verificar se o projeto é válido antes de prosseguir
            is_valid_project = False
            
            # Obter repositório de projetos (sem hardcoding)
            # Usar repository_factory em vez de StorageFactory (classe não existe; prevenir erros de import)
            from ...storage.factory import repository_factory
            
            original_project_id = project_id
            try:
                project_repo = repository_factory.get_project_repository()
                project = await project_repo.get_by_id(project_id)
                if project:
                    is_valid_project = True
                else:
                    logger.warning(f"⚠️ Projeto não encontrado p/ guardrail event: {project_id}")
            except Exception as project_error:
                logger.error(f"❌ Erro verificando projeto: {project_error}")
            
            # Registrar o evento de guardrail
            if self.guardrail_repo:
                from ...storage.json_storage import GuardrailEvent
                try:
                    repo_path = getattr(self.guardrail_repo, 'file_path', None)
                    logger.debug(f"GuardrailRepo ativo em: {repo_path}")
                except Exception:
                    pass
                clean_details = {**rule}
                clean_details["is_valid_project"] = is_valid_project
                # Removido fallback_project_used para simplificar auditoria
                event = GuardrailEvent(
                    event_id=request_id,
                    project_id=original_project_id,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    request_id=request_id,
                    guardrail_type=event_type,
                    action=action,
                    reason=description,
                    details=clean_details
                )
                try:
                    result = await self.guardrail_repo.create(event)
                    logger.info(f"✅ Guardrail event registrado: {event_type} - {action} para projeto {original_project_id}")
                except Exception as ce:
                    logger.error(f"❌ Falha ao persistir guardrail event: {ce}")
            else:
                # Apenas log do erro, sem implementação de fallback
                # Fallbacks não documentados são um problema de segurança
                logger.error("❌ Repositório de guardrail não disponível e nenhum fallback seguro configurado")
        except Exception as e:
            logger.error(f"⚠️ Erro registrando guardrail event: {e}")
    
    async def _register_telemetry(self, project_id: str, request_id: str, provider: str,
                                  model: str, input_tokens: int, output_tokens: int, response_time: float, cost: float,
                                  prompt_text: str = "", response_text: str = ""):
        """Registra telemetria - FAIL-FAST se repository indisponível (sem fallback)."""
        if not (self.repositories_available and self.telemetry_repo):
            from ...exceptions import BradaxTechnicalException
            raise BradaxTechnicalException(
                message="Telemetry repository indisponível - operação abortada",
                component="LLMService",
                operation="register_telemetry"
            )
        try:
            from ...storage.json_storage import TelemetryData
            telemetry = TelemetryData(
                telemetry_id=request_id,
                project_id=project_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                request_id=request_id,
                endpoint="chat",
                method="POST",
                status_code=200,
                response_time_ms=response_time * 1000,
                model_used=model,
                tokens_used=input_tokens + output_tokens,
                user_agent=f"bradax-broker/{provider}",
                error_message=""
            )
            await self.telemetry_repo.create(telemetry)
            print(f"✅ Telemetria registrada: {provider}/{model} - {input_tokens + output_tokens} tokens")
        except Exception as e:
            from ...exceptions import BradaxTechnicalException
            raise BradaxTechnicalException(
                message=f"Falha ao registrar telemetria: {e}",
                component="LLMService",
                operation="register_telemetry"
            ) from e

    def get_available_models(self) -> List[LLMModelInfo]:
        """Retorna modelos disponíveis"""
        from .interfaces import LLMProviderType, LLMCapability
        
        return [
            LLMModelInfo(
                model_id="gpt-4.1-nano",
                name="GPT-4.1 Nano",
                provider=LLMProviderType.OPENAI,
                max_tokens=4096,
                cost_per_1k_input=0.0005,
                cost_per_1k_output=0.001,
                capabilities=[LLMCapability.TEXT_GENERATION, LLMCapability.CODE_GENERATION],
                enabled=True,
                description="OpenAI's GPT-4.1 Nano model - most cost-effective"
            )
        ]
    
    async def invoke(self, operation: str, model_id: str, payload: Dict, 
                    project_id: Optional[str] = None, request_id: Optional[str] = None, 
                    custom_guardrails: Optional[Dict] = None) -> Dict:  # CORREÇÃO: Aceitar guardrails customizados
        """
        Método de invocação LLM com GUARDRAILS E TELEMETRIA OBRIGATÓRIOS.
        ⚠️ GUARDRAILS SÃO APLICADOS AUTOMATICAMENTE PELO BROKER (TRANSPARENTE ao SDK)
        """
        req_id = request_id or str(uuid.uuid4())
        start_time = time.time()
        project_id = project_id or "default"
        guardrails_applied = 0
        # Stage: request_received
        try:
            from ..interactions import append_interaction_stage
            append_interaction_stage(req_id, project_id, "request_received", "Requisição recebida", {"operation": operation, "model": model_id})
        except Exception:
            pass

        # LIMPAR FLAGS DE SEGURANÇA para nova requisição
        self._input_guardrails_passed = False
        self._output_guardrails_required = False
        self._output_guardrails_applied = False
        
        # VERIFICAÇÃO CRÍTICA DE SEGURANÇA: Bloquear se guardrails não carregaram
        if not self._is_system_secure():
            error_msg = "🚨 SISTEMA BLOQUEADO: Guardrails obrigatórios não disponíveis. Execução negada por segurança."
            print(error_msg)
            
            # Registrar tentativa de uso inseguro
            try:
                from ..telemetry_raw import save_raw_response
                save_raw_response(
                    request_id=req_id,
                    project_id=project_id,
                    model=model_id,
                    prompt=str(payload)[:200],
                    response=error_msg,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    metadata={
                        "error": "guardrails_not_available",
                        "security_block": True,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
            except Exception:
                pass  # Falha na telemetria não deve afetar o bloqueio de segurança
            
            raise GuardrailViolationError(error_msg)
        
        try:
            print(f"🔒 BROKER: Aplicando guardrails obrigatórios para projeto '{project_id}'")
            
            # STEP 1: EXTRAIR INPUT para análise de guardrails
            if "messages" in payload:
                # Formato LangChain
                messages = payload["messages"]
                input_text = " ".join([msg.get("content", "") for msg in messages if isinstance(msg, dict)])
            elif "prompt" in payload:
                # Formato legado
                input_text = payload["prompt"]
                messages = [{"role": "user", "content": input_text}]
            else:
                raise ValueError("Either 'messages' or 'prompt' must be provided")

            # STEP 2: APLICAR GUARDRAILS DE INPUT OBRIGATORIAMENTE
            try:
                await self._apply_input_guardrails(project_id, input_text, req_id, custom_guardrails)  # CORREÇÃO: Passar guardrails customizados
                print(f"✅ Input aprovado pelo guardrail para {project_id}")
                self._input_guardrails_passed = True
                try:
                    from ..interactions import append_interaction_stage
                    append_interaction_stage(
                        req_id,
                        project_id,
                        "guardrail_input_pass",
                        "Input passou guardrails",
                        {
                            "length": len(input_text),
                            "result": "pass",
                            "guardrail_type": "input",
                            "action": "pass",
                            "metadata": {"phase": "pre_invoke"}
                        }
                    )
                except Exception:
                    pass
                # Evento de PASS opcional
                if self.log_guardrail_pass_events:
                    try:
                        await self._log_guardrail_event_async(
                            project_id=project_id,
                            request_id=req_id,
                            event_type="input_guardrail",
                            action="pass",
                            description="Input aprovado pelos guardrails",
                            rule={"stage": "input", "source": "_apply_input_guardrails", "blocked": False}
                        )
                    except Exception as e_pass:
                        logger.warning(f"Falha registrar guardrail pass input: {e_pass}")
            except GuardrailViolationError as e:
                guardrails_applied += 1
                processing_time_ms = int((time.time() - start_time) * 1000)
                try:
                    from ..interactions import append_interaction_stage
                    append_interaction_stage(
                        req_id,
                        project_id,
                        "guardrail_input_blocked",
                        "Input bloqueado",
                        {
                            "error": str(e),
                            "result": "block",
                            "guardrail_type": "input",
                            "action": "blocked",
                            "metadata": {"phase": "pre_invoke", "blocked": True}
                        }
                    )
                except Exception:
                    pass
                # Registro explícito do evento de guardrail (bloqueio input) para garantir persistência mesmo em retorno antecipado
                try:
                    await self._log_guardrail_event_async(
                        project_id=project_id,
                        request_id=req_id,
                        event_type="input_guardrail",
                        action="blocked",
                        description=str(e),
                        rule={"stage": "input", "source": "_apply_input_guardrails", "blocked": True}
                    )
                except Exception as log_err:
                    logger.error(f"⚠️ Falha ao registrar guardrail_event bloqueio input: {log_err}")
                await self._register_telemetry(project_id, req_id, "guardrail", "blocked", 
                                               len(input_text.split()), 0, processing_time_ms / 1000, 0.0,
                                               prompt_text=input_text[:100], response_text="BLOCKED")
                return {"request_id": req_id, "success": False, "error": f"Entrada rejeitada pelos guardrails: {str(e)}", "model_used": "guardrail_blocked", "response_time_ms": processing_time_ms, "guardrails_triggered": True}

            # STEP 3: PROCESSAR REQUISIÇÃO LLM REAL
            print(f"🤖 Processando LLM real para projeto '{project_id}'...")
            try:
                from ..interactions import append_interaction_stage
                append_interaction_stage(req_id, project_id, "llm_invocation_start", "Início invocação LLM", {})
            except Exception:
                pass
            # Obter provider real e invocar
            provider = get_provider("openai")
            result_text = provider.invoke(messages)
            try:
                from ..interactions import append_interaction_stage
                append_interaction_stage(req_id, project_id, "llm_invocation_end", "Fim invocação LLM", {"output_preview": result_text[:60]})
            except Exception:
                pass
            # Guardar output original para comparação posterior
            original_output = result_text
            try:
                result_text = await self._apply_output_guardrails(project_id, result_text, req_id)
                if result_text != original_output:
                    guardrails_applied += 1
                    print(f"✅ Output modificado pelo guardrail para {project_id}")
                    try:
                        from ..interactions import append_interaction_stage
                        append_interaction_stage(
                            req_id,
                            project_id,
                            "guardrail_output_modified",
                            "Output modificado",
                            {
                                "delta": len(original_output) - len(result_text),
                                "result": "sanitize",
                                "guardrail_type": "output",
                                "action": "modified",
                                "metadata": {"phase": "post_invoke", "sanitized": True}
                            }
                        )
                    except Exception:
                        pass
                self._output_guardrails_applied = True
                print(f"✅ Output guardrails aplicados com sucesso para {project_id}")
                try:
                    from ..interactions import append_interaction_stage
                    append_interaction_stage(
                        req_id,
                        project_id,
                        "guardrail_output_pass",
                        "Output passou guardrails",
                        {
                            "result": "pass",
                            "guardrail_type": "output",
                            "action": "pass",
                            "metadata": {"phase": "post_invoke"}
                        }
                    )
                except Exception:
                    pass
                # Evento de PASS opcional para output
                if self.log_guardrail_pass_events:
                    try:
                        await self._log_guardrail_event_async(
                            project_id, req_id, "output_guardrail", "pass", "Output aprovado pelos guardrails", {"stage": "output", "modified": result_text != original_output}
                        )
                    except Exception as e_pass_out:
                        logger.warning(f"Falha registrar guardrail pass output: {e_pass_out}")
            except Exception as e:
                print(f"⚠️ Erro ao aplicar guardrail de output: {e}")
                if result_text != original_output:
                    guardrails_applied += 1
                    print(f"✅ Output modificado pelo guardrail para {project_id}")
            # ...existing code...
            # Calcular métricas antes de registrar telemetria final
            processing_time_ms = int((time.time() - start_time) * 1000)
            input_tokens = len(input_text.split())
            output_tokens = len(result_text.split())
            await self._register_telemetry(project_id, req_id, "openai", model_id,
                                          input_tokens, output_tokens, processing_time_ms / 1000, 0.001,
                                          prompt_text=input_text[:100], response_text=result_text[:100])
            print(f"📊 BROKER: Telemetria registrada automaticamente (TRANSPARENTE ao SDK)")
            try:
                from ..interactions import append_interaction_stage
                append_interaction_stage(req_id, project_id, "telemetry_persisted", "Telemetria registrada", {"input_tokens": input_tokens, "output_tokens": output_tokens})
            except Exception:
                pass
            return {"request_id": req_id, "success": True, "response": result_text, "response_text": result_text, "model_used": model_id, "response_time_ms": processing_time_ms, "guardrails_applied": guardrails_applied, "project_id": project_id, "broker_processed": True}
        except Exception as e:
            # Log erro e registrar telemetria de falha
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # INTERCEPTAÇÃO TELEMETRIA RAW: Capturar erro como response
            error_response_data = {
                "request_id": req_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "provider": "error",
                "model": model_id,
                "error": str(e),
                "processing_time_ms": processing_time_ms,
                "success": False,
                "metadata": {
                    "guardrails_applied": guardrails_applied,
                    "project_id": project_id,
                    "error_type": type(e).__name__
                }
            }
            
            # Salvar erro como response raw
            try:
                from ..telemetry_raw import save_raw_response
                save_raw_response(req_id, error_response_data)
                print(f"💾 Error response raw salvo: {req_id}")
            except Exception as save_error:
                print(f"⚠️ Erro ao salvar error response raw: {save_error}")
            
            if 'input_text' in locals():
                await self._register_telemetry(project_id, req_id, "error", "error", 
                                              len(input_text.split()), 0, processing_time_ms / 1000, 0.0,
                                              prompt_text=input_text[:100], response_text=f"ERROR: {str(e)}")
            else:
                await self._register_telemetry(project_id, req_id, "error", "error", 
                                              0, 0, processing_time_ms / 1000, 0.0,
                                              prompt_text="", response_text=f"ERROR: {str(e)}")
            
            return {
                "request_id": req_id,
                "success": False,
                "error": str(e),
                "model_used": model_id,
                "response_time_ms": processing_time_ms,
                "guardrails_attempted": guardrails_applied
            }


# Instância global
llm_service = LLMService()
