"""
LangChain-based LLM Provider Implementation

Sistema de providers para integração com serviços de LLM usando LangChain.
Implementação focada em confiabilidade e tratamento robusto de erros.
"""

import os
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()

# LangChain imports
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# Bradax robust exception system
from ...exceptions import (
    BradaxExternalAPIException,
    BradaxConfigurationException,
    BradaxTechnicalException,
    ErrorSeverity
)


class LLMProvider(ABC):
    """Interface base para providers de LLM"""
    
    @abstractmethod
    def invoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Invoca o modelo LLM com as mensagens fornecidas"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se o provider está disponível"""
        pass


class OpenAIProvider(LLMProvider):
    """
    Provider OpenAI usando LangChain
    
    Implementação robusta com tratamento de erros usando o sistema
    de exceções Bradax. Sem fallbacks ou simulações.
    """
    
    def __init__(self):
        """Inicializa o provider OpenAI"""
        if not LANGCHAIN_AVAILABLE:
            raise BradaxConfigurationException(
                message="LangChain não disponível. Instale langchain-openai",
                config_key="langchain_dependency",
                severity=ErrorSeverity.CRITICAL
            )
        
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise BradaxConfigurationException(
                message="Chave API OpenAI não configurada",
                config_key="OPENAI_API_KEY",
                severity=ErrorSeverity.CRITICAL
            )
        
        try:
            self.client = ChatOpenAI(
                api_key=self.api_key,
                model="gpt-3.5-turbo",
                temperature=0.7
            )
        except Exception as e:
            raise BradaxTechnicalException(
                message=f"Falha ao inicializar cliente OpenAI: {str(e)}",
                component="OpenAIProvider",
                operation="initialization",
                severity=ErrorSeverity.CRITICAL
            )
    
    def invoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Invoca o modelo OpenAI via LangChain
        
        Args:
            messages: Lista de mensagens no formato [{"role": "user", "content": "texto"}]
            **kwargs: Parâmetros adicionais para o modelo
        
        Returns:
            str: Resposta do modelo
            
        Raises:
            BradaxExternalAPIException: Erros da API OpenAI
            BradaxTechnicalException: Erros técnicos internos
        """
        if not self.is_available():
            raise BradaxTechnicalException(
                message="Provider OpenAI não está disponível",
                component="OpenAIProvider",
                operation="invoke",
                severity=ErrorSeverity.HIGH
            )
        
        try:
            # Converte mensagens para formato LangChain
            langchain_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    langchain_messages.append(SystemMessage(content=content))
                elif role in ["user", "human"]:
                    langchain_messages.append(HumanMessage(content=content))
                else:
                    # Trata roles desconhecidos como user
                    langchain_messages.append(HumanMessage(content=content))
            
            # Executa a invocação
            response = self.client.invoke(langchain_messages)
            
            # Extrai o conteúdo da resposta
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
                
        except Exception as e:
            # Determina se é erro da API ou erro técnico
            error_message = str(e).lower()
            
            if any(keyword in error_message for keyword in [
                "api", "rate limit", "quota", "authentication", "invalid_api_key",
                "insufficient_quota", "model_not_found"
            ]):
                raise BradaxExternalAPIException(
                    message=f"Erro na API OpenAI: {str(e)}",
                    api_name="OpenAI",
                    endpoint="chat/completions",
                    status_code=getattr(e, 'status_code', None),
                    response_body=str(e),
                    severity=ErrorSeverity.HIGH
                )
            else:
                raise BradaxTechnicalException(
                    message=f"Erro técnico durante invocação OpenAI: {str(e)}",
                    component="OpenAIProvider",
                    operation="invoke",
                    severity=ErrorSeverity.HIGH
                )
    
    def is_available(self) -> bool:
        """Verifica se o provider está disponível"""
        return (
            LANGCHAIN_AVAILABLE and 
            self.api_key is not None and 
            hasattr(self, 'client') and 
            self.client is not None
        )


# Provider registry
available_providers = {}

def get_available_providers() -> Dict[str, LLMProvider]:
    """Retorna os providers disponíveis"""
    global available_providers
    
    if not available_providers:
        # Registra apenas providers que estão efetivamente disponíveis
        if LANGCHAIN_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                openai_provider = OpenAIProvider()
                if openai_provider.is_available():
                    available_providers["openai"] = openai_provider
            except Exception:
                # Se falhou ao inicializar, não adiciona à lista
                pass
    
    return available_providers


def get_provider(provider_name: str) -> LLMProvider:
    """
    Obtém um provider específico
    
    Args:
        provider_name: Nome do provider
        
    Returns:
        LLMProvider: Instância do provider
        
    Raises:
        BradaxConfigurationException: Provider não disponível
    """
    providers = get_available_providers()
    
    if provider_name not in providers:
        available_names = list(providers.keys())
        raise BradaxConfigurationException(
            message=f"Provider '{provider_name}' não disponível",
            config_key="llm_provider",
            severity=ErrorSeverity.HIGH
        )
    
    return providers[provider_name]
