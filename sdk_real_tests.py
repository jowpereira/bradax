#!/usr/bin/env python3
"""
Chamadas SDK REAIS para auditoria com projeto cadastrado
Executa via HTTP direto com headers corretos de telemetria
"""

import requests
import json
import uuid
import time
from datetime import datetime

def make_real_sdk_call(prompt, correlation_id, project_id="proj_real_001"):
    """Fazer chamada real usando projeto cadastrado"""
    
    payload = {
        "operation": "chat",
        "model": "gpt-4o-mini",  # Modelo disponível na OpenAI
        "payload": {
            "prompt": prompt,
            "model": "gpt-4o-mini",
            "max_tokens": 100,
            "temperature": 0.7,
            "project_id": project_id
        },
        "correlation_id": correlation_id,
        "project_id": project_id
    }
    
    # Headers SDK completos para telemetria
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer hash_proj1",  # API key do projeto
        "User-Agent": "bradax-sdk/1.0.0",
        "x-bradax-sdk-version": "1.0.0",
        "x-bradax-machine-fingerprint": "8e219290de7aa69a",
        "x-bradax-session-id": f"session-{correlation_id}",
        "x-bradax-telemetry-enabled": "true",
        "x-bradax-environment": "production",
        "x-bradax-platform": "win32",
        "x-bradax-python-version": "3.10.0",
        "x-bradax-request-timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    print(f"🚀 CHAMADA SDK - {prompt[:30]}...")
    print(f"   📋 Project: {project_id}")
    print(f"   🆔 Correlation: {correlation_id}")
    
    try:
        start_time = time.time()
        response = requests.post(
            "http://localhost:8000/api/v1/llm/invoke",
            json=payload,
            headers=headers,
            timeout=60  # Timeout maior para OpenAI real
        )
        end_time = time.time()
        
        print(f"   ⏱️  Tempo: {end_time - start_time:.2f}s")
        print(f"   📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: {data.get('success', False)}")
            print(f"   🎯 Model: {data.get('model_used', 'N/A')}")
            print(f"   📝 Response: {str(data.get('response', ''))[:100]}...")
            print(f"   🔒 Guardrails: {data.get('guardrails_attempted', 0)}")
            print(f"   🆔 Request ID: {data.get('request_id', 'N/A')}")
            return True, data
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
            return False, None
            
    except Exception as e:
        print(f"   💥 Exception: {e}")
        return False, None

def main():
    print("🔥 TESTES SDK REAIS - AUDITORIA COMPLETA")
    print("="*60)
    
    # Lista de testes variados
    test_cases = [
        "What is 2+2? Answer in one sentence.",
        "Explain Python in 20 words.",
        "What is the capital of Brazil?",
        "Write a haiku about programming.",
        "List 3 benefits of cloud computing."
    ]
    
    results = []
    
    for i, prompt in enumerate(test_cases, 1):
        print(f"\n{'='*20} TESTE {i} {'='*20}")
        correlation_id = f"test-{i:03d}-{str(uuid.uuid4())[:8]}"
        
        success, data = make_real_sdk_call(prompt, correlation_id)
        results.append({
            'test': i,
            'success': success,
            'correlation_id': correlation_id,
            'data': data
        })
        
        # Aguardar entre chamadas
        print("   ⏳ Aguardando 3s...")
        time.sleep(3)
    
    # Sumário
    print(f"\n{'='*60}")
    print("📊 SUMÁRIO DOS TESTES")
    print("="*60)
    
    successful = sum(1 for r in results if r['success'])
    print(f"✅ Sucessos: {successful}/{len(results)}")
    
    for r in results:
        status = "✅" if r['success'] else "❌"
        print(f"   {status} Teste {r['test']}: {r['correlation_id']}")
    
    print(f"\n🎯 Verifique os dados de auditoria em: C:\\Users\\letha\\OneDrive\\desktop\\WorkSpace\\bradax\\data\\")

if __name__ == "__main__":
    main()
