#!/usr/bin/env python3
"""
Script para executar o bradax Broker

Uso:
    python run_broker.py
"""

import sys
import os

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Importar e executar o broker
if __name__ == "__main__":
    try:
        from broker.main import app
        import uvicorn
        from broker.config import settings
        
        print(f"🚀 Iniciando bradax Broker em {settings.BRADAX_BROKER_HOST}:{settings.BRADAX_BROKER_PORT}")
        print(f"🔧 Modo DEBUG: {settings.BRADAX_BROKER_DEBUG}")
        print(f"🌐 CORS Origins: {settings.BRADAX_BROKER_CORS_ORIGINS}")
        
        uvicorn.run(
            "broker.main:app",
            host=settings.BRADAX_BROKER_HOST,
            port=settings.BRADAX_BROKER_PORT,
            reload=False,  # Desabilitado para evitar warning
            log_level=settings.BRADAX_BROKER_LOG_LEVEL.lower()
        )
        
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro ao iniciar broker: {e}")
        sys.exit(1)
