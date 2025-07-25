#!/usr/bin/env python3
"""
Script de teste simples para validar os schemas da API bradax

Execute este script para fazer um teste rápido dos schemas:
python test_schemas_quick.py
"""

import sys
import os
from datetime import datetime
from pprint import pprint

# Adicionar o diretório shared ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from schemas.api_models import (
        AuthRequest, AuthResponse, LLMRequest, LLMResponse,
        Message, MessageRole, LLMParameters, Usage,
        VectorQueryRequest, VectorDocument, VectorUpsertRequest,
        GraphDeployRequest, TokenType
    )
    print("✅ Importação dos schemas bem-sucedida!")
except ImportError as e:
    print(f"❌ Erro na importação: {e}")
    sys.exit(1)


def test_auth_models():
    """Testa modelos de autenticação"""
    print("\n🔐 Testando modelos de autenticação...")
    
    # Teste AuthRequest
    auth_req = AuthRequest(
        project_id="fraude-claims",
        api_key="bx_live_abc123",
        scopes=["invoke_llm", "read_vector"]
    )
    print(f"✅ AuthRequest criado: {auth_req.project_id}")
    
    # Teste AuthResponse
    auth_resp = AuthResponse(
        access_token="eyJ0eXAi...",
        refresh_token="eyJ0eXAi...",
        expires_in=900,
        scopes=["invoke_llm", "read_vector"]
    )
    print(f"✅ AuthResponse criado: expires_in={auth_resp.expires_in}s")
    
    return True


def test_llm_models():
    """Testa modelos de LLM"""
    print("\n🤖 Testando modelos de LLM...")
    
    # Teste Message
    messages = [
        Message(
            role=MessageRole.SYSTEM,
            content="Você é um perito em sinistros de seguros."
        ),
        Message(
            role=MessageRole.USER,
            content="Meu carro foi roubado, o que devo fazer?"
        )
    ]
    print(f"✅ Messages criadas: {len(messages)} mensagens")
    
    # Teste LLMParameters
    params = LLMParameters(
        temperature=0.7,
        max_tokens=1000,
        top_p=0.9,
        stream=False
    )
    print(f"✅ LLMParameters criado: temp={params.temperature}")
    
    # Teste LLMRequest
    llm_req = LLMRequest(
        model="gpt-4o-mini",
        messages=messages,
        parameters=params
    )
    print(f"✅ LLMRequest criado: model={llm_req.model}")
    
    # Teste Usage
    usage = Usage(
        prompt_tokens=45,
        completion_tokens=150,
        total_tokens=195,
        cost_usd=0.001
    )
    print(f"✅ Usage criado: total_tokens={usage.total_tokens}")
    
    # Teste LLMResponse
    llm_resp = LLMResponse(
        content="Para casos de roubo de veículo, você deve seguir os seguintes passos...",
        model="gpt-4o-mini",
        usage=usage
    )
    print(f"✅ LLMResponse criado: {len(llm_resp.content)} caracteres")
    
    return True


def test_vector_models():
    """Testa modelos de Vector DB"""
    print("\n🔍 Testando modelos de Vector Database...")
    
    # Teste VectorQueryRequest com texto
    query_req = VectorQueryRequest(
        collection="claims_vectors",
        query_text="roubo de veículo",
        top_k=5,
        threshold=0.7
    )
    print(f"✅ VectorQueryRequest criado: collection={query_req.collection}")
    
    # Teste VectorDocument
    documents = [
        VectorDocument(
            id="doc_123",
            vector=[0.1, 0.2, 0.3, 0.4, 0.5],
            metadata={
                "title": "Procedimentos para Roubo de Veículo",
                "category": "sinistros",
                "last_updated": "2025-07-25"
            },
            text="Em casos de roubo de veículo, o segurado deve..."
        ),
        VectorDocument(
            id="doc_124",
            vector=[0.2, 0.3, 0.4, 0.5, 0.6],
            metadata={
                "title": "Documentação Necessária",
                "category": "documentos"
            }
        )
    ]
    print(f"✅ VectorDocuments criados: {len(documents)} documentos")
    
    # Teste VectorUpsertRequest
    upsert_req = VectorUpsertRequest(
        collection="claims_vectors",
        documents=documents
    )
    print(f"✅ VectorUpsertRequest criado: {len(upsert_req.documents)} docs")
    
    return True


def test_graph_models():
    """Testa modelos de Graph"""
    print("\n🕸️ Testando modelos de Graph...")
    
    yaml_definition = """
name: classify_claims
nodes:
  - id: embed
    tool: embedder
    params:
      model: text-embedding-3-small
  - id: llm
    tool: llm
    params:
      model: gpt-4o-mini
      temperature: 0.1
edges:
  - [embed, llm]
"""
    
    graph_req = GraphDeployRequest(
        name="pipeline_fraude_detection",
        definition=yaml_definition,
        format="yaml"
    )
    print(f"✅ GraphDeployRequest criado: {graph_req.name}")
    
    return True


def test_json_serialization():
    """Testa serialização JSON"""
    print("\n📄 Testando serialização JSON...")
    
    # Criar um objeto complexo
    auth_req = AuthRequest(
        project_id="test-project",
        api_key="bx_test_12345",
        scopes=["invoke_llm", "read_vector"],
        metadata={"client": "test", "version": "1.0"}
    )
    
    # Serializar para JSON
    json_data = auth_req.model_dump()
    print("✅ Serialização JSON:")
    pprint(json_data, indent=2)
    
    # Deserializar de volta
    restored = AuthRequest(**json_data)
    print(f"✅ Deserialização: {restored.project_id}")
    
    return True


def test_validation_errors():
    """Testa validação de erros"""
    print("\n❌ Testando validação de erros...")
    
    try:
        # Deve falhar - project_id obrigatório
        AuthRequest(api_key="test")
        print("❌ Erro: deveria ter falhado!")
        return False
    except Exception as e:
        print(f"✅ Validação funcionou: {type(e).__name__}")
    
    try:
        # Deve falhar - temperature fora do range
        LLMParameters(temperature=3.0)
        print("❌ Erro: deveria ter falhado!")
        return False
    except Exception as e:
        print(f"✅ Validação funcionou: {type(e).__name__}")
    
    try:
        # Deve falhar - sem query_vector nem query_text
        VectorQueryRequest(collection="test")
        print("❌ Erro: deveria ter falhado!")
        return False
    except Exception as e:
        print(f"✅ Validação funcionou: {type(e).__name__}")
    
    return True


def main():
    """Executa todos os testes"""
    print("🚀 Iniciando testes dos schemas bradax API...")
    
    tests = [
        test_auth_models,
        test_llm_models,
        test_vector_models,
        test_graph_models,
        test_json_serialization,
        test_validation_errors
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"❌ Teste {test.__name__} falhou")
        except Exception as e:
            print(f"❌ Teste {test.__name__} teve exceção: {e}")
    
    print(f"\n📊 Resultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 Todos os testes dos schemas passaram!")
        return 0
    else:
        print("💥 Alguns testes falharam!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
