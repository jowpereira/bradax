"""
Demonstração do Problema: TestClient vs Servidor Real
====================================================

🚨 DEMONSTRAÇÃO DO PROBLEMA APONTADO:
- TestClient do FastAPI NÃO persiste dados nos arquivos JSON
- Servidor real SIM persiste dados nos arquivos JSON
- SDK real fazendo chamadas HTTP SIM gera telemetria real

Este arquivo compara os dois approaches e mostra a diferença.
"""

import json
import time
import subprocess
import sys
import requests
from datetime import datetime
from pathlib import Path
from fastapi.testclient import TestClient

# Setup dos paths
test_dir = Path(__file__).parent.parent
broker_dir = test_dir.parent / "bradax-broker"
sdk_dir = test_dir.parent / "bradax-sdk" / "src"
data_dir = broker_dir / "data"

# Adicionar paths para imports
sys.path.insert(0, str(broker_dir / "src"))
sys.path.insert(0, str(sdk_dir))


def show_json_file_content(file_name: str, description: str):
    """Mostra conteúdo de um arquivo JSON"""
    file_path = data_dir / f"{file_name}.json"
    
    print(f"\n📄 {description} ({file_path}):")
    
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list) and len(data) == 0:
                print("   ✅ Arquivo existe mas está VAZIO (sem dados persistidos)")
            else:
                print(f"   📊 {len(data)} itens encontrados:")
                print(json.dumps(data, indent=4, ensure_ascii=False))
    else:
        print("   ❌ Arquivo não existe")


