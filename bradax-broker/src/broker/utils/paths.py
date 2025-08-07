"""
Sistema de Paths Centralizados - Bradax
Garante que SEMPRE use /bradax/data/ como única pasta de dados.
"""
import os
from pathlib import Path
from typing import Optional

def get_project_root() -> Path:
    """
    Detecta a pasta raiz do projeto Bradax de forma robusta.
    Sempre retorna o diretório /bradax/ independente de onde for executado.
    """
    # Começar do arquivo atual
    current_path = Path(__file__).resolve()

    # Subir na hierarquia procurando por todas as pastas chamadas 'bradax'
    bradax_dirs = [parent for parent in current_path.parents if parent.name == "bradax"]
    if bradax_dirs:
        # Retorna a mais alta (mais próxima da raiz)
        return bradax_dirs[-1]

    # Fallback: usar variável de ambiente se configurada
    env_root = os.getenv("BRADAX_PROJECT_ROOT")
    if env_root and Path(env_root).exists():
        return Path(env_root)

    # Se nada funcionar, ERRO explícito (não cria pasta data em local errado)
    raise RuntimeError("Raiz do projeto Bradax não encontrada. Execute o script a partir do projeto ou defina BRADAX_PROJECT_ROOT.")

def get_data_dir() -> Path:
    """Retorna pasta de dados centralizada SEMPRE em /bradax/data/"""
    root = get_project_root()
    data_dir = root / "data"
    
    # Não criar automaticamente. Se não existir, lançar erro.
    if not data_dir.exists():
        raise RuntimeError(f"Diretório de dados não encontrado: {data_dir}")
    return data_dir

def get_logs_dir() -> Path:
    """Retorna pasta de logs centralizada em /bradax/logs/"""
    root = get_project_root()
    logs_dir = root / "logs"
    
    # Criar se não existir
    logs_dir.mkdir(exist_ok=True)
    
    return logs_dir

# Para debug - mostrar paths detectados
if __name__ == "__main__":
    print(f"🏠 Project Root: {get_project_root()}")
    print(f"📁 Data Dir: {get_data_dir()}")
    print(f"📋 Logs Dir: {get_logs_dir()}")
    print(f"✅ Data dir exists: {get_data_dir().exists()}")
