"""
Cliente SDK bradax - Implementação principal

SDK Python profissional para comunicação segura com o bradax Broker.
Inclui autenticação por projeto, guardrails automáticos e auditoria completa.
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
        project_token: str,
        broker_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: int = 3,
        verbose: bool = False,
        config: Optional[BradaxSDKConfig] = None
    ):
        """
        Inicializa um novo cliente bradax.
        
        Args:
            project_token: Token de autenticação do projeto
            broker_url: URL do bradax broker (usa config se None)
            timeout: Timeout para requisições em segundos (usa config se None)
            max_retries: Número máximo de tentativas de reconexão
            verbose: Se True, exibe logs detalhados
            config: Configuração do SDK (usa global se None)
        """
        if not project_token:
            raise BradaxConfigurationError("Token de projeto é obrigatório")
        
        # Configuração: usar fornecida ou global
        self.config = config or get_sdk_config()
        
        # Parâmetros: usar fornecidos ou da configuração
        self.project_token = project_token
        self.broker_url = (broker_url or self.config.broker_url).rstrip("/")
        self.timeout = timeout or self.config.timeout
        self.max_retries = max_retries
        self.verbose = verbose or self.config.debug
        
        # Configuração do cliente HTTP
        headers = self.config.get_headers()
        headers.update({
            "X-Project-Token": project_token,
        })
        
        self.client = httpx.Client(
            timeout=self.timeout,
            headers=headers
        )
        
        # Configuração de logs
        if self.verbose:
            logger.setLevel(logging.DEBUG)
            
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
            response = self.client.get(f"{self.broker_url}/api/v1/project/validate")
            
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
            raise BradaxConnectionError(
                f"Não foi possível conectar ao broker: {str(e)}",
                broker_url=self.broker_url,
                timeout=self.timeout
            )
            
    def run_llm(self, 
               prompt: str, 
               model: str = "gpt-3.5-turbo", 
               max_tokens: int = 1000,
               temperature: float = 0.7,
               system_message: str = None,
               options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executa um modelo LLM através do broker.
        
        Args:
            prompt: O texto do prompt
            model: Nome do modelo (padrão: gpt-3.5-turbo)
            max_tokens: Número máximo de tokens na resposta
            temperature: Temperatura (criatividade) da resposta
            system_message: Mensagem de sistema opcional
            options: Opções adicionais para o modelo
            
        Returns:
            Resultado da execução do LLM
            
        Raises:
            BradaxError: Se ocorrer algum erro durante a execução
        """
        options = options or {}
        
        payload = {
            "prompt": prompt,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "options": options
        }
        
        if system_message:
            payload["system_message"] = system_message
            
        try:
            response = self.client.post(
                f"{self.broker_url}/api/v1/llm/run",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise BradaxBrokerError(
                    f"Erro ao executar LLM: {response.text}",
                    status_code=response.status_code,
                    response_body=response.text,
                    endpoint="/api/v1/llm/run"
                )
                
        except httpx.RequestError as e:
            raise BradaxConnectionError(
                f"Falha de conexão ao executar LLM: {str(e)}",
                broker_url=self.broker_url,
                timeout=self.timeout
            )
            
    def run_langchain(self, 
                     chain_type: str,
                     inputs: Dict[str, Any],
                     options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executa uma chain do LangChain através do broker.
        
        Args:
            chain_type: Tipo de chain a ser executada
            inputs: Entradas para a chain
            options: Opções adicionais para configuração da chain
            
        Returns:
            Resultado da execução da chain
            
        Raises:
            BradaxError: Se ocorrer algum erro durante a execução
        """
        options = options or {}
        
        payload = {
            "chain_type": chain_type,
            "inputs": inputs,
            "options": options
        }
        
        try:
            response = self.client.post(
                f"{self.broker_url}/api/v1/langchain/run",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise BradaxBrokerError(
                    f"Erro ao executar LangChain: {response.text}",
                    status_code=response.status_code,
                    response_body=response.text,
                    endpoint="/api/v1/langchain/run"
                )
                
        except httpx.RequestError as e:
            raise BradaxConnectionError(
                f"Falha de conexão ao executar LangChain: {str(e)}",
                broker_url=self.broker_url,
                timeout=self.timeout
            )
            
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
        operation: str,
        model: str,
        payload: Dict[str, Any],
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Método de invocação central para LangChain wrapper.
        
        Este é o método primitivo que faz comunicação direta com o broker.
        Outros métodos como generate_text() usam este internamente.
        
        Args:
            operation: Tipo de operação ('chat', 'completion', 'batch', 'stream', etc.)
            model: ID do modelo LLM
            payload: Dados específicos da operação (prompts, parâmetros, etc.)
            request_id: ID opcional da requisição
            
        Returns:
            Resultado da operação com metadados
            
        Raises:
            BradaxError: Para qualquer erro de execução
        """
        try:
            # Preparar dados da requisição
            request_data = {
                "operation": operation,
                "model": model,
                "payload": payload,
                "project_id": self._extract_project_id(),
                "request_id": request_id
            }
            
            # Executar via broker
            response = self.client.post(
                f"{self.broker_url}/api/v1/llm/invoke",
                json=request_data,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if self.verbose:
                    print(f"✅ Invoke {operation} concluído: {result.get('request_id', 'N/A')}")
                return result
            else:
                error_msg = f"Invoke {operation} falhou: {response.text}"
                if self.verbose:
                    print(f"❌ {error_msg}")
                raise BradaxBrokerError(
                    error_msg,
                    error_code="INVOKE_HTTP_ERROR",
                    context={
                        "status_code": response.status_code,
                        "response_body": response.text,
                        "endpoint": "/api/v1/llm/invoke",
                        "operation": operation,
                        "model": model
                    }
                )
                
        except httpx.RequestError as e:
            error_msg = f"Erro de conexão no invoke: {str(e)}"
            if self.verbose:
                print(f"❌ {error_msg}")
            raise BradaxConnectionError(
                error_msg,
                error_code="INVOKE_CONNECTION_ERROR",
                context={
                    "broker_url": self.broker_url,
                    "timeout": self.timeout,
                    "operation": operation,
                    "model": model
                }
            )
        except Exception as e:
            error_msg = f"Erro inesperado no invoke: {str(e)}"
            if self.verbose:
                print(f"❌ {error_msg}")
            raise BradaxError(error_msg)

    def generate_text(
        self,
        prompt: str,
        model: str = "gpt-4o-mini",
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Método de conveniência para geração de texto.
        
        Usa invoke() internamente para operação 'chat'.
        Interface simples para casos básicos de uso.
        
        Args:
            prompt: Texto de entrada
            model: Modelo a ser usado
            system_prompt: Prompt de sistema opcional
            max_tokens: Máximo de tokens
            temperature: Criatividade (0-2)
            stream: Se deve usar streaming
            
        Returns:
            Resultado da geração de texto
        """
        payload = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }
        
        return self.invoke(
            operation="chat",
            model=model,
            payload=payload
        )

    def health_check(self) -> Dict[str, Any]:
        """
        Verifica conectividade e saúde do broker.
        
        Returns:
            Status de saúde do sistema
        """
        try:
            response = self.client.get(f"{self.broker_url}/api/v1/health")
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "status": "error",
                    "message": f"Status HTTP {response.status_code}",
                    "details": response.text
                }
                
        except httpx.RequestError as e:
            return {
                "status": "error", 
                "message": "Connection failed",
                "details": str(e)
            }
            
    def add_custom_guardrail(self, name: str, rule: Dict[str, Any]) -> None:
        """
        Adiciona um guardrail personalizado (além dos defaults do projeto).
        
        IMPORTANTE: Guardrails e telemetria do projeto são obrigatórios e não podem
        ser desabilitados. Este método ADICIONA validações personalizadas.
        
        Args:
            name: Nome único do guardrail personalizado
            rule: Configuração da regra personalizada
            
        Example:
            client.add_custom_guardrail("content_length", {
                "max_chars": 5000,
                "check_encoding": "utf-8",
                "forbidden_patterns": ["spam", "phishing"]
            })
        """
        self.config.set_custom_guardrail(name, rule)
        logger.debug(f"Guardrail personalizado '{name}' adicionado")
    
    def remove_custom_guardrail(self, name: str) -> bool:
        """
        Remove um guardrail personalizado.
        
        Args:
            name: Nome do guardrail a remover
            
        Returns:
            True se removido, False se não existia
        """
        removed = self.config.remove_custom_guardrail(name)
        if removed:
            logger.debug(f"Guardrail personalizado '{name}' removido")
        return removed
    
    def list_custom_guardrails(self) -> Dict[str, Any]:
        """
        Lista todos os guardrails personalizados configurados.
        
        Returns:
            Dicionário com os guardrails personalizados
        """
        return self.config.get_custom_guardrails()
    
    def get_telemetry_config(self) -> Dict[str, Any]:
        """
        Retorna configuração de telemetria local.
        
        Note: A telemetria do projeto é sempre ativa e obrigatória.
        Esta é apenas a configuração adicional local.
        """
        return {
            "local_enabled": self.config.local_telemetry_enabled,
            "buffer_size": self.config.telemetry_buffer_size,
            "environment": self.config.environment
        }
            
    def close(self) -> None:
        """Fecha o cliente HTTP e libera recursos"""
        if hasattr(self, 'client') and self.client:
            self.client.close()
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
