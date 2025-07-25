#!/bin/bash
# Script para gerar código gRPC a partir dos arquivos .proto

set -e

echo "🔄 Gerando código gRPC..."

# Verificar se protoc está instalado
if ! command -v protoc >/dev/null 2>&1; then
    echo "❌ protoc não encontrado. Instalando..."
    
    # Detectar sistema operacional
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew >/dev/null 2>&1; then
            brew install protobuf
        else
            echo "❌ Homebrew não encontrado. Instale o protobuf manualmente."
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get update && sudo apt-get install -y protobuf-compiler
        elif command -v yum >/dev/null 2>&1; then
            sudo yum install -y protobuf-compiler
        else
            echo "❌ Gerenciador de pacotes não suportado. Instale o protobuf manualmente."
            exit 1
        fi
    else
        echo "❌ Sistema operacional não suportado para instalação automática."
        exit 1
    fi
fi

# Criar diretórios de saída se não existirem
mkdir -p packages/bradax-sdk/src/bradax/grpc_client
mkdir -p packages/bradax-broker/src/broker/grpc_service/generated

# Gerar código Python para o SDK (cliente)
echo "📦 Gerando cliente gRPC para SDK..."
python -m grpc_tools.protoc \
    --proto_path=shared/proto \
    --python_out=packages/bradax-sdk/src/bradax/grpc_client \
    --grpc_python_out=packages/bradax-sdk/src/bradax/grpc_client \
    shared/proto/broker.proto

# Gerar código Python para o Broker (servidor)
echo "🖥️ Gerando servidor gRPC para Broker..."
python -m grpc_tools.protoc \
    --proto_path=shared/proto \
    --python_out=packages/bradax-broker/src/broker/grpc_service/generated \
    --grpc_python_out=packages/bradax-broker/src/broker/grpc_service/generated \
    shared/proto/broker.proto

# Criar arquivos __init__.py se não existirem
touch packages/bradax-sdk/src/bradax/grpc_client/__init__.py
touch packages/bradax-broker/src/broker/grpc_service/__init__.py
touch packages/bradax-broker/src/broker/grpc_service/generated/__init__.py

# Corrigir imports relativos no código gerado
echo "🔧 Corrigindo imports..."

# SDK
if [ -f "packages/bradax-sdk/src/bradax/grpc_client/broker_pb2_grpc.py" ]; then
    sed -i 's/import broker_pb2/from . import broker_pb2/g' packages/bradax-sdk/src/bradax/grpc_client/broker_pb2_grpc.py
fi

# Broker
if [ -f "packages/bradax-broker/src/broker/grpc_service/generated/broker_pb2_grpc.py" ]; then
    sed -i 's/import broker_pb2/from . import broker_pb2/g' packages/bradax-broker/src/broker/grpc_service/generated/broker_pb2_grpc.py
fi

echo "✅ Código gRPC gerado com sucesso!"
echo ""
echo "📁 Arquivos gerados:"
echo "   - packages/bradax-sdk/src/bradax/grpc_client/broker_pb2.py"
echo "   - packages/bradax-sdk/src/bradax/grpc_client/broker_pb2_grpc.py"
echo "   - packages/bradax-broker/src/broker/grpc_service/generated/broker_pb2.py"
echo "   - packages/bradax-broker/src/broker/grpc_service/generated/broker_pb2_grpc.py"
