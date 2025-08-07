"""
Configuração de Logging para SDK Bradax.
Integra com configuração centralizada do sistema.
"""
import logging
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class BradaxSDKLogger:
    """Logger estruturado para o SDK Bradax com compatibilidade legacy."""
    
    def __init__(self, name: str, level: str = "INFO", verbose: bool = False):
        """
        Inicializa o logger estruturado.
        
        Args:
            name: Nome do logger (ex: 'bradax.sdk.client', 'bradax.sdk.telemetry')
            level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            verbose: Se True, também faz output para console
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self.verbose = verbose
        
        # Evitar duplicação de handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Configura handlers baseado na configuração centralizada."""
        # Detectar ambiente
        environment = os.getenv("BRADAX_ENVIRONMENT", "development").lower()
        
        # Configuração baseada no ambiente
        if environment == "production":
            # Produção: apenas logs críticos para arquivo
            if self.verbose:  # Respeitar configuração verbose para console
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(self._get_formatter(structured=True))
                self.logger.addHandler(console_handler)
        else:
            # Desenvolvimento/Testing: console sempre se verbose
            if self.verbose:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(self._get_formatter(structured=False))
                self.logger.addHandler(console_handler)
    
    def _get_formatter(self, structured: bool = False) -> logging.Formatter:
        """Retorna formatter apropriado."""
        if structured:
            return StructuredFormatter()
        else:
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
    
    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log de debug com dados estruturados."""
        self._log_structured(logging.DEBUG, message, extra_data)
    
    def info(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log de informação com dados estruturados."""
        self._log_structured(logging.INFO, message, extra_data)
    
    def warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log de warning com dados estruturados."""
        self._log_structured(logging.WARNING, message, extra_data)
    
    def error(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log de erro com dados estruturados."""
        self._log_structured(logging.ERROR, message, extra_data)
    
    def critical(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log crítico com dados estruturados."""
        self._log_structured(logging.CRITICAL, message, extra_data)
    
    def _log_structured(self, level: int, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Método interno para logging estruturado."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message": message
        }
        
        if extra_data:
            log_entry.update(extra_data)
        
        # Log com dados estruturados como extra
        self.logger.log(level, message, extra={"structured_data": json.dumps(log_entry)})


class StructuredFormatter(logging.Formatter):
    """Formatter para logs estruturados JSON (versão simplificada para SDK)."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Formata log como JSON estruturado."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": "bradax.sdk",
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Adicionar dados estruturados extras
        if hasattr(record, 'structured_data'):
            try:
                extra_data = json.loads(record.structured_data)
                log_entry.update(extra_data)
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Adicionar informações de exceção
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


# Instância global para o SDK
sdk_logger = BradaxSDKLogger("bradax.sdk", level="INFO")
