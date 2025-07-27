#!/usr/bin/env python3
"""
Teste rápido do bradax SDK
Verifica se SDK está funcionando corretamente.
"""

import asyncio
import sys
from pathlib import Path

# Adicionar path do SDK
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

async def quick_test():
    """Teste rápido de funcionalidade básica"""
    
    print("🧪 Teste Rápido - bradax SDK")
    print("=" * 40)
    
    try:
        # 1. Importar SDK
        print("1️⃣ Importando bradax SDK...")
        from bradax import CorporateBradaxClient
        print("   ✅ SDK importado com sucesso!")
        
        # 2. Instanciar cliente (sem conectar ainda)
        print("\n2️⃣ Criando cliente corporativo...")
        client = CorporateBradaxClient(
            project_token="proj_test_demo_quicktest_2025_testkey123",
            broker_url="http://localhost:8001"  # Broker local para teste
        )
        print("   ✅ Cliente criado com sucesso!")
        print(f"   📋 Projeto: {client.project_token}")
        print(f"   🌐 Broker: {client.broker_url}")
        
        # 3. Verificar configurações
        print("\n3️⃣ Verificando configurações...")
        print(f"   💰 Orçamento: ${client.config.budget_monthly_usd}")
        print(f"   🎯 Modelos: {', '.join(client.config.models_allowed)}")
        print(f"   🔢 Max tokens: {client.config.max_tokens_per_request}")
        print(f"   ⏱️ Max req/hour: {client.config.max_requests_per_hour}")
        
        # 4. Teste de validação (sem chamar API)
        print("\n4️⃣ Testando validações...")
        
        # Teste validação de modelo
        try:
            client._validate_model("gpt-4.1-nano")
            print("   ✅ Validação de modelo: OK")
        except Exception as e:
            print(f"   ❌ Validação de modelo: {e}")
        
        # Teste validação de parâmetros
        try:
            client._validate_request_params(parameters={"max_tokens": 500})
            print("   ✅ Validação de parâmetros: OK")
        except Exception as e:
            print(f"   ❌ Validação de parâmetros: {e}")
        
        print("\n🎉 Teste rápido concluído com sucesso!")
        print("💡 Para testar com API real, certifique-se que o broker está rodando.")
        
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        print("💡 Verifique se o SDK está instalado corretamente")
        
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(quick_test())
