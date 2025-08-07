"""
Sistema de Guardrails Centralizados - Bradax Hub

Implementa proteções de conteúdo que NÃO podem ser desabilitadas pelo SDK.
Controle total do hub sobre o que é permitido ou bloqueado.
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

from ..constants import HubStorageConstants, get_hub_environment
from ..exceptions import ValidationException, ConfigurationException, BusinessException
from .telemetry import get_telemetry_collector

logger = logging.getLogger(__name__)

# Import LLM Service para validação inteligente
try:
    from .llm.service import LLMService
    LLM_VALIDATION_AVAILABLE = True
except ImportError:
    LLM_VALIDATION_AVAILABLE = False
    logger.warning("LLM Service não disponível - usando apenas validação por regex/keywords")


class GuardrailSeverity(Enum):
    """Níveis de severidade dos guardrails"""
    INFO = "info"          # Log apenas, não bloqueia
    WARNING = "warning"    # Log + warning, não bloqueia  
    BLOCK = "block"        # Bloqueia requisição
    CRITICAL = "critical"  # Bloqueia + alerta administrador


class GuardrailAction(Enum):
    """Ações possíveis dos guardrails"""
    ALLOW = "allow"           # Permite passar
    BLOCK = "block"           # Bloqueia completamente
    SANITIZE = "sanitize"     # Remove/substitui conteúdo problemático
    FLAG = "flag"             # Marca para revisão posterior


@dataclass
class GuardrailRule:
    """Regra de guardrail configurável"""
    rule_id: str
    name: str
    description: str
    enabled: bool
    severity: GuardrailSeverity
    action: GuardrailAction
    pattern: Optional[str]  # Regex pattern
    keywords: List[str]     # Lista de palavras-chave
    whitelist: List[str]    # Exceções permitidas
    category: str           # Categoria da regra
    metadata: Dict[str, Any]


@dataclass
class GuardrailResult:
    """Resultado da verificação de guardrails"""
    allowed: bool
    triggered_rules: List[str]
    blocked_content: List[str]
    sanitized_content: Optional[str]
    severity: GuardrailSeverity
    reason: str
    action: str  # CORREÇÃO CRÍTICA: Adicionar campo action que estava faltando
    metadata: Dict[str, Any]
    
    @property
    def is_safe(self) -> bool:
        """Compatibilidade: is_safe é o inverso de allowed (quando não permitido = não seguro)"""
        return self.allowed


class GuardrailEngine:
    """
    Motor de guardrails centralizado
    
    CARACTERÍSTICAS:
    - Não pode ser desabilitado pelo SDK
    - Regras configuráveis apenas pelo admin do hub
    - Telemetria automática de todas as verificações
    - Suporte a múltiplos tipos de conteúdo
    - Cache de regras para performance
    """
    
    def __init__(self):
        self.environment = get_hub_environment()
        
        # Usar caminho absoluto FORÇADO para evitar problemas de pasta
        from pathlib import Path
        current_dir = Path(__file__).resolve()
        project_root = None
        
        # Subir diretórios até encontrar a pasta bradax
        for parent in current_dir.parents:
            if parent.name == "bradax":
                project_root = parent
                break
        
        if not project_root:
            raise RuntimeError("Pasta raiz 'bradax' não encontrada - estrutura de projeto incorreta")
        
        from ..utils.paths import get_data_dir
        self.storage_path = get_data_dir()
        self.guardrails_file = self.storage_path / "guardrails.json"
        self.telemetry = get_telemetry_collector()
        
        # Inicializar LLM Service para validação inteligente
        self.llm_service = None
        if LLM_VALIDATION_AVAILABLE:
            try:
                self.llm_service = LLMService()
                logger.info("LLM Service integrado para validação inteligente de guardrails")
            except Exception as e:
                logger.warning(f"Falha ao inicializar LLM Service: {e}")
        
        # Cache de regras
        self._rules_cache: Dict[str, GuardrailRule] = {}
        self._cache_loaded = False
        
        # Verificar se diretório existe
        if not self.storage_path.exists():
            raise RuntimeError(f"Diretório de dados não encontrado: {self.storage_path}")
        
        # SEMPRE carregar do arquivo JSON (fonte única de verdade)
        if not self.guardrails_file.exists():
            raise RuntimeError(f"Arquivo de guardrails obrigatório não encontrado: {self.guardrails_file}")
        
        self._create_default_rules()  # Na verdade carrega do JSON
        logger.info(f"GuardrailEngine iniciado - ambiente: {self.environment.value}")
    
    def _create_default_rules(self) -> None:
        """
        Carrega regras de guardrails do arquivo JSON (fonte única de verdade).
        
        IMPORTANTE: Regras padrão agora são definidas em data/guardrails.json
        para permitir configuração dinâmica sem redeploy.
        """
        try:
            # Usar caminho absoluto FORÇADO para raiz do projeto
            import os
            from pathlib import Path
            
            # Encontrar raiz do projeto (pasta bradax)
            current_dir = Path(__file__).resolve()
            project_root = None
            
            # Subir diretórios até encontrar a pasta bradax
            for parent in current_dir.parents:
                if parent.name == "bradax":
                    project_root = parent
                    break
            
            if not project_root:
                raise FileNotFoundError("Pasta raiz 'bradax' não encontrada")
            
            from ..utils.paths import get_data_dir
            guardrails_file = get_data_dir() / "guardrails.json"
            
            print(f"🔍 Tentando carregar: {guardrails_file}")
            
            if not guardrails_file.exists():
                raise FileNotFoundError(f"Arquivo não encontrado: {guardrails_file}")
            
            with open(guardrails_file, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            print(f"📄 Arquivo lido com {len(rules_data)} regras")
            
            # Converter regras do JSON para objetos GuardrailRule
            for rule_data in rules_data:
                if not rule_data.get("enabled", True):
                    print(f"   ⏭️ Pulando regra desabilitada: {rule_data.get('rule_id', 'unknown')}")
                    continue
                
                # Mapear severidade do JSON para enum
                severity_map = {
                    "LOW": GuardrailSeverity.WARNING,
                    "MEDIUM": GuardrailSeverity.WARNING, 
                    "HIGH": GuardrailSeverity.BLOCK,
                    "CRITICAL": GuardrailSeverity.CRITICAL
                }
                severity = severity_map.get(rule_data.get("severity")) # Coleta a severidade cadastrada na regra
                
                # Mapear ação do JSON para enum
                action_map = {
                    "flag": GuardrailAction.FLAG,
                    "sanitize": GuardrailAction.SANITIZE,
                    "block": GuardrailAction.BLOCK
                }
                action = action_map.get(rule_data.get("action", "flag"), GuardrailAction.FLAG)
                
                # Combinar todos os padrões regex em um único pattern
                patterns = rule_data.get("patterns", {})
                combined_pattern = None
                if patterns:
                    pattern_list = [f"({pattern})" for pattern in patterns.values() if pattern]
                    if pattern_list:
                        combined_pattern = "|".join(pattern_list)
                
                # Extrair keywords dos padrões e campos específicos
                keywords = []
                if "keywords" in rule_data:
                    keywords.extend(rule_data["keywords"])
                keywords.extend(patterns.keys())  # Adicionar nomes dos padrões como keywords
                
                # Criar regra
                rule = GuardrailRule(
                    rule_id=rule_data["rule_id"],
                    name=rule_data["name"],
                    description=rule_data.get("description", rule_data["name"]),
                    enabled=rule_data.get("enabled", True),
                    severity=severity,
                    action=action,
                    pattern=combined_pattern,
                    keywords=keywords,
                    whitelist=rule_data.get("whitelist", []),
                    category=rule_data.get("category", "general"),
                    metadata={"source": "json_file", "file_path": str(guardrails_file)}
                )
                
                self._rules_cache[rule.rule_id] = rule
                print(f"   ✅ Regra carregada: {rule.rule_id} - {rule.name}")
            
            print(f"✅ {len(self._rules_cache)} regras de guardrails carregadas de {guardrails_file}")
            self._cache_loaded = True
            
        except Exception as e:
            print(f"❌ ERRO CRÍTICO ao carregar regras de guardrails: {e}")
            print(f"   Tipo: {type(e).__name__}")
            print(f"   Sistema BLOQUEADO - nenhuma regra disponível")
            raise RuntimeError(f"Sistema de guardrails falhou: {e}")

    
    def _load_rules(self) -> None:
        """Carrega regras do arquivo de configuração"""
        # Se já carregamos via _create_default_rules, não duplicar
        if self._cache_loaded:
            print(f"📋 Regras já carregadas: {len(self._rules_cache)} regras")
            return
        
        try:
            print(f"🔍 Carregando regras de: {self.guardrails_file}")
            with open(self.guardrails_file, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            self._rules_cache.clear()
            
            # Usar mesma lógica de conversão que _create_default_rules
            for rule_data in rules_data:
                if not rule_data.get("enabled", True):
                    continue  # Pular regras desabilitadas
                
                # Mapear severidade do JSON para enum
                severity_map = {
                    "LOW": GuardrailSeverity.WARNING,
                    "MEDIUM": GuardrailSeverity.WARNING, 
                    "HIGH": GuardrailSeverity.BLOCK,
                    "CRITICAL": GuardrailSeverity.CRITICAL
                }
                severity = severity_map.get(rule_data.get("severity", "MEDIUM"), GuardrailSeverity.WARNING)
                
                # Mapear ação do JSON para enum
                action_map = {
                    "flag": GuardrailAction.FLAG,
                    "sanitize": GuardrailAction.SANITIZE,
                    "block": GuardrailAction.BLOCK
                }
                action = action_map.get(rule_data.get("action", "flag"), GuardrailAction.FLAG)
                
                # Combinar todos os padrões regex em um único pattern
                patterns = rule_data.get("patterns", {})
                combined_pattern = None
                if patterns:
                    pattern_list = [f"({pattern})" for pattern in patterns.values() if pattern]
                    if pattern_list:
                        combined_pattern = "|".join(pattern_list)
                
                # Extrair keywords dos padrões e campos específicos
                keywords = []
                if "keywords" in rule_data:
                    keywords.extend(rule_data["keywords"])
                keywords.extend(patterns.keys())  # Adicionar nomes dos padrões como keywords
                
                # Criar regra
                rule = GuardrailRule(
                    rule_id=rule_data["rule_id"],
                    name=rule_data["name"],
                    description=rule_data.get("description", rule_data["name"]),
                    enabled=rule_data.get("enabled", True),
                    severity=severity,
                    action=action,
                    pattern=combined_pattern,
                    keywords=keywords,
                    whitelist=rule_data.get("whitelist", []),
                    category=rule_data.get("category", "general"),
                    metadata={"source": "json_file", "file_path": str(self.guardrails_file)}
                )
                
                self._rules_cache[rule.rule_id] = rule
            
            self._cache_loaded = True
            print(f"✅ Guardrails carregados via _load_rules: {len(self._rules_cache)} regras")
            
        except Exception as e:
            logger.error(f"Erro ao carregar guardrails: {e}")
            raise ConfigurationException(
                "Falha ao carregar configuração de guardrails",
                details={"file": str(self.guardrails_file), "error": str(e)}
            )
    
    async def _llm_content_analysis(self, content: str, rule: GuardrailRule) -> Dict[str, Any]:
        """
        Análise de conteúdo usando LLM para validação inteligente
        
        Args:
            content: Conteúdo a ser analisado
            rule: Regra de guardrail para validação
            
        Returns:
            Dict com resultado da análise LLM
        """
        if not self.llm_service:
            return {"available": False, "violation": False}
        
        try:
            # Prompt especializado para análise de guardrails
            analysis_prompt = f"""
