"""
Script de execução do Bradax Broker
Carrega configurações do .env e inicia o servidor
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import uvicorn

# Adicionar src ao path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """Função principal"""
    # Carregar variáveis de ambiente
    env_file = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=env_file)
    
    print("🚀 Iniciando Bradax Broker...")
    print(f"📁 Diretório de trabalho: {Path.cwd()}")
    print(f"🔑 JWT_SECRET definido: {'***' if os.getenv('JWT_SECRET') else 'NÃO'}")
    print(f"🤖 OpenAI configurado: {'✅' if os.getenv('OPENAI_API_KEY', '').startswith('sk-') else '❌'}")
    
    # Importar e iniciar aplicação
    try:
        from broker.main import app
        
        # Configuração do servidor
        config = {
            "app": app,
            "host": "0.0.0.0",
            "port": 8000,
            "reload": False,  # Desabilitado para evitar conflitos em produção
            "log_level": "info"
        }
        
        print(f"🌐 Iniciando servidor em http://{config['host']}:{config['port']}")
        uvicorn.run(**config)
        
    except ImportError as e:
        print(f"❌ Erro ao importar aplicação: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro ao iniciar servidor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
