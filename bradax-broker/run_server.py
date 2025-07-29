#!/usr/bin/env python3
"""
Script para rodar o hub_ia (broker) localmente para testes.
"""
import sys
import os

# Adiciona o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import uvicorn

if __name__ == "__main__":
    uvicorn.run("broker.main:app", host="0.0.0.0", port=8000, reload=True)
