#!/bin/bash
# Script para executar todos os testes do projeto

set -e

echo "🧪 Executando testes do bradax..."

# Ativar ambiente virtual se existir
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Função para executar testes com cobertura
run_tests() {
    local package_name=$1
    local package_path=$2
    
    echo "📋 Testando $package_name..."
    cd "$package_path"
    
    # Executar testes com cobertura
    python -m pytest tests/ \
        --cov=src \
        --cov-report=term-missing \
        --cov-report=html:htmlcov \
        --cov-report=xml:coverage.xml \
        --junit-xml=test-results.xml \
        -v
    
    cd - > /dev/null
}

# Verificar se as dependências estão instaladas
echo "🔍 Verificando dependências..."
pip check

# Executar linting primeiro
echo "🧹 Executando linting..."
./tools/lint.sh

# Testes do SDK
run_tests "bradax-sdk" "packages/bradax-sdk"

# Testes do Broker
run_tests "bradax-broker" "packages/bradax-broker"

# Testes de integração
echo "🔗 Executando testes de integração..."
if [ -d "tests/integration" ]; then
    python -m pytest tests/integration/ -v
fi

# Gerar relatório consolidado
echo "📊 Gerando relatório consolidado..."
coverage combine packages/*/coverage.xml 2>/dev/null || true
coverage report --show-missing || true

echo ""
echo "✅ Todos os testes executados com sucesso!"
echo ""
echo "📁 Relatórios gerados:"
echo "   - packages/bradax-sdk/htmlcov/index.html"
echo "   - packages/bradax-broker/htmlcov/index.html"
echo "   - coverage.xml (relatório consolidado)"