Você é um sistema de análise de conteúdo para guardrails de segurança.

REGRA SENDO VALIDADA:
- Nome: {rule.name}
- Descrição: {rule.description}
- Categoria: {rule.category}
- Keywords relevantes: {', '.join(rule.keywords) if rule.keywords else 'Nenhuma'}

CONTEÚDO PARA ANÁLISE:
{content}

TAREFA:
Analise se o conteúdo viola a regra especificada. Considere:
1. O contexto e intenção do conteúdo
2. Se palavras-chave estão sendo usadas de forma problemática
3. Nuances que regex não detectaria
4. Falsos positivos (uso legítimo de termos sensíveis)

RESPOSTA (JSON):
{{
    "violacao_detectada": true/false,
    "confianca": 0.0-1.0,
    "explicacao": "breve explicação da análise",
    "contexto_problematico": true/false,
    "recomendacao": "allow/flag/sanitize/block"
}}
"""
            
            # Executar análise via LLM
            response = await self.llm_service.invoke(
                operation="chat",
                model_id="gpt-4o-mini",
                payload={
                    "messages": [{"role": "user", "content": analysis_prompt}],
                    "max_tokens": 300,
                    "temperature": 0.1
                },
                project_id="system_guardrails"
            )
            
            # Tentar extrair JSON da resposta
            response_content = response.get("response", {})
            response_text = response_content.get("content", "") if isinstance(response_content, dict) else str(response_content)
            try:
                import json
                # Tentar encontrar JSON na resposta
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    analysis_result = json.loads(json_str)
                    analysis_result["available"] = True
                    return analysis_result
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Resposta LLM não contém JSON válido: {response_text}")
                return {"available": False, "violation": False, "error": "Resposta LLM inválida"}
            
        except Exception as e:
            logger.warning(f"Erro na análise LLM para regra {rule.rule_id}: {e}")
            return {"available": False, "violation": False, "error": str(e)}
    
    def check_content(
        self,
        content: str,
        project_id: str,
        content_type: str = "prompt",
        endpoint: str = "/llm/generate"
    ) -> GuardrailResult:
        """
        Verifica conteúdo contra todas as regras de guardrails
        
        Args:
            content: Conteúdo a ser verificado
            project_id: ID do projeto fazendo a requisição
            content_type: Tipo de conteúdo (prompt, response, etc.)
            endpoint: Endpoint que está sendo usado
            
        Returns:
            GuardrailResult: Resultado da verificação
        """
        if not self._cache_loaded:
            self._load_rules()
        
        triggered_rules = []
        blocked_content_pieces = []
        sanitized_content = content
        highest_severity = GuardrailSeverity.INFO
        blocking_action = False
        
        # Verificar cada regra ativa
        for rule in self._rules_cache.values():
            if not rule.enabled:
                continue
            
            violation_found = False
            violation_details = []
            
            # Verificar keywords
            if rule.keywords:
                content_lower = content.lower()
                for keyword in rule.keywords:
                    if keyword.lower() in content_lower:
                        # Verificar se não está na whitelist
                        whitelisted = False
                        for whitelist_item in rule.whitelist:
                            if whitelist_item.lower() in content_lower:
                                whitelisted = True
                                break
                        
                        if not whitelisted:
                            violation_found = True
                            violation_details.append(f"Keyword detectada: {keyword}")
            
            # Verificar padrão regex
            if rule.pattern:
                try:
                    matches = re.findall(rule.pattern, content, re.IGNORECASE)
                    if matches:
                        violation_found = True
                        violation_details.append(f"Padrão detectado: {len(matches)} ocorrências")
                except Exception as e:
                    logger.warning(f"Erro no padrão regex da regra {rule.rule_id}: {e}")
            
            # VALIDAÇÃO LLM INTELIGENTE (para regras de conteúdo)
            if rule.category in ["content_safety", "business", "compliance"] and self.llm_service:
                try:
                    # Evitar asyncio.run() dentro de event loop ativo
                    import asyncio
                    
                    # Verificar se já estamos em um event loop
                    try:
                        current_loop = asyncio.get_running_loop()
                        # Já estamos em um loop, criar task
                        llm_analysis = {"available": False, "violation": False, "confidence": 0.0}
                        logger.debug("Event loop ativo detectado, pulando validação LLM para evitar conflito")
                    except RuntimeError:
                        # Não há loop ativo, pode usar asyncio.run()
                        llm_analysis = asyncio.run(self._llm_content_analysis(content, rule))
                    
                    if llm_analysis.get("available", False):
                        llm_violation = llm_analysis.get("violation", False)
                        llm_confidence = llm_analysis.get("confidence", 0.0)
                        
                        # Se LLM detectou violação com alta confiança
                        if llm_violation and llm_confidence > 0.7:
                            violation_found = True
                            violation_details.append(f"LLM detectou violação (confiança: {llm_confidence:.2f})")
                            
                        # Se LLM indica falso positivo em regras básicas
                        elif violation_found and not llm_violation and llm_confidence > 0.8:
                            logger.info(f"LLM override: falso positivo detectado para regra {rule.rule_id}")
                            violation_found = False
                            violation_details = [f"LLM override: falso positivo (confiança: {llm_confidence:.2f})"]
                            
                        # Adicionar contexto LLM à telemetria
                        violation_details.append(f"Análise LLM: {llm_analysis.get('explanation', 'N/A')}")
                        
                except Exception as e:
                    logger.warning(f"Erro na validação LLM para regra {rule.rule_id}: {e}")
            
            # Se violação encontrada, processar ação
            if violation_found:
                triggered_rules.append(rule.rule_id)
                
                # Registrar telemetria
                self.telemetry.record_guardrail_trigger(
                    project_id=project_id,
                    guardrail_name=rule.name,
                    blocked_content=content,  # Conteúdo original bloqueado
                    endpoint=endpoint,
                    metadata={
                        "rule_id": rule.rule_id,
                        "content_type": content_type,
                        "violation_details": violation_details,
                        "severity": rule.severity.value,
                        "action": rule.action.value
                    }
                )
                
                # Determinar severidade máxima
                if rule.severity.value == "critical":
                    highest_severity = GuardrailSeverity.CRITICAL
                elif rule.severity.value == "block" and highest_severity.value != "critical":
                    highest_severity = GuardrailSeverity.BLOCK
                elif rule.severity.value == "warning" and highest_severity.value in ["info"]:
                    highest_severity = GuardrailSeverity.WARNING
                
                # Executar ação da regra
                if rule.action == GuardrailAction.BLOCK:
                    blocking_action = True
                    blocked_content_pieces.extend(violation_details)
                
                elif rule.action == GuardrailAction.SANITIZE:
                    # Implementar sanitização (simplificada)
                    if rule.keywords:
                        for keyword in rule.keywords:
                            sanitized_content = re.sub(
                                re.escape(keyword),
                                "[REDACTED]",
                                sanitized_content,
                                flags=re.IGNORECASE
                            )
                    
                    if rule.pattern:
                        sanitized_content = re.sub(
                            rule.pattern,
                            "[REDACTED]",
                            sanitized_content,
                            flags=re.IGNORECASE
                        )
                
                elif rule.action == GuardrailAction.FLAG:
                    # Apenas marcar para auditoria (não bloquear)
                    pass
        
        # Determinar resultado final
        allowed = not blocking_action
        reason = "Aprovado" if allowed else f"Bloqueado por {len([r for r in self._rules_cache.values() if r.rule_id in triggered_rules and r.action == GuardrailAction.BLOCK])} regra(s)"
        
        # Determinar ação predominante baseada nas regras acionadas
        if blocking_action:
            action = "BLOCK"
        elif sanitized_content != content:
            action = "SANITIZE"
        elif triggered_rules:
            action = "FLAG"
        else:
            action = "ALLOW"
        
        result = GuardrailResult(
            allowed=allowed,
            triggered_rules=triggered_rules,
            blocked_content=blocked_content_pieces,
            sanitized_content=sanitized_content if sanitized_content != content else None,
            severity=highest_severity,
            reason=reason,
            action=action,  # CORREÇÃO CRÍTICA: Incluir campo action no resultado
            metadata={
                "content_type": content_type,
                "endpoint": endpoint,
                "project_id": project_id,
                "total_rules_checked": len([r for r in self._rules_cache.values() if r.enabled]),
                "content_length": len(content)
            }
        )
        
        # Log resultado
        if not allowed:
            logger.warning(f"Guardrail BLOQUEOU: {project_id} -> {len(triggered_rules)} regras violadas")
        elif triggered_rules:
            logger.info(f"Guardrail flagged: {project_id} -> {len(triggered_rules)} regras marcadas")
        
        return result
    
    def get_active_rules(self) -> List[GuardrailRule]:
        """Retorna lista de regras ativas"""
        if not self._cache_loaded:
            self._load_rules()
        
        return [rule for rule in self._rules_cache.values() if rule.enabled]
    
    def get_rule(self, rule_id: str) -> Optional[GuardrailRule]:
        """Obtém regra específica por ID"""
        if not self._cache_loaded:
            self._load_rules()
        
        return self._rules_cache.get(rule_id)
    
    def add_rule(self, rule: GuardrailRule) -> None:
        """Adiciona nova regra (apenas admin)"""
        if rule.rule_id in self._rules_cache:
            raise ValidationException(
                f"Regra {rule.rule_id} já existe",
                details={"rule_id": rule.rule_id}
            )
        
        self._rules_cache[rule.rule_id] = rule
        self._save_rules()
        logger.info(f"Nova regra adicionada: {rule.rule_id} - {rule.name}")
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> GuardrailRule:
        """Atualiza regra existente (apenas admin)"""
        if rule_id not in self._rules_cache:
            raise ValidationException(
                f"Regra {rule_id} não encontrada",
                details={"rule_id": rule_id}
            )
        
        rule = self._rules_cache[rule_id]
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        self._save_rules()
        logger.info(f"Regra atualizada: {rule_id}")
        return rule
    
    def delete_rule(self, rule_id: str) -> bool:
        """Remove regra (apenas admin)"""
        if rule_id not in self._rules_cache:
            return False
        
        del self._rules_cache[rule_id]
        self._save_rules()
        logger.info(f"Regra removida: {rule_id}")
        return True
    
    def _save_rules(self) -> None:
        """Persiste regras no arquivo"""
        try:
            rules_data = []
            for rule in self._rules_cache.values():
                rule_dict = asdict(rule)
                # Converter enums para strings
                rule_dict['severity'] = rule.severity.value
                rule_dict['action'] = rule.action.value
                rules_data.append(rule_dict)
            
            with open(self.guardrails_file, 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, indent=2, ensure_ascii=False)
            
            logger.debug("Regras de guardrails salvas")
            
        except Exception as e:
            logger.error(f"Erro ao salvar guardrails: {e}")
            raise ConfigurationException(
                "Falha ao salvar configuração de guardrails",
                details={"error": str(e)}
            )
    
    def reload_rules(self) -> None:
        """Recarrega regras do arquivo (para mudanças em runtime)"""
        self._load_rules()
        logger.info("Regras de guardrails recarregadas")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas dos guardrails"""
        if not self._cache_loaded:
            self._load_rules()
        
        total_rules = len(self._rules_cache)
        active_rules = len([r for r in self._rules_cache.values() if r.enabled])
        
        categories = {}
        for rule in self._rules_cache.values():
            categories[rule.category] = categories.get(rule.category, 0) + 1
        
        return {
            "total_rules": total_rules,
            "active_rules": active_rules,
            "categories": categories,
            "environment": self.environment.value,
            "last_loaded": self._cache_loaded
        }


# Singleton global
guardrail_engine = GuardrailEngine()


def get_guardrail_engine() -> GuardrailEngine:
    """Factory function para obter motor de guardrails"""
    return guardrail_engine
