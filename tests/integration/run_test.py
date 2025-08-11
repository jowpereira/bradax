"""
Script de execução do Bradax Broker - Versão para Testes
Sem emojis para compatibilidade Windows
"""
import os
import sys
from pathlib import Path
import uvicorn

# Adicionar src ao path
src_path = Path(__file__).parent.parent / "bradax-broker" / "src"
sys.path.insert(0, str(src_path))

def main():
    """Função principal"""
    
    # Configurar environment para teste
    os.environ["BRADAX_JWT_SECRET"] = "test_jwt_secret_2025"
    os.environ["BRADAX_OPENAI_API_KEY"] = "test_openai_key"
    
    print("Iniciando Bradax Broker para testes...")
    print(f"Diretorio de trabalho: {Path.cwd()}")
    print(f"JWT_SECRET definido: SIM")
    print(f"OpenAI configurado: SIM (teste)")
    
    # Configuração do servidor
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "localhost")
    
    print(f"Servidor: {host}:{port}")
    print("Iniciando servidor uvicorn...")
    
    # Importar app
    try:
        from broker.main import app
        print("App importado com sucesso")
        
        # Iniciar servidor
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=False,
            log_level="info",
            access_log=True
        )
        
    except Exception as e:
        print(f"ERRO ao iniciar: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
