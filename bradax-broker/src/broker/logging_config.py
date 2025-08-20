"""
Configuração Centralizada de Logging - Sistema Bradax
Unifica logging entre SDK e Broker com configurações por ambiente.
"""
import logging
import logging.handlers
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union
from enum import Enum


class LogLevel(Enum):
    """Níveis de log padronizados."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Environment(Enum):
    """Ambientes suportados."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class BradaxLogConfig:
    """Configuração centralizada de logging para todo o sistema Bradax."""

    # Configurações por ambiente
    ENV_CONFIGS = {
        Environment.DEVELOPMENT: {
            "level": LogLevel.DEBUG,
            "console_enabled": True,
            "file_enabled": True,
            "structured_logs": False,
            "max_file_size": "10MB",
            "backup_count": 3
        },
        Environment.TESTING: {
            "level": LogLevel.INFO,
            "console_enabled": False,
            "file_enabled": True,
            "structured_logs": True,
            "max_file_size": "5MB",
            "backup_count": 2
        },
        Environment.STAGING: {
            "level": LogLevel.INFO,
            "console_enabled": True,
            "file_enabled": True,
            "structured_logs": True,
            "max_file_size": "50MB",
            "backup_count": 5
        },
        Environment.PRODUCTION: {
            "level": LogLevel.WARNING,
            "console_enabled": False,
            "file_enabled": True,
            "structured_logs": True,
            "max_file_size": "100MB",
            "backup_count": 10
        }
    }

    def __init__(self,
                 environment: Union[Environment, str] = None,
                 log_dir: Optional[str] = None,
                 service_name: str = "bradax"):
        """
        Inicializa configuração de logging.

        Args:
            environment: Ambiente (development, testing, staging, production)
            log_dir: Diretório para logs (usa padrão se None)
            service_name: Nome do serviço (bradax.sdk, bradax.broker, etc)
        """
        # Detectar ambiente
        if environment is None:
            # Unificado: usar apenas BRADAX_ENV
            env_str = os.getenv("BRADAX_ENV", "development").lower()
            try:
                environment = Environment(env_str)
            except ValueError:
                environment = Environment.DEVELOPMENT
        elif isinstance(environment, str):
            environment = Environment(environment.lower())

        self.environment = environment
        self.service_name = service_name
        self.config = self.ENV_CONFIGS[environment].copy()

        # Configurar diretório de logs
        if log_dir is None:
            log_dir = self._get_default_log_dir()
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Request ID para correlação (thread-local)
        self._request_id = None

    def _get_default_log_dir(self) -> str:
        """Calcula diretório padrão de logs baseado na estrutura do projeto."""
        current_dir = Path(__file__).resolve()
        project_root = None

        # Subir na hierarquia até encontrar pasta "bradax"
        for parent in current_dir.parents:
            if parent.name == "bradax":
                project_root = parent
                break

        if not project_root:
            # Fallback para diretório atual
            return "logs"

        return str(project_root / "logs")

    def _parse_file_size(self, size_str: str) -> int:
        """Converte string de tamanho (ex: '10MB') para bytes."""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Cria logger configurado com handlers apropriados.

        Args:
            name: Nome do logger (ex: 'bradax.sdk.client')

        Returns:
            Logger configurado
        """
        logger = logging.getLogger(name)

        # Evitar duplicação de handlers
        if logger.handlers:
            return logger

        # Configurar nível
        level = getattr(logging, self.config["level"].value)
        logger.setLevel(level)

        # Handler para console
        if self.config["console_enabled"]:
            console_handler = self._create_console_handler()
            logger.addHandler(console_handler)

        # Handler para arquivo
        if self.config["file_enabled"]:
            file_handler = self._create_file_handler(name)
            logger.addHandler(file_handler)

        # Prevenir propagação para evitar duplicação
        logger.propagate = False

        return logger

    def _create_console_handler(self) -> logging.StreamHandler:
        """Cria handler para console."""
        handler = logging.StreamHandler(sys.stdout)

        if self.config["structured_logs"]:
            formatter = StructuredFormatter(
                service_name=self.service_name,
                environment=self.environment.value
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

        handler.setFormatter(formatter)
        return handler

    def _create_file_handler(self, logger_name: str) -> logging.handlers.RotatingFileHandler:
        """Cria handler para arquivo com rotação."""
        # Arquivo baseado no nome do logger e data
        log_filename = f"{logger_name.replace('.', '_')}_{datetime.now().strftime('%Y%m%d')}.log"
        log_path = self.log_dir / log_filename

        max_bytes = self._parse_file_size(self.config["max_file_size"])
        backup_count = self.config["backup_count"]

        handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )

        if self.config["structured_logs"]:
            formatter = StructuredFormatter(
                service_name=self.service_name,
                environment=self.environment.value
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

        handler.setFormatter(formatter)
        return handler

    def set_request_id(self, request_id: str):
        """Define request_id para correlação de logs."""
        self._request_id = request_id

    def get_request_id(self) -> Optional[str]:
        """Retorna request_id atual."""
        return self._request_id


class StructuredFormatter(logging.Formatter):
    """Formatter para logs estruturados JSON usando schema padronizado."""

    def __init__(self, service_name: str, environment: str):
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        """Formata log como JSON estruturado seguindo schema padrão."""
        from .log_schema import BradaxLogSchema

        # Criar log seguindo schema obrigatório
        log_entry = BradaxLogSchema(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=record.levelname,
            service=self.service_name,
            logger=record.name,
            message=record.getMessage(),
            module=record.module,
            function=record.funcName,
            line=record.lineno,
            environment=self.environment
        )

        # Adicionar request_id se disponível
        if hasattr(record, 'request_id') and record.request_id:
            log_entry.request_id = record.request_id

        # Adicionar dados estruturados extras do record
        if hasattr(record, 'structured_data'):
            try:
                extra_data = json.loads(record.structured_data)

                # Mapear campos estruturados para schema
                if 'user_id' in extra_data:
                    log_entry.user_id = extra_data['user_id']
                if 'project_id' in extra_data:
                    log_entry.project_id = extra_data['project_id']
                if 'operation' in extra_data:
                    log_entry.operation = extra_data['operation']
                if 'operation_duration_ms' in extra_data:
                    log_entry.operation_duration_ms = extra_data['operation_duration_ms']
                if 'error_code' in extra_data:
                    log_entry.error_code = extra_data['error_code']
                if 'error_details' in extra_data:
                    log_entry.error_details = extra_data['error_details']
                if 'performance_metrics' in extra_data:
                    log_entry.performance_metrics = extra_data['performance_metrics']

                # Dados não mapeados vão para custom_data
                custom_fields = {k: v for k, v in extra_data.items()
                               if k not in ['user_id', 'project_id', 'operation', 'operation_duration_ms',
                                          'error_code', 'error_details', 'performance_metrics']}
                if custom_fields:
                    log_entry.custom_data = custom_fields

            except (json.JSONDecodeError, TypeError):
                # Se não conseguir fazer parse, adiciona como custom_data
                log_entry.custom_data = {"structured_data_raw": str(record.structured_data)}

        # Adicionar informações de exceção
        if record.exc_info:
            log_entry.error_details = {
                "exception": self.formatException(record.exc_info),
                "exception_type": record.exc_info[0].__name__ if record.exc_info[0] else None
            }

        return log_entry.to_json()


# Instância global de configuração
_global_config: Optional[BradaxLogConfig] = None

def get_log_config() -> BradaxLogConfig:
    """Retorna configuração global de logging."""
    global _global_config
    if _global_config is None:
        _global_config = BradaxLogConfig()
    return _global_config

def configure_logging(environment: Union[Environment, str] = None,
                     log_dir: Optional[str] = None,
                     service_name: str = "bradax") -> BradaxLogConfig:
    """
    Configura logging global do sistema.

    Args:
        environment: Ambiente de execução
        log_dir: Diretório para logs
        service_name: Nome do serviço

    Returns:
        Configuração aplicada
    """
    global _global_config
    _global_config = BradaxLogConfig(environment, log_dir, service_name)
    return _global_config

def get_logger(name: str) -> logging.Logger:
    """
    Obtém logger configurado.

    Args:
        name: Nome do logger

    Returns:
        Logger configurado
    """
    config = get_log_config()
    return config.get_logger(name)


# Instâncias globais para compatibilidade com código anterior
broker_logger = get_logger("bradax.broker")
storage_logger = get_logger("bradax.storage")