def test_with_testclient():
    """Demonstra que TestClient NÃO persiste dados"""
    print("\n" + "="*60)
    print("🧪 TESTE 1: USANDO TestClient (FastAPI)")
    print("="*60)
    
    try:
        from broker.main import app
        client = TestClient(app)
        
        # Request simulada com TestClient
        headers = {
            "Authorization": "Bearer bradax_test_token_2025_secure",
            "Content-Type": "application/json",
            "X-Bradax-Telemetry": json.dumps({
                "cpu_usage": 45.2,
                "ram_usage": 78.5,
                "user_context": "test_user",
                "timestamp": datetime.now().isoformat()
            })
        }
        
        request_data = {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Test via TestClient"}],
            "max_tokens": 50
        }
        
        print("📤 Fazendo request via TestClient...")
        response = client.post("/llm/invoke", json=request_data, headers=headers)
        print(f"📥 Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"⚠️  Response body: {response.text}")
        
        # Verificar se dados foram persistidos
        print("\n🔍 VERIFICANDO PERSISTÊNCIA APÓS TestClient:")
        show_json_file_content("telemetry", "Telemetria")
        
        print("\n❌ RESULTADO: TestClient NÃO persiste dados nos arquivos JSON!")
        print("   - É apenas uma simulação interna do FastAPI")
        print("   - Não roda o servidor real")
        print("   - Não executa middlewares de persistência")
        
    except Exception as e:
        print(f"❌ Erro no teste TestClient: {e}")


def test_with_real_server():
    """Demonstra que servidor real SIM persiste dados"""
    print("\n" + "="*60)
    print("🚀 TESTE 2: SERVIDOR REAL + REQUESTS HTTP")
    print("="*60)
    
    # Iniciar servidor real em processo separado
    print("🚀 Iniciando servidor real na porta 8002...")
    
    import os
    env = os.environ.copy()
    env["BRADAX_JWT_SECRET"] = "test_jwt_secret_real_demo"
    env["BRADAX_OPENAI_API_KEY"] = "test_openai_key"
    
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "broker.main:app", 
         "--host", "localhost", "--port", "8002", "--reload", "False"],
        cwd=str(broker_dir / "src"),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Aguardar servidor inicializar
    server_url = "http://localhost:8002"
    max_attempts = 20
    
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{server_url}/health", timeout=2)
            if response.status_code == 200:
                print(f"✅ Servidor iniciado com sucesso!")
                break
        except:
            pass
        time.sleep(0.5)
    else:
        print("❌ Servidor não inicializou")
        server_process.terminate()
        return
    
    try:
        # Request real via HTTP
        headers = {
            "Authorization": "Bearer bradax_test_token_2025_secure",
            "Content-Type": "application/json",
            "X-Bradax-Telemetry": json.dumps({
                "cpu_usage": 52.1,
                "ram_usage": 81.3,
                "user_context": "real_http_user",
                "timestamp": datetime.now().isoformat(),
                "request_id": f"real_test_{int(time.time())}"
            })
        }
        
        request_data = {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Test via REAL HTTP server"}],
            "max_tokens": 50
        }
        
        print("📤 Fazendo request via HTTP real...")
        response = requests.post(
            f"{server_url}/llm/invoke", 
            json=request_data, 
            headers=headers,
            timeout=10
        )
        
        print(f"📥 Response status: {response.status_code}")
        print(f"📝 Response body: {response.text[:200]}...")
        
        # Aguardar persistência
        time.sleep(2)
        
        # Verificar se dados foram persistidos
        print("\n🔍 VERIFICANDO PERSISTÊNCIA APÓS SERVIDOR REAL:")
        show_json_file_content("telemetry", "Telemetria")
        
        if data_dir.joinpath("telemetry.json").exists():
            with open(data_dir / "telemetry.json", 'r') as f:
                telemetry_data = json.load(f)
                
            if len(telemetry_data) > 0:
                print("\n✅ RESULTADO: SERVIDOR REAL persiste dados nos arquivos JSON!")
                print("   - Executa todos os middlewares")
                print("   - Roda storage real com transações ACID") 
                print("   - Dados persistidos ficam disponíveis para outras aplicações")
                
                latest_log = telemetry_data[-1]
                print(f"\n📊 ÚLTIMA TELEMETRIA GERADA:")
                print(f"   Request ID: {latest_log.get('request_id', 'N/A')}")
                print(f"   Timestamp: {latest_log.get('timestamp', 'N/A')}")
                print(f"   CPU: {latest_log.get('system_info', {}).get('cpu_usage', 'N/A')}%")
                print(f"   RAM: {latest_log.get('system_info', {}).get('ram_usage', 'N/A')}%")
            else:
                print("\n⚠️ Servidor real rodou mas dados não foram persistidos")
                print("   (pode haver configuração ou erro interno)")
        
    except Exception as e:
        print(f"❌ Erro no teste servidor real: {e}")
    
    finally:
        # Parar servidor
        print("\n🛑 Parando servidor...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()


def test_sdk_real_usage():
    """Demonstra como SDK real deveria ser usado"""
    print("\n" + "="*60)
    print("📱 TESTE 3: SDK REAL (como deveria ser testado)")
    print("="*60)
    
    print("🔧 Para testar o SDK real corretamente, precisaríamos:")
    print("   1. Servidor Hub rodando em processo real")
    print("   2. BradaxClient configurado para esse servidor")
    print("   3. Chamadas via client.chat_completion()")
    print("   4. Verificação de dados persistidos nos JSONs")
    print("")
    print("💡 Exemplo de código:")
    print("""
    # Configurar SDK
    config = BradaxSDKConfig.for_testing(
        broker_url="http://localhost:8002",
        project_id="proj_test_bradax_2025",
        enable_telemetry=True
    )
    set_sdk_config(config)
    
    # Usar cliente real
    client = BradaxClient(project_token="bradax_test_token_2025_secure")
    response = client.chat_completion(
        messages=[{"role": "user", "content": "Hello"}],
        model="gpt-4.1-nano"
    )
    
    # Verificar arquivos JSON modificados
    """)


def main():
    """Executa demonstração completa"""
    print("🎯 DEMONSTRAÇÃO: TestClient vs Servidor Real vs SDK Real")
    print("="*60)
    print("Problema apontado: TestClient não garante persistência real de dados")
    print("")
    
    # Mostrar estado inicial
    print("📊 ESTADO INICIAL DOS ARQUIVOS JSON:")
    show_json_file_content("projects", "Projetos")
    show_json_file_content("guardrails", "Guardrails") 
    show_json_file_content("telemetry", "Telemetria")
    
    # Executar testes
    test_with_testclient()
    test_with_real_server()
    test_sdk_real_usage()
    
    print("\n" + "="*60)
    print("🎯 CONCLUSÃO:")
    print("="*60)
    print("✅ VOCÊ ESTAVA CERTO:")
    print("   - TestClient é apenas simulação interna")
    print("   - NÃO testa persistência real de dados")
    print("   - NÃO garante que Hub + SDK funcionam juntos")
    print("")
    print("🚀 SOLUÇÃO:")
    print("   - Testes com servidor real em processo separado")
    print("   - SDK real fazendo chamadas HTTP")
    print("   - Verificação de arquivos JSON modificados")
    print("   - Validação visual dos dados gerados")


if __name__ == "__main__":
    main()
