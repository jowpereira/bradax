#!/usr/bin/env python3
"""
TESTE REAL COM SDK BRADAX - MÍNIMO CÓDIGO, MÁXIMO PODER
Baseado na arquitetura do ARCHITECTURE_MEMORY.md
"""

import sys
import os

# Adicionar SDK ao path
SDK_PATH = r"C:\Users\letha\OneDrive\desktop\WorkSpace\bradax\bradax-sdk\src"
sys.path.insert(0, SDK_PATH)

# Importar SDK real
from bradax.client import BradaxClient

def main():
    print("🔥 TESTE REAL COM SDK BRADAX")
    print("="*50)
    
    # Usar projeto real cadastrado
    PROJECT_TOKEN = "proj_real_001"  # Do projects.json
    
    # Cliente SDK real (ele monta os headers automaticamente)
    print(f"🔧 Criando cliente SDK com token: {PROJECT_TOKEN}")
    client = BradaxClient(
        base_url="http://localhost:8000",
        project_token=PROJECT_TOKEN
    )
    
    try:
        # Teste 1: invoke() simples
        print("\n📞 Chamada 1: invoke() - Pergunta simples")
        response1 = client.invoke(
            prompt="What is 2+2? Answer in exactly one word.",
            model="gpt-4o-mini",
            max_tokens=5
        )
        
        print(f"✅ Response 1: {response1}")
        
        # Teste 2: invoke() com mais context
        print("\n📞 Chamada 2: invoke() - Context maior")
        response2 = client.invoke(
            prompt="Explain what Python is in 10 words maximum.",
            model="gpt-4o-mini", 
            max_tokens=15
        )
        
        print(f"✅ Response 2: {response2}")
        
        print("\n🎉 SUCESSO! SDK funcionou perfeitamente!")
        print("📊 Verifique agora os dados de auditoria em:")
        print("   - C:\\...\\bradax\\data\\telemetry.json")
        print("   - C:\\...\\bradax\\data\\interactions.json")
        print("   - C:\\...\\bradax\\data\\guardrail_events.json")
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        print("\n🔍 Detalhes do erro:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensagem: {str(e)}")
        
        # Se houver atributos específicos do SDK
        if hasattr(e, 'status_code'):
            print(f"   Status Code: {e.status_code}")
        if hasattr(e, 'response'):
            print(f"   Response: {e.response}")

if __name__ == "__main__":
    main()
