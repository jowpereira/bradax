#!/usr/bin/env python3
"""
Teste único para verificar se OpenAI está funcionando com chave nova
"""

import requests
import uuid

def test_single_request():
    """Teste único com chave OpenAI nova"""
    
    correlation_id = str(uuid.uuid4())[:8]
    
    payload = {
        "operation": "chat",
        "model": "gpt-4o-mini",  # Modelo que sabemos que existe
        "payload": {
            "prompt": "Say 'Hello World' in exactly 2 words.",
            "model": "gpt-4o-mini",
            "max_tokens": 10,
            "temperature": 0.1
        },
        "correlation_id": correlation_id
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-key-123",
        "User-Agent": "bradax-sdk/1.0.0",
        "x-bradax-sdk-version": "1.0.0",
        "x-bradax-machine-fingerprint": "8e219290de7aa69a",
        "x-bradax-session-id": f"session-{correlation_id}",
        "x-bradax-telemetry-enabled": "true",
        "x-bradax-environment": "testing",
        "x-bradax-platform": "win32",
        "x-bradax-python-version": "3.10.0"
    }
    
    print(f"🔍 Testando com gpt-4o-mini - correlation_id: {correlation_id}")
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/llm/invoke",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ SUCCESS: {data.get('success', False)}")
            if data.get('success'):
                print(f"📝 Response: {data.get('response', 'N/A')}")
                print(f"⚡ Time: {data.get('response_time_ms', 0)}ms")
                print(f"🔒 Guardrails: {data.get('guardrails_attempted', 0)}")
                print(f"🆔 Request ID: {data.get('request_id', 'N/A')}")
                return True
            else:
                print(f"❌ Error: {data.get('error', 'N/A')}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    print("🔥 TESTE ÚNICO COM CHAVE NOVA")
    print("="*40)
    success = test_single_request()
    print("="*40)
    if success:
        print("🎉 SUCESSO! OpenAI funcionando!")
    else:
        print("❌ FALHA! Verificar configuração.")
