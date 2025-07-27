#!/usr/bin/env python3
"""
Exemplo de uso corporativo completo
Demonstra integração real com o bradax SDK.
"""

import asyncio
import os
import sys
from pathlib import Path

# Adicionar path do SDK
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

async def exemplo_chatbot():
    """Exemplo de chatbot corporativo"""
    
    print("🤖 Exemplo - Chatbot Corporativo")
    print("=" * 40)
    
    try:
        from bradax import CorporateBradaxClient
        
        # Configurar cliente
        client = CorporateBradaxClient(
            project_token="proj_atendimento_chatbot_seguros_2025_exemplo",
            broker_url=os.getenv("BRADAX_BROKER_URL", "http://localhost:8001")
        )
        
        print(f"🏢 Cliente configurado para: {client.project_token}")
        print(f"💰 Orçamento mensal: ${client.config.budget_monthly_usd}")
        
        # Simular perguntas de clientes
        perguntas = [
            "O que é um seguro de vida?",
            "Quais são os benefícios do Seguro Auto Bradesco?",
            "Como funciona o seguro residencial?"
        ]
        
        for i, pergunta in enumerate(perguntas, 1):
            print(f"\n🔸 Pergunta {i}: {pergunta}")
            
            try:
                response = await client.invoke_llm(
                    model="gpt-4.1-nano",
                    messages=[
                        {
                            "role": "system", 
                            "content": "Você é um assistente especializado em seguros Bradesco. Seja informativo e profissional."
                        },
                        {
                            "role": "user", 
                            "content": pergunta
                        }
                    ],
                    parameters={
                        "max_tokens": 300,
                        "temperature": 0.3
                    }
                )
                
                resposta = response['choices'][0]['message']['content']
                metadata = response['_bradax_metadata']
                
                print(f"🤖 Resposta: {resposta[:100]}...")
                print(f"💰 Custo: ${metadata['cost_usd']:.6f}")
                print(f"⚡ Latência: {metadata['latency_ms']}ms")
                print(f"🔍 Trace ID: {metadata['trace_id']}")
                
            except Exception as e:
                print(f"❌ Erro na pergunta {i}: {e}")
        
        print("\n✅ Exemplo de chatbot concluído!")
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")

async def exemplo_analise_documento():
    """Exemplo de análise de documento"""
    
    print("\n📄 Exemplo - Análise de Documento")
    print("=" * 40)
    
    try:
        from bradax import CorporateBradaxClient
        
        client = CorporateBradaxClient(
            project_token="proj_juridico_analise_contratos_2025_exemplo",
            broker_url=os.getenv("BRADAX_BROKER_URL", "http://localhost:8001")
        )
        
        # Texto simulado de contrato
        contrato_texto = """
        CONTRATO DE SEGURO VIDA
        
        Segurado: João Silva
        CPF: 123.456.789-00
        Valor da Apólice: R$ 100.000,00
        Vigência: 12 meses
        Beneficiários: Maria Silva (esposa), Pedro Silva (filho)
        
        Coberturas:
        - Morte natural ou acidental
        - Invalidez permanente total
        - Despesas médicas hospitalares
        """
        
        print("📋 Analisando contrato de seguro...")
        
        response = await client.invoke_llm(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um especialista em análise de contratos de seguro. Extraia e organize as informações principais."
                },
                {
                    "role": "user",
                    "content": f"Analise este contrato e extraia as informações principais:\n\n{contrato_texto}"
                }
            ],
            parameters={
                "max_tokens": 800,
                "temperature": 0.1
            }
        )
        
        analise = response['choices'][0]['message']['content']
        metadata = response['_bradax_metadata']
        
        print(f"📊 Análise:\n{analise}")
        print(f"\n💰 Custo da análise: ${metadata['cost_usd']:.6f}")
        print(f"🔍 Trace ID: {metadata['trace_id']}")
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")

async def main():
    """Executar todos os exemplos"""
    
    print("🏢 bradax SDK - Exemplos Corporativos")
    print("=" * 50)
    
    # Verificar se broker está configurado
    broker_url = os.getenv("BRADAX_BROKER_URL", "http://localhost:8001")
    print(f"🌐 Broker URL: {broker_url}")
    
    if broker_url == "http://localhost:8001":
        print("⚠️ Usando broker local. Certifique-se que está rodando em localhost:8001")
    
    # Executar exemplos
    await exemplo_chatbot()
    await exemplo_analise_documento()
    
    print("\n🎉 Todos os exemplos concluídos!")
    print("💡 Para usar em produção, configure BRADAX_BROKER_URL")

if __name__ == "__main__":
    asyncio.run(main())
