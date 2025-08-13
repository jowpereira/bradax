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
from .telemetry_interceptor import TelemetryInterceptor, initialize_global_telemetry
from .logging_config import BradaxSDKLogger
from .exceptions.bradax_exceptions import (
    BradaxError,
    BradaxAuthenticationError,
    BradaxConnectionError,
    BradaxConfigurationError,
    BradaxValidationError,
    BradaxBrokerError
)


class BradaxClient:
    """Cliente principal para integração com bradax Hub (Broker)"""

    def __init__(
        self,
        project_token: Optional[Union[str, BradaxSDKConfig]] = None,
        broker_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: int = 3,
        verbose: bool = False,
        config: Optional[BradaxSDKConfig] = None,
        **kwargs
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

        Raises:
            BradaxConfigurationError: Se tentar desabilitar telemetria
        """
        # 🚨 PROTEÇÃO ANTI-BURLA: Bloquear desabilitação de telemetria
        if 'telemetry_enabled' in kwargs and not kwargs['telemetry_enabled']:
            raise BradaxConfigurationError(
                "🚨 VIOLAÇÃO DE SEGURANÇA: Telemetria é obrigatória e não pode ser desabilitada. "
                "Todas as interações devem ser auditadas conforme política corporativa."
            )

        if 'disable_telemetry' in kwargs and kwargs['disable_telemetry']:
            raise BradaxConfigurationError(
                "🚨 VIOLAÇÃO DE SEGURANÇA: Tentativa de bypass da telemetria detectada. "
                "O uso do SDK requer auditoria completa."
            )

        # Verificar se o primeiro parâmetro é um objeto de config
        if isinstance(project_token, BradaxSDKConfig):
            config = project_token
            project_token = None

        # Configuração: usar fornecida ou global
        self.config = config or get_sdk_config()

        # Project token: usar fornecido ou buscar no ambiente (sem fallback inseguro)
        if not project_token:
            project_token = os.getenv("BRADAX_PROJECT_TOKEN")
        if not project_token:
            raise BradaxConfigurationError(
                "🚨 Segurança: Token de projeto é obrigatório (defina project_token ou variável BRADAX_PROJECT_TOKEN)."
            )
        if project_token == "test-project-token":
            raise BradaxAuthenticationError(
                "🚨 Segurança: Uso de token placeholder proibido. Forneça token real do projeto.",
                context={
                    "project_token": project_token,
                    "broker_url": broker_url or (self.config.broker_url if hasattr(self, 'config') else 'N/A')
                }
            )

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

        # Configurar logger estruturado
        self.logger = BradaxSDKLogger("bradax.sdk.client", verbose=self.verbose)

        self.client = httpx.Client(
            timeout=self.timeout,
            headers=headers
        )

        # Configuração de logs
        if self.verbose:
            self.logger.logger.setLevel(logging.DEBUG)

        # Inicializar contadores de telemetria local
        self._telemetry_count = 0
        self._operation_types = set()

        # Inicializar interceptor de telemetria para enviar dados ao broker
        from .telemetry_interceptor import initialize_global_telemetry
        self.telemetry_interceptor = initialize_global_telemetry(self.broker_url, self.project_token)

        # Telemetria é sempre habilitada (não pode ser desabilitada)
        self.telemetry_enabled = True

        self.logger.debug(
            "BradaxClient inicializado",
            extra_data={
                "broker_url": self.broker_url,
                "environment": self.config.environment,
                "has_custom_guardrails": self.config.has_custom_guardrails(),
                "timeout": self.timeout
            }
        )

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
            response = self.client.post(f"{self.broker_url}/api/v1/auth/validate")

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
                    url="/api/v1/project/validate",
                    context={"response_body": response.text, "endpoint": "/api/v1/project/validate"}
                )

        except httpx.RequestError as e:
            raise BradaxConnectionError(f"Não foi possível conectar ao broker: {str(e)}")

    def _invoke_generic(
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
            "request_id": request_id,
            "custom_guardrails": self.config.get_custom_guardrails()  # CORREÇÃO: Enviar guardrails para broker
        }

        self.logger.info(
            "_invoke_generic interno iniciado",
            extra_data={"operation": operation, "model": model_id, "request_id": request_id}
        )

        # 🔒 GERAR HEADERS DE TELEMETRIA OBRIGATÓRIOS
        telemetry_headers = self.telemetry_interceptor.get_telemetry_headers()

        try:
            response = self.client.post(
                f"{self.broker_url}/api/v1/llm/invoke",
                json=request_data,
                headers=telemetry_headers  # ← CORREÇÃO: Headers obrigatórios
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
                    url="/api/v1/llm/invoke",
                    context={"response_body": response.text, "endpoint": "/api/v1/llm/invoke"}
                )
            elif response.status_code >= 400:
                raise BradaxError(f"Erro na requisição: {response.text}")

            result = response.json()

            if result.get("success"):
                self.logger.info(
                    "_invoke_generic concluído",
                    extra_data={"request_id": result.get('request_id')}
                )
            else:
                self.logger.warning(
                    "_invoke_generic falhou",
                    extra_data={"error": result.get('error')}
                )

            return result

        except httpx.RequestError as e:
            raise BradaxConnectionError(
                f"Falha de conexão ao executar _invoke_generic: {str(e)}",
                broker_url=self.broker_url,
                timeout=self.timeout
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
                            self.logger.info(
                                "Project ID extraído do token",
                                extra_data={"project_id": project_id}
                            )
        except Exception as e:
            if self.verbose:
                self.logger.warning(
                    "Erro ao fazer parse do token",
                    extra_data={"error": str(e)}
                )

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
                            self.logger.info(
                                "Project ID obtido do broker",
                                extra_data={"project_id": project_id}
                            )

            except Exception as e:
                if self.verbose:
                    self.logger.warning(
                        "Erro ao consultar broker para project_id",
                        extra_data={"error": str(e)}
                    )

        # Estratégia 3: Fallback - usar hash do token como project_id
        if not project_id:
            import hashlib
            token_hash = hashlib.md5(self.project_token.encode()).hexdigest()[:8]
            project_id = f"projeto-sdk-{token_hash}"
            if self.verbose:
                self.logger.info(
                    "Project ID fallback gerado",
                    extra_data={"project_id": project_id}
                )

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
                },
                "custom_guardrails": self.config.get_custom_guardrails()  # CORREÇÃO: Enviar guardrails para broker
            }

            # 🔒 VERIFICAÇÃO OBRIGATÓRIA DE TELEMETRIA
            if not self.telemetry_enabled:
                raise BradaxConfigurationError(
                    "🚨 VIOLAÇÃO DE SEGURANÇA: Telemetria desabilitada detectada. "
                    "Todas as invocações devem ser auditadas."
                )

            # INTERCEPTAÇÃO TELEMETRIA: Capturar request antes do envio
            request_data = self.telemetry_interceptor.intercept_request(
                prompt=input_,
                model=model,
                temperature=kwargs.get("temperature", config.get("temperature", 0.7)),
                max_tokens=kwargs.get("max_tokens", config.get("max_tokens", 1000)),
                metadata={
                    "operation": "invoke",
                    "config": config,
                    "kwargs": kwargs,
                    "payload": payload,
                    "security_check": "telemetry_verified"
                }
            )

            # 🔒 GERAR HEADERS DE TELEMETRIA OBRIGATÓRIOS
            telemetry_headers = self.telemetry_interceptor.get_telemetry_headers()

            # Combinar headers (telemetria + config + auth) – manter telemetria obrigatória
            headers = {}
            try:
                headers.update(self.config.get_headers())  # headers adicionais do SDK/config
            except Exception:
                pass
            headers.update(telemetry_headers)
            # Authorization: usar token explícito se disponível (priorizar self.project_token)
            project_token = os.getenv('BRADAX_PROJECT_TOKEN') or getattr(self, 'project_token', None)
            if project_token:
                headers['Authorization'] = f"Bearer {project_token}"

            # Executar via broker COM HEADERS COMPLETOS
            response = self.client.post(
                f"{self.broker_url}/api/v1/llm/invoke",
                json=payload,
                headers=headers
            )

            if response.status_code == 200:
                result = response.json()

                # Verificar se foi sucesso
                if result.get("success"):
                    # Formato de resposta compatível com LangChain
                    langchain_response = {
                        "content": result.get("response_text", ""),
                        "response_metadata": {
                            "model": model,
                            "usage": result.get("usage", {}),
                            "finish_reason": result.get("finish_reason"),
                            "request_id": result.get("request_id")
                        }
                    }

                    # INTERCEPTAÇÃO TELEMETRIA: Capturar response após sucesso
                    self.telemetry_interceptor.capture_response(
                        request_data=request_data,
                        response_data=langchain_response,
                        raw_response=result,
                        success=True
                    )

                    # Retornar formato compatível com LangChain
                    return langchain_response
                else:
                    # Caso de erro do broker
                    error_msg = result.get("error", "Erro desconhecido")

                    # INTERCEPTAÇÃO TELEMETRIA: Capturar erro do broker
                    self.telemetry_interceptor.capture_response(
                        request_data=request_data,
                        response_data=None,
                        raw_response=result,
                        success=False,
                        error_message=error_msg
                    )

                    raise BradaxBrokerError(f"Erro no broker: {error_msg}")
            else:
                # INTERCEPTAÇÃO TELEMETRIA: Capturar erro HTTP
                self.telemetry_interceptor.capture_response(
                    request_data=request_data,
                    response_data=None,
                    raw_response={"status_code": response.status_code, "text": response.text},
                    success=False,
                    error_message=f"Erro HTTP: {response.status_code}"
                )

                raise BradaxBrokerError(f"Erro HTTP: {response.status_code} - {response.text}")

        except httpx.RequestError as e:
            # INTERCEPTAÇÃO TELEMETRIA: Capturar erro de conexão
            if 'request_data' in locals():
                self.telemetry_interceptor.capture_response(
                    request_data=request_data,
                    response_data=None,
                    raw_response=None,
                    success=False,
                    error_message=f"Conexão falhou: {str(e)}"
                )

            raise BradaxConnectionError(f"Falha de conexão ao executar invoke: {str(e)}")

    async def ainvoke(self, *args, **kwargs):  # type: ignore[override]
        """Função assíncrona desabilitada.
        Política atual: apenas invoke síncrono autorizado. Uso futuro planejado.
        """
        raise BradaxConfigurationError(
            "🚨 Segurança: ainvoke() desabilitado nesta versão. Use invoke()."
        )


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

    # REMOVIDO: validate_content() - Toda validação é centralizada no broker
    # Use o broker para todas as validações via guardrails

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
                self.logger.debug("Telemetria local desabilitada - evento ignorado")
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
            self.logger.warning(
                "Erro ao registrar telemetria",
                extra_data={"error": str(e)}
            )
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
        self.logger.info(
            "Regra de guardrail adicionada",
            extra_data={"rule_id": rule["id"], "rule_type": rule["type"], "severity": rule["severity"]}
        )

    def close(self) -> None:
        """Fecha o cliente HTTP e libera recursos"""
        if hasattr(self, 'client') and self.client:
            self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
