"""
Teste Simples: Verificar se run.py funciona
===========================================

Apenas testa se o run.py inicia o servidor corretamente.
"""

import subprocess
import sys
import time
import requests
from pathlib import Path

def test_run_py():
    """Testa se run.py funciona"""
    
    print("🚀 Testando run.py do bradax-broker...")
    
    # Paths
    project_root = Path(__file__).parent.parent.parent
    broker_dir = project_root / "bradax-broker"
    run_py = broker_dir / "run.py"
    
    print(f"📁 Projeto: {project_root}")
    print(f"📁 Broker: {broker_dir}")
    print(f"📄 run.py: {run_py}")
    
    if not run_py.exists():
        print("❌ run.py não encontrado!")
        return False
    
    # Environment
    import os
    env = os.environ.copy()
    env["BRADAX_JWT_SECRET"] = "test_secret_123"
    env["BRADAX_OPENAI_API_KEY"] = "test_key_123"
    
    # Iniciar processo
    try:
        print("🚀 Iniciando run.py...")
        process = subprocess.Popen(
            [sys.executable, str(run_py)],
            env=env,
            cwd=str(broker_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print(f"📝 Processo iniciado (PID: {process.pid})")
        
        # Aguardar um pouco
        print("⏳ Aguardando 10 segundos...")
        time.sleep(10)
        
        # Verificar se ainda está rodando
        if process.poll() is None:
            print("✅ Processo ainda rodando")
            
            # Tentar acessar localhost:8000
            try:
                response = requests.get("http://localhost:8000/health", timeout=5)
                print(f"📥 Response: {response.status_code}")
                
                if response.status_code == 200:
                    print("🎉 HUB FUNCIONANDO!")
                    result = True
                else:
                    print(f"⚠️ Hub responde mas status: {response.status_code}")
                    result = False
                    
            except Exception as e:
                print(f"❌ Erro ao acessar Hub: {e}")
                result = False
        else:
            print("❌ Processo terminou")
            result = False
            
            # Mostrar output
            stdout, stderr = process.communicate()
            if stdout:
                print(f"STDOUT:\n{stdout}")
            if stderr:
                print(f"STDERR:\n{stderr}")
        
        # Parar processo
        print("🛑 Parando processo...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            
        return result
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return False


if __name__ == "__main__":
    success = test_run_py()
    print(f"\n🏁 Resultado: {'SUCESSO' if success else 'FALHA'}")
