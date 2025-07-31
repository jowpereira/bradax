"""
LLM Service - Bradax Broker

Serviço principal para orquestração de LLMs usando LangChain.
INTERCEPTA TODAS as requisições e aplica guardrails/telemetria OBRIGATÓRIOS.
"""

import time
import uuid
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone

from .interfaces import LLMRequest, LLMResponse, LLMModelInfo
from .providers import get_provider, get_available_providers
from .registry import LLMRegistry


class GuardrailViolationError(Exception):
    """Exceção para violações de guardrails"""
    pass



class GuardrailViolationError(Exception):
    """Exceção para violações de guardrails"""
    pass


class LLMService:
    """Serviço principal de LLM com LangChain + GUARDRAILS OBRIGATÓRIOS"""
    
    def __init__(self):
        try:
            self.providers = get_available_providers()
            self.registry = LLMRegistry()
            
            # Inicializar repositories usando factory
            from ..storage.factory import create_storage_repositories
            repositories = create_storage_repositories()
            self.project_repo = repositories["project"]
            self.telemetry_repo = repositories["telemetry"] 
            self.guardrail_repo = repositories["guardrail"]
            
            print(f"✅ LLM Service inicializado com providers: {list(self.providers.keys())}")
            print(f"✅ LLM Registry integrado para governança de modelos")
            print(f"✅ Repositories integrados: project, telemetry, guardrail")
        except Exception as e:
            print(f"⚠️ Erro ao inicializar LLM Service: {e}")
            self.providers = {}
            self.registry = None
            self.project_repo = None
            self.telemetry_repo = None
            self.guardrail_repo = None

    async def _apply_input_guardrails(self, project_id: str, input_text: str, request_id: str) -> bool:
        """Aplica guardrails no INPUT OBRIGATORIAMENTE usando repositories existentes"""
        try:
            project = await self.project_repo.get_by_id(project_id)
            if not project:
                return True  # Se não tem projeto, permite
            
            guardrails = project.config.get("guardrails", {}) if hasattr(project, 'config') and project.config else {}
            input_rules = guardrails.get("input_validation", {}).get("rules", [])
            
            for rule in input_rules:
                if rule.get("action") == "reject":
                    if self._check_rule_violation(input_text, rule):
                        # Registrar evento usando repository existente
                        await self._log_guardrail_event_async(
                            project_id, request_id, "input_validation", "blocked", 
                            f"Regra violada: {rule.get('name', 'N/A')}", rule
                        )
                        raise GuardrailViolationError(f"Entrada rejeitada: {rule.get('name', 'Regra não especificada')}")
            
            return True
        except GuardrailViolationError:
            raise
        except Exception as e:
            print(f"⚠️ Erro ao aplicar guardrails input: {e}")
            return True
    
    async def _apply_output_guardrails(self, project_id: str, output_text: str, request_id: str) -> str:
        """Aplica guardrails no OUTPUT OBRIGATORIAMENTE usando repositories existentes"""
        try:
            project = await self.project_repo.get_by_id(project_id)
            if not project:
                return output_text  # Se não tem projeto, retorna original
            
            guardrails = project.config.get("guardrails", {}) if hasattr(project, 'config') and project.config else {}
            output_rules = guardrails.get("output_validation", {}).get("rules", [])
            
            modified_output = output_text
            for rule in output_rules:
                action = rule.get("action")
                if action in ["modify", "enhance"]:
                    modified_output = self._apply_output_rule(modified_output, rule)
                    # Registrar evento usando repository existente
                    await self._log_guardrail_event_async(
                        project_id, request_id, "output_validation", action, 
                        f"Regra aplicada: {rule.get('name', 'N/A')}", rule
                    )
            
            return modified_output
        except Exception as e:
            print(f"⚠️ Erro ao aplicar guardrails output: {e}")
            return output_text

    def _check_rule_violation(self, text: str, rule: Dict) -> bool:
        """Verifica se texto viola uma regra específica"""
        try:
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
            
            # Fallback para formato legado
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
            
            # Fallback para formato legado
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
    
    async def _log_guardrail_event_async(self, project_id: str, request_id: str, event_type: str, action: str, description: str, rule: Dict):
        """Registra evento de guardrail usando repository existente"""
        try:
            if self.guardrail_repo:
                from ...storage.json_storage import GuardrailEvent
                event = GuardrailEvent(
                    project_id=project_id,
                    request_id=request_id,
                    event_type=event_type,
                    action=action,
                    description=description,
                    rule_applied=rule
                )
                await self.guardrail_repo.create(event)
                print(f"✅ Guardrail event registrado: {event_type} - {action}")
        except Exception as e:
            print(f"⚠️ Erro registrando guardrail event: {e}")
    
    async def _log_telemetry_async(self, project_id: str, request_id: str, provider: str, model: str, 
                                 input_tokens: int, output_tokens: int, response_time: float, cost: float):
        """Registra telemetria usando repository existente"""
        try:
            if self.telemetry_repo:
                from ...storage.json_storage import TelemetryData
                telemetry = TelemetryData(
                    project_id=project_id,
                    request_id=request_id,
                    provider=provider,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    response_time_ms=response_time * 1000,  # converter para ms
                    cost_usd=cost
                )
                await self.telemetry_repo.create(telemetry)
                print(f"✅ Telemetria registrada: {provider}/{model} - {input_tokens + output_tokens} tokens")
        except Exception as e:
            print(f"⚠️ Erro registrando telemetria: {e}")

    def get_available_models(self) -> List[LLMModelInfo]:
        """Retorna modelos disponíveis"""
        from .interfaces import LLMProviderType, LLMCapability
        
        return [
            LLMModelInfo(
                model_id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                provider=LLMProviderType.OPENAI,
                max_tokens=4096,
                cost_per_1k_input=0.0015,
                cost_per_1k_output=0.002,
                capabilities=[LLMCapability.TEXT_GENERATION, LLMCapability.CODE_GENERATION],
                enabled=True,
                description="OpenAI's GPT-3.5 Turbo model"
            )
        ]
    
    async def invoke(self, operation: str, model_id: str, payload: Dict, 
                    project_id: Optional[str] = None, request_id: Optional[str] = None) -> Dict:
        """
        Método de invocação LLM com GUARDRAILS E TELEMETRIA OBRIGATÓRIOS.
        ⚠️ GUARDRAILS SÃO APLICADOS AUTOMATICAMENTE PELO BROKER (TRANSPARENTE ao SDK)
        """
        req_id = request_id or str(uuid.uuid4())
        start_time = time.time()
        project_id = project_id or "default"
        guardrails_applied = 0
        
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
                await self._apply_input_guardrails(project_id, input_text, req_id)
                print(f"✅ Input aprovado pelo guardrail para {project_id}")
            except GuardrailViolationError as e:
                guardrails_applied += 1
                processing_time_ms = int((time.time() - start_time) * 1000)
                await self._log_telemetry_async(project_id, req_id, "guardrail", "blocked", 
                                               len(input_text.split()), 0, processing_time_ms / 1000, 0.0)
                return {
                    "request_id": req_id,
                    "success": False,
                    "error": f"Entrada rejeitada pelos guardrails: {str(e)}",
                    "model_used": "guardrail_blocked",
                    "response_time_ms": processing_time_ms,
                    "guardrails_triggered": True
                }

            # STEP 3: PROCESSAR REQUISIÇÃO LLM REAL
            print(f"🤖 Processando LLM real para projeto '{project_id}'...")
            
            # Obter provider real
            provider = get_provider("openai")
            result_text = provider.invoke(messages)
            
            # STEP 4: APLICAR GUARDRAILS DE OUTPUT OBRIGATORIAMENTE
            original_output = result_text
            try:
                result_text = await self._apply_output_guardrails(project_id, result_text, req_id)
                if result_text != original_output:
                    guardrails_applied += 1
                    print(f"✅ Output modificado pelo guardrail para {project_id}")
            except Exception as e:
                print(f"⚠️ Erro ao aplicar guardrail de output: {e}")

            # STEP 5: REGISTRAR TELEMETRIA OBRIGATORIAMENTE
            processing_time_ms = int((time.time() - start_time) * 1000)
            input_tokens = len(input_text.split())
            output_tokens = len(result_text.split())
            await self._log_telemetry_async(project_id, req_id, "openai", model_id,
                                          input_tokens, output_tokens, processing_time_ms / 1000, 0.001)
            
            print(f"📊 BROKER: Telemetria registrada automaticamente (TRANSPARENTE ao SDK)")

            # STEP 6: RETORNAR RESPOSTA PROCESSADA
            return {
                "request_id": req_id,
                "success": True,
                "response_text": result_text,
                "model_used": model_id,
                "response_time_ms": processing_time_ms,
                "guardrails_applied": guardrails_applied,
                "project_id": project_id,
                "broker_processed": True  # Indica processamento obrigatório pelo broker
            }
            
        except Exception as e:
            # Log erro e registrar telemetria de falha
            processing_time_ms = int((time.time() - start_time) * 1000)
            if 'input_text' in locals():
                await self._log_telemetry_async(project_id, req_id, "error", "error", 
                                              len(input_text.split()), 0, processing_time_ms / 1000, 0.0)
            
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
