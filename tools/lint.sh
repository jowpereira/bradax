#!/bin/bash
# Script para linting e formatação de código

set -e

echo "🧹 Executando linting e formatação..."

# Ativar ambiente virtual se existir
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Função para lint de um pacote
lint_package() {
    local package_name=$1
    local package_path=$2
    
    echo "📋 Linting $package_name..."
    cd "$package_path"
    
    # Black (formatação)
    echo "  🎨 Formatando com Black..."
    black src/ tests/ --check --diff
    
    # Ruff (linting)
    echo "  🔍 Analisando com Ruff..."
    ruff check src/ tests/
    
    # MyPy (type checking)
    echo "  🏷️ Verificando tipos com MyPy..."
    mypy src/
    
    cd - > /dev/null
}

# Lint do SDK
lint_package "bradax-sdk" "packages/bradax-sdk"

# Lint do Broker
lint_package "bradax-broker" "packages/bradax-broker"

# Verificar arquivos compartilhados
echo "📋 Verificando arquivos compartilhados..."
if [ -d "shared" ]; then
    black shared/ --check --diff
    ruff check shared/
fi

# Verificar scripts de tools
echo "📋 Verificando scripts de ferramentas..."
shellcheck tools/*.sh || echo "⚠️ ShellCheck não encontrado - pule esta verificação"

echo ""
echo "✅ Linting concluído com sucesso!"
echo ""
echo "💡 Para corrigir automaticamente:"
echo "   ./tools/format.sh"
