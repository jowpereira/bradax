#!/bin/bash
# Setup completo do ambiente de desenvolvimento bradax

set -e

echo "🚀 Configurando ambiente de desenvolvimento bradax..."

# Verificar dependências
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3.10+ é necessário"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker é necessário"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "❌ Git é necessário"; exit 1; }

# Verificar versão do Python
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.10"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "❌ Python 3.10+ é necessário. Versão atual: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detectado"

# Criar ambiente virtual se não existir
if [ ! -d ".venv" ]; then
    echo "📦 Criando ambiente virtual..."
    python3 -m venv .venv
fi

# Ativar ambiente virtual
source .venv/bin/activate

# Atualizar pip
echo "⬆️ Atualizando pip..."
pip install --upgrade pip setuptools wheel

# Instalar dependências de desenvolvimento
echo "📚 Instalando dependências do SDK..."
cd packages/bradax-sdk
pip install -e ".[dev,agents]"

echo "📚 Instalando dependências do Broker..."
cd ../bradax-broker
pip install -e ".[dev]"

cd ../..

# Instalar pre-commit hooks
echo "🔧 Configurando pre-commit hooks..."
pre-commit install

# Copiar arquivo de exemplo se não existir
if [ ! -f ".env" ]; then
    echo "📋 Criando arquivo .env..."
    cp .env.example .env
    echo "⚠️ Configure o arquivo .env com suas credenciais"
fi

# Gerar código gRPC
echo "🔄 Gerando código gRPC..."
./tools/generate-proto.sh

# Verificar se Docker está rodando
if ! docker info >/dev/null 2>&1; then
    echo "⚠️ Docker não está rodando. Inicie o Docker para continuar."
else
    echo "🐳 Iniciando dependências Docker..."
    docker-compose -f docker/docker-compose.deps.yml up -d
fi

echo ""
echo "✅ Ambiente de desenvolvimento configurado com sucesso!"
echo ""
echo "📋 Próximos passos:"
echo "   1. Ativar ambiente virtual: source .venv/bin/activate"
echo "   2. Configurar .env com suas credenciais"
echo "   3. Executar testes: ./tools/test.sh"
echo "   4. Iniciar desenvolvimento: docker-compose up -d"
echo ""
echo "🔗 URLs úteis:"
echo "   - Broker API: http://localhost:8000"
echo "   - Grafana: http://localhost:3000 (admin/admin)"
echo "   - Jaeger: http://localhost:16686"
echo "   - Prometheus: http://localhost:9090"
