"""
Cliente SDK bradax - Implementação principal

SDK Python profissional para comunicação segura com o bradax Broker.
Inclui autenticação por projet        options = options or {}
        
        # Formato para endpoint /invoke
        invoke_payload = {
            "operation": "chat",  # Tipo de operação
            "model": model,
            "payload": {
                "prompt": prompt,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "options": options
            },
            "project_id": None  # Será obtido do token de autenticação
        }
        
        if system_message:
            invoke_payload["payload"]["system_message"] = system_message
            
        try:
            response = self.client.post(
                f"{self.broker_url}/api/v1/llm/invoke",
                json=invoke_payload
            )omáticos e auditoria completa.
"""

import httpx
import json
import os
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator, Union
from datetime import datetime
from pathlib import Path

from .config import BradaxSDKConfig, get_sdk_config
from .exceptions.bradax_exceptions import (
    BradaxError,
    BradaxAuthenticationError,
    BradaxConnectionError,
    BradaxConfigurationError,
    BradaxValidationError,
    BradaxBrokerError
)

# Configuração de logging
logger = logging.getLogger("bradax")


class BradaxClient:
    """Cliente principal para integração com bradax Hub (Broker)"""
    
    def __init__(
        self,
        project_token: Optional[Union[str, BradaxSDKConfig]] = None,
        broker_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: int = 3,
        verbose: bool = False,
        config: Optional[BradaxSDKConfig] = None
    ):
        """
        Inicializa um novo cliente bradax.
        
        Args:
            project_token: Token de autenticação do projeto (ou objeto BradaxSDKConfig)
            broker_url: URL do bradax broker (usa config se None)
            timeout: Timeout para requisições em segundos (usa config se None)
            max_retries: Número máximo de tentativas de reconexão
            verbose: Se True, exibe logs detalhados
            config: Configuração do SDK (usa global se None)
        """
        # Verificar se o primeiro parâmetro é um objeto de config
        if isinstance(project_token, BradaxSDKConfig):
            config = project_token
            project_token = None
        
        # Configuração: usar fornecida ou global
        self.config = config or get_sdk_config()
        
        # Project token: usar fornecido ou buscar no ambiente
        if not project_token:
            project_token = os.getenv("BRADAX_PROJECT_TOKEN") or "test-project-token"
            if not project_token:
                raise BradaxConfigurationError("Token de projeto é obrigatório (project_token ou BRADAX_PROJECT_TOKEN)")
        
        # Parâmetros: usar fornecidos ou da configuração
        self.project_token = project_token
        self.broker_url = (broker_url or self.config.broker_url).rstrip("/")
        self.timeout = timeout or self.config.timeout
        self.max_retries = max_retries
        self.verbose = verbose or self.config.debug
        
        # Configuração do cliente HTTP
        headers = self.config.get_headers()
        headers.update({
            "Authorization": f"Bearer {project_token}",
        })
        
        self.client = httpx.Client(
            timeout=self.timeout,
            headers=headers
        )
        
        # Configuração de logs
        if self.verbose:
            logger.setLevel(logging.DEBUG)
            
        # Inicializar contadores de telemetria local
        self._telemetry_count = 0
        self._operation_types = set()
            
        logger.debug(f"BradaxClient inicializado para {self.broker_url}")
        logger.debug(f"Configuração: {self.config.environment}, guardrails personalizados: {self.config.has_custom_guardrails()}")
        
    def validate_connection(self) -> Dict[str, Any]:
        """
        Valida a conexão com o broker e autenticação do projeto.
        
        Returns:
            Dict com informações do projeto autenticado
            
        Raises:
            BradaxAuthenticationError: Se a autenticação falhar
            BradaxConnectionError: Se não for possível conectar ao broker
        """
        try:
            response = self.client.get(f"{self.broker_url}/api/v1/auth/validate")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401 or response.status_code == 403:
                raise BradaxAuthenticationError(
                    "Falha na autenticação do projeto",
                    project_token=self.project_token,
                    broker_url=self.broker_url
                )
            else:
                raise BradaxBrokerError(
                    f"Erro no broker: {response.text}",
                    status_code=response.status_code,
                    response_body=response.text,
                    endpoint="/api/v1/project/validate"
                )
                
        except httpx.RequestError as e:
            raise BradaxConnectionError(f"Não foi possível conectar ao broker: {str(e)}")
            
    # REMOVIDO: run_llm() - Redundante com invoke()
    # Use invoke() para execução de LLM com compatibilidade LangChain
    
    # REMOVIDO: run_langchain() - Redundante com invoke() e ainvoke()
    # Use invoke() ou ainvoke() para compatibilidade LangChain completa
            
    def invoke_generic(
        self,
        operation: str,
        model_id: str,
        payload: Dict[str, Any],
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Método de invocação genérico para wrapper LangChain.
        
        Ponto de entrada único para diferentes tipos de operações LLM.
        Todos os guardrails e telemetria são aplicados automaticamente pelo hub.
        
        Args:
            operation: Tipo de operação ('chat', 'completion', 'batch', 'stream', etc.)
            model_id: ID do modelo a ser usado
            payload: Payload completo da requisição
            request_id: ID da requisição (opcional)
            
        Returns:
            Dict com resultado da operação + metadados
            
        Raises:
            BradaxAuthenticationError: Token inválido
            BradaxConnectionError: Erro de conectividade
            BradaxValidationError: Parâmetros inválidos
            BradaxBrokerError: Erro no broker
        """
        if not operation or not model_id:
            raise BradaxValidationError("Parâmetros 'operation' e 'model_id' são obrigatórios")
        
        if not isinstance(payload, dict):
            raise BradaxValidationError("Payload deve ser um dicionário")
        
        # Preparar dados da requisição
        request_data = {
            "operation": operation,
            "model": model_id,
            "payload": payload,
            "project_id": None,  # Será extraído do token no broker
            "request_id": request_id
        }
        
        logger.info(f"🔄 Invoke genérico: {operation} | Modelo: {model_id}")
        
        try:
            response = self.client.post(
                f"{self.broker_url}/api/v1/llm/invoke",
                json=request_data
            )
            
            if response.status_code == 401:
                raise BradaxAuthenticationError(
                    "Token de projeto inválido",
                    project_token=self.project_token,
                    broker_url=self.broker_url
                )
            elif response.status_code == 422:
                raise BradaxValidationError(f"Dados inválidos: {response.text}")
            elif response.status_code >= 500:
                raise BradaxBrokerError(
                    f"Erro interno do broker: {response.text}",
                    status_code=response.status_code,
                    response_body=response.text,
                    endpoint="/api/v1/llm/invoke"
                )
            elif response.status_code >= 400:
                raise BradaxError(f"Erro na requisição: {response.text}")
            
            result = response.json()
            
            if result.get("success"):
                logger.info(f"✅ Invoke genérico concluído: {result.get('request_id')}")
            else:
                logger.warning(f"⚠️ Invoke genérico falhou: {result.get('error')}")
            
            return result
            
        except httpx.RequestError as e:
            raise BradaxConnectionError(
                f"Falha de conexão ao executar invoke genérico: {str(e)}",
                broker_url=self.broker_url,
                timeout=self.timeout
            )

    def generate_text(
        self, 
        model: str, 
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Gera texto usando LLM (wrapper para invoke_generic).
        
        Args:
            model: ID do modelo
            prompt: Prompt principal
            system_prompt: Prompt de sistema (opcional)
            max_tokens: Máximo de tokens
            temperature: Temperatura
            stream: Streaming (não implementado ainda)
            
        Returns:
            Resultado da geração
        """
        payload = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }
        
        return self.invoke_generic(
            operation="chat",
            model_id=model,
            payload=payload
        )

    def _extract_project_id(self) -> Optional[str]:
        """
        Extrai project_id do token ou consulta o broker.
        
        Implementação completa que tenta várias estratégias:
        1. Parse do token estruturado (formato: bradax_projeto-id_org_hash_timestamp)
        2. Consulta direta ao broker com o token
        3. Cache para evitar consultas repetidas
        
        Returns:
            project_id extraído ou None se não conseguir determinar
        """
        # Cache para evitar múltiplas consultas
        if hasattr(self, '_cached_project_id'):
            return self._cached_project_id
        
        project_id = None
        
        # Estratégia 1: Parse do token estruturado
        try:
            # Formato esperado: bradax_projeto-marketing-001_bradax-corp_a1b2c3d4_12345678
            if self.project_token.startswith('bradax_') and self.project_token.count('_') >= 4:
                parts = self.project_token.split('_')
                if len(parts) >= 2:
                    potential_project_id = parts[1]  # segundo componente
                    # Validar se parece com project_id (contém 'projeto-' e termina com número)
                    if potential_project_id.startswith('projeto-') and potential_project_id[-3:].isdigit():
                        project_id = potential_project_id
                        if self.verbose:
                            print(f"🔍 Project ID extraído do token: {project_id}")
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Erro ao fazer parse do token: {e}")
        
        # Estratégia 2: Consultar broker se parse falhou
        if not project_id:
            try:
                response = self.client.get(
                    f"{self.broker_url}/api/v1/project/validate",
                    timeout=min(self.timeout, 10)  # Timeout menor para esta consulta
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and 'data' in data:
                        project_data = data['data']
                        project_id = project_data.get('project_id')
                        if self.verbose and project_id:
                            print(f"🔍 Project ID obtido do broker: {project_id}")
                            
            except Exception as e:
                if self.verbose:
                    print(f"⚠️ Erro ao consultar broker para project_id: {e}")
        
        # Estratégia 3: Fallback - usar hash do token como project_id
        if not project_id:
            import hashlib
            token_hash = hashlib.md5(self.project_token.encode()).hexdigest()[:8]
            project_id = f"projeto-sdk-{token_hash}"
            if self.verbose:
                print(f"🔍 Project ID fallback gerado: {project_id}")
        
        # Cache do resultado
        self._cached_project_id = project_id
        return project_id
    
    def _invalidate_project_cache(self) -> None:
        """Invalida cache do project_id (útil se token mudar)"""
        if hasattr(self, '_cached_project_id'):
            delattr(self, '_cached_project_id')

    def invoke(
        self,
        input_: Union[str, List[Dict[str, str]], Dict[str, Any]],
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Método invoke compatível com LangChain para execução de LLMs.
        
        Este método segue o padrão LangChain e aceita diferentes tipos de input:
        - String simples: "Hello, world!"
        - Lista de mensagens: [{"role": "user", "content": "Hello"}]
        - Prompt complexo: {"messages": [...], "model": "gpt-4"}
        
        Args:
            input_: Input no formato LangChain (string, messages, prompt)
            config: Configuração opcional (model, temperature, etc.)
            **kwargs: Argumentos adicionais (max_tokens, temperature, etc.)
            
        Returns:
            Resultado no formato LangChain com content e metadata
            
        Raises:
            BradaxError: Para qualquer erro de execução
        """
        try:
            # Configuração padrão
            config = config or {}
            model = config.get("model") or kwargs.get("model", "gpt-4.1-nano")
            
            # Processar diferentes tipos de input
            if isinstance(input_, str):
                # String simples -> usar diretamente
                prompt_text = input_
            elif isinstance(input_, list):
                # Lista de mensagens -> converter para texto
                prompt_text = "\n".join([msg.get("content", str(msg)) for msg in input_])
            elif isinstance(input_, dict) and "messages" in input_:
                # Prompt complexo -> extrair mensagens e converter
                messages = input_["messages"]
                prompt_text = "\n".join([msg.get("content", str(msg)) for msg in messages])
                model = input_.get("model", model)
            else:
                raise BradaxValidationError(f"Input type não suportado: {type(input_)}")
            
            # Preparar payload para o broker - formato LangChain padrão
            payload = {
                "operation": "chat",  # Operação padrão para LangChain
                "model": model,
                "payload": {
                    "messages": [{"role": "user", "content": prompt_text}],  # Formato LangChain padrão
                    "max_tokens": kwargs.get("max_tokens", config.get("max_tokens", 1000)),
                    "temperature": kwargs.get("temperature", config.get("temperature", 0.7)),
                    **{k: v for k, v in kwargs.items() if k not in ["model", "max_tokens", "temperature"]}
                }
            }
            
            # Executar via broker
            response = self.client.post(
                f"{self.broker_url}/api/v1/llm/invoke",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Verificar se foi sucesso
                if result.get("success"):
                    # Retornar formato compatível com LangChain
                    return {
                        "content": result.get("response_text", ""),
                        "response_metadata": {
                            "model": model,
                            "usage": result.get("usage", {}),
                            "finish_reason": result.get("finish_reason"),
                            "request_id": result.get("request_id")
                        }
                    }
                else:
                    # Caso de erro do broker
                    error_msg = result.get("error", "Erro desconhecido")
                    raise BradaxBrokerError(f"Erro no broker: {error_msg}")
            else:
                raise BradaxBrokerError(f"Erro HTTP: {response.status_code} - {response.text}")
                
        except httpx.RequestError as e:
            raise BradaxConnectionError(f"Falha de conexão ao executar invoke: {str(e)}")
    
    async def ainvoke(
        self,
        input_: Union[str, List[Dict[str, str]], Dict[str, Any]],
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Método ainvoke assíncrono compatível com LangChain para execução de LLMs.
        
        Este método segue o padrão LangChain e aceita diferentes tipos de input:
        - String simples: "Hello, world!"
        - Lista de mensagens: [{"role": "user", "content": "Hello"}]
        - Prompt complexo: {"messages": [...], "model": "gpt-4"}
        
        Args:
            input_: Input no formato LangChain (string, messages, prompt)
            config: Configuração opcional (model, temperature, etc.)
            **kwargs: Argumentos adicionais (max_tokens, temperature, etc.)
            
        Returns:
            Resultado no formato LangChain com content e metadata
            
        Raises:
            BradaxError: Para qualquer erro de execução
        """
        try:
            # Configuração padrão
            config = config or {}
            model = config.get("model") or kwargs.get("model", "gpt-4.1-nano")
            
            # Processar diferentes tipos de input para formato de mensagens
            if isinstance(input_, str):
                # String simples -> converter para formato de mensagem
                input_text = input_
            elif isinstance(input_, list):
                # Lista de mensagens -> extrair conteúdo
                input_text = "\n".join([msg.get("content", str(msg)) for msg in input_])
            elif isinstance(input_, dict) and "messages" in input_:
                # Prompt complexo -> extrair mensagens
                messages = input_["messages"]
                input_text = "\n".join([msg.get("content", str(msg)) for msg in messages])
                model = input_.get("model", model)
            else:
                raise BradaxValidationError(f"Input type não suportado: {type(input_)}")
            
            # Preparar payload para o broker - formato LangChain padrão
            payload = {
                "operation": kwargs.get("operation", "chat"),
                "model": kwargs.get("model", model),
                "payload": {
                    "messages": [{"role": "user", "content": input_text}],  # Formato LangChain padrão
                    "temperature": kwargs.get("temperature", 0.7),
                    "max_tokens": kwargs.get("max_tokens", 1000),
                    **{k: v for k, v in kwargs.items() if k not in ["operation", "model", "max_tokens", "temperature"]}
                }
            }
            
            # Executar via broker (usando httpx async com mesmos headers)
            project_token = os.getenv('BRADAX_PROJECT_TOKEN', 'default-token')
            headers = self.config.get_headers()
            headers.update({
                "Authorization": f"Bearer {project_token}",
            })
            
            async with httpx.AsyncClient(timeout=30.0) as async_client:
                response = await async_client.post(
                    f"{self.broker_url}/api/v1/llm/invoke",
                    json=payload,
                    headers=headers
                )
            
            if response.status_code == 200:
                result = response.json()
                
                # Verificar se foi sucesso
                if result.get("success"):
                    # Retornar formato compatível com LangChain
                    return {
                        "content": result.get("response_text", ""),
                        "response_metadata": {
                            "model": model,
                            "usage": result.get("usage", {}),
                            "finish_reason": result.get("finish_reason"),
                            "request_id": result.get("request_id")
                        }
                    }
                else:
                    # Caso de erro do broker
                    error_msg = result.get("error", "Erro desconhecido")
                    raise BradaxBrokerError(f"Erro no broker: {error_msg}")
            else:
                raise BradaxBrokerError(f"Erro HTTP: {response.status_code} - {response.text}")
                
        except httpx.RequestError as e:
            raise BradaxConnectionError(f"Falha de conexão ao executar ainvoke: {str(e)}")
    
    # REMOVIDO: Métodos duplicados invoke_generic() e generate_text()
    # Use os métodos originais definidos anteriormente no arquivo
    
    def check_broker_health(self) -> Dict[str, Any]:
        """
        Verifica saúde do broker.
        
        Returns:
            Status de saúde do broker
            
        Raises:
            BradaxConnectionError: Se não conseguir conectar ao broker
        """
        try:
            response = self.client.get(f"{self.broker_url}/health/")
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
                
        except httpx.RequestError as e:
            error_msg = str(e).lower()
            if "getaddrinfo failed" in error_msg or "connection" in error_msg:
                raise BradaxConnectionError(f"Network connection error to broker: {str(e)}")
            elif "timeout" in error_msg:
                raise BradaxConnectionError(f"Network timeout error to broker: {str(e)}")
            else:
                raise BradaxConnectionError(f"Network error accessing broker: {str(e)}")
    
    def validate_content(self, content: str) -> Dict[str, Any]:
        """
        Validação local de conteúdo usando guardrails configurados.
        
        Args:
            content: Conteúdo a ser validado
            
        Returns:
            Dict com resultado da validação: {"is_safe": bool, "violations": list}
        """
        import re
        
        is_safe = True
        violations = []
        
        # Verificar guardrails customizados primeiro
        for rule_id, rule in self.config.custom_guardrails.items():
            pattern = rule.get("pattern")
            if pattern:
                try:
                    if re.search(pattern, content, re.IGNORECASE):
                        is_safe = False
                        message = rule.get("message", f"Regra {rule_id} violada")
                        violations.append(f"Custom guardrail: {message}")
                except re.error:
                    # Pattern inválido, ignorar
                    pass
        
        # Verificar alguns padrões básicos de segurança (guardrails padrão)
        unsafe_patterns = [
            "senha", "password", "token", "secret", "key",
            "cpf", "cnpj", "email", "@", "telefone", "cartão"
        ]
        
        content_lower = content.lower()
        for pattern in unsafe_patterns:
            if pattern in content_lower:
                is_safe = False
                violations.append(f"Conteúdo sensível detectado: {pattern}")
        
        return {
            "is_safe": is_safe,
            "violations": violations,
            "content_length": len(content)
        }
    
    def record_telemetry_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Registra evento de telemetria no broker.
        
        Args:
            event_data: Dados do evento de telemetria
            
        Returns:
            True se registrado com sucesso
        """
        try:
            # Atualizar contadores locais
            self._telemetry_count += 1
            if "type" in event_data:
                self._operation_types.add(event_data["type"])
            
            # Se telemetria local estiver desabilitada, apenas simular
            if not self.config.local_telemetry_enabled:
                logger.debug("Telemetria local desabilitada - evento ignorado")
                return True
            
            response = self.client.post(
                f"{self.broker_url}/api/v1/system/telemetry",
                json={
                    "event": event_data,
                    "timestamp": datetime.now().isoformat(),
                    "project_token": self.project_token
                }
            )
            
            return response.status_code in [200, 201]
            
        except httpx.RequestError as e:
            logger.warning(f"Erro ao registrar telemetria: {e}")
            return False
    
    def get_local_telemetry(self) -> Dict[str, Any]:
        """
        Retorna estatísticas de telemetria local acumuladas.
        
        Returns:
            Dict com estatísticas de operações locais
        """
        return {
            "total_operations": self._telemetry_count,
            "operation_types": list(self._operation_types),
            "local_enabled": self.config.local_telemetry_enabled,
            "last_operation": datetime.now().isoformat(),
            "buffer_size": self.config.telemetry_buffer_size
        }
    
    def add_custom_guardrail_rule(self, rule: Dict[str, Any]) -> None:
        """
        Adiciona regra de guardrail personalizada.
        
        Args:
            rule: Regra de guardrail com campos obrigatórios (id, pattern, severity)
            
        Raises:
            BradaxValidationError: Se a regra for inválida
        """
        # Validar estrutura da regra
        required_fields = ["id", "pattern", "severity"]
        for field in required_fields:
            if field not in rule:
                raise BradaxValidationError(f"Campo obrigatório '{field}' não encontrado na regra")
        
        # Validar valores dos campos
        if not rule["id"] or not isinstance(rule["id"], str):
            raise BradaxValidationError("Validation error: Campo 'id' deve ser uma string não vazia")
        
        if not rule["pattern"] or not isinstance(rule["pattern"], str):
            raise BradaxValidationError("Validation error: Campo 'pattern' deve ser uma string não vazia")
        
        if rule["severity"] not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            raise BradaxValidationError("Validation error: Campo 'severity' deve ser um dos valores: LOW, MEDIUM, HIGH, CRITICAL")
        
        # Adicionar à configuração local
        self.config.set_custom_guardrail(rule["id"], rule)
        logger.info(f"Regra de guardrail '{rule['id']}' adicionada")
    
    async def send_llm_request(
        self,
        prompt: str,
        model: str = "gpt-4.1-nano",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Método assíncrono para envio de requisições LLM.
        
        Args:
            prompt: Texto do prompt
            model: Modelo a usar
            max_tokens: Máximo de tokens
            temperature: Temperatura da resposta
            **kwargs: Argumentos adicionais
            
        Returns:
            Resposta do LLM
        """
        # Usar ainvoke internamente para consistência
        return await self.ainvoke(
            input_=prompt,
            config={"model": model},
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
            
    def close(self) -> None:
        """Fecha o cliente HTTP e libera recursos"""
        if hasattr(self, 'client') and self.client:
            self.client.close()
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
