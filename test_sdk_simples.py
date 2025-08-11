#!/usr/bin/env python3
"""
TESTE SDK SIMPLES - Apenas testar o constructor e conexão básica
"""

import sys
import os

# Adicionar SDK ao path
SDK_PATH = r"C:\Users\letha\OneDrive\desktop\WorkSpace\bradax\bradax-sdk\src"
sys.path.insert(0, SDK_PATH)

def main():
    print("🔥 TESTE SDK SIMPLES - CONSTRUTOR")
    print("="*40)
    
    try:
        # Importar SDK
        from bradax.client import BradaxClient
        print("✅ SDK importado com sucesso")
        
        # Criar cliente com configurações mínimas
        print("\n🔧 Criando cliente SDK...")
        client = BradaxClient(
            project_token="proj_real_001",
            broker_url="http://localhost:8000",
            verbose=True
        )
        print("✅ Cliente criado com sucesso")
        
        # Verificar se o cliente tem os métodos esperados
        print(f"✅ Cliente tem método invoke: {hasattr(client, 'invoke')}")
        print(f"✅ Cliente tem broker_url: {getattr(client, 'broker_url', 'N/A')}")
        
        # Testar uma chamada simples (se servidor estiver online)
        print("\n📞 Testando chamada invoke...")
        
        result = client.invoke(
            "Hello, what is 2+2?",
            config={"model": "gpt-4o-mini", "max_tokens": 20}
        )
        
        print(f"✅ SUCESSO! Resposta: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        print(f"   Tipo: {type(e).__name__}")
        import traceback
        print(f"   Stack: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = main()
    print("="*40)
    if success:
        print("🎉 TESTE PASSOU!")
    else:
        print("❌ TESTE FALHOU!")
