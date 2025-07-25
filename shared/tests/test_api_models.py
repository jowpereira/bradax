"""
Testes para os schemas Pydantic compartilhados

Este arquivo testa a validação, serialização e deserialização
dos modelos de dados da API bradax.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from schemas.api_models import (
    TokenType, MessageRole, GraphStatus, HealthStatus,
    AuthRequest, AuthResponse, LLMRequest, LLMResponse,
    VectorQueryRequest, VectorUpsertRequest, GraphDeployRequest,
    GraphExecuteRequest, ErrorResponse, ErrorDetail, Message, 
    LLMParameters, Usage, VectorDocument
)


class TestEnums:
    """Testa os enums definidos nos schemas"""
    
    def test_token_type_enum(self):
        assert TokenType.BEARER == "Bearer"
        
    def test_message_role_enum(self):
        assert MessageRole.SYSTEM == "system"
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        
    def test_graph_status_enum(self):
        assert GraphStatus.PENDING == "pending"
        assert GraphStatus.RUNNING == "running"
        assert GraphStatus.COMPLETED == "completed"
        assert GraphStatus.FAILED == "failed"
        
    def test_health_status_enum(self):
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"


class TestAuthenticationModels:
    """Testa os modelos de autenticação"""
    
    def test_auth_request_valid(self):
        data = {
            "project_id": "test-project",
            "api_key": "bx_test_12345",
            "scopes": ["invoke_llm", "read_vector"]
        }
        auth_req = AuthRequest(**data)
        
        assert auth_req.project_id == "test-project"
        assert auth_req.api_key == "bx_test_12345"
        assert auth_req.scopes == ["invoke_llm", "read_vector"]
        
    def test_auth_request_missing_required_fields(self):
        with pytest.raises(ValidationError) as exc_info:
            AuthRequest(api_key="test")
        
        assert "project_id" in str(exc_info.value)
        
    def test_auth_response_valid(self):
        data = {
            "access_token": "eyJ0eXAi...",
            "refresh_token": "eyJ0eXAi...",
            "expires_in": 900,
            "scopes": ["invoke_llm"]
        }
        auth_resp = AuthResponse(**data)
        
        assert auth_resp.token_type == TokenType.BEARER
        assert auth_resp.expires_in == 900
        assert isinstance(auth_resp.timestamp, datetime)


class TestLLMModels:
    """Testa os modelos relacionados a LLM"""
    
    def test_message_valid(self):
        msg = Message(
            role=MessageRole.USER,
            content="Olá, como você está?",
            metadata={"source": "test"}
        )
        
        assert msg.role == MessageRole.USER
        assert msg.content == "Olá, como você está?"
        assert msg.metadata["source"] == "test"
        
    def test_message_invalid_role(self):
        with pytest.raises(ValidationError):
            Message(role="invalid_role", content="test")
            
    def test_llm_parameters_valid(self):
        params = LLMParameters(
            temperature=0.7,
            max_tokens=1000,
            top_p=0.9,
            stream=True
        )
        
        assert params.temperature == 0.7
        assert params.max_tokens == 1000
        assert params.stream is True
        
    def test_llm_parameters_invalid_temperature(self):
        with pytest.raises(ValidationError):
            LLMParameters(temperature=3.0)  # > 2.0
            
        with pytest.raises(ValidationError):
            LLMParameters(temperature=-0.1)  # < 0.0
            
    def test_usage_model(self):
        usage = Usage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.001
        )
        
        assert usage.prompt_tokens == 100
        assert usage.total_tokens == 150
        assert usage.cost_usd == 0.001
        
    def test_usage_negative_tokens(self):
        with pytest.raises(ValidationError):
            Usage(
                prompt_tokens=-1,
                completion_tokens=50,
                total_tokens=150
            )
            
    def test_llm_request_valid(self):
        messages = [
            Message(role=MessageRole.SYSTEM, content="You are a helpful assistant"),
            Message(role=MessageRole.USER, content="Hello!")
        ]
        
        llm_req = LLMRequest(
            model="gpt-4o-mini",
            messages=messages,
            parameters=LLMParameters(temperature=0.7)
        )
        
        assert llm_req.model == "gpt-4o-mini"
        assert len(llm_req.messages) == 2
        assert llm_req.parameters.temperature == 0.7
        
    def test_llm_request_empty_messages(self):
        with pytest.raises(ValidationError):
            LLMRequest(model="gpt-4", messages=[])
            
    def test_llm_response_valid(self):
        usage = Usage(
            prompt_tokens=50,
            completion_tokens=100,
            total_tokens=150
        )
        
        response = LLMResponse(
            content="Olá! Como posso ajudar?",
            model="gpt-4o-mini",
            usage=usage
        )
        
        assert response.content == "Olá! Como posso ajudar?"
        assert response.model == "gpt-4o-mini"
        assert response.usage.total_tokens == 150


class TestVectorModels:
    """Testa os modelos relacionados ao Vector Database"""
    
    def test_vector_query_request_with_text(self):
        req = VectorQueryRequest(
            collection="test_collection",
            query_text="buscar documentos similares",
            top_k=5
        )
        
        assert req.collection == "test_collection"
        assert req.query_text == "buscar documentos similares"
        assert req.top_k == 5
        
    def test_vector_query_request_with_vector(self):
        req = VectorQueryRequest(
            collection="test_collection",
            query_vector=[0.1, 0.2, 0.3],
            top_k=10
        )
        
        assert req.query_vector == [0.1, 0.2, 0.3]
        assert req.top_k == 10
        
    def test_vector_query_request_without_query(self):
        with pytest.raises(ValidationError) as exc_info:
            VectorQueryRequest(collection="test")
            
        assert "Either query_vector or query_text must be provided" in str(exc_info.value)
        
    def test_vector_query_invalid_top_k(self):
        with pytest.raises(ValidationError):
            VectorQueryRequest(
                collection="test",
                query_text="test",
                top_k=0  # deve ser > 0
            )
            
        with pytest.raises(ValidationError):
            VectorQueryRequest(
                collection="test", 
                query_text="test",
                top_k=101  # deve ser <= 100
            )
            
    def test_vector_document_valid(self):
        doc = VectorDocument(
            id="doc_123",
            vector=[0.1, 0.2, 0.3, 0.4],
            metadata={"title": "Test Document", "category": "test"},
            text="Conteúdo do documento de teste"
        )
        
        assert doc.id == "doc_123"
        assert len(doc.vector) == 4
        assert doc.metadata["title"] == "Test Document"
        
    def test_vector_upsert_request_valid(self):
        documents = [
            VectorDocument(
                id="doc1",
                vector=[0.1, 0.2],
                metadata={"type": "test"}
            ),
            VectorDocument(
                id="doc2", 
                vector=[0.3, 0.4],
                metadata={"type": "test"}
            )
        ]
        
        req = VectorUpsertRequest(
            collection="test_collection",
            documents=documents
        )
        
        assert req.collection == "test_collection"
        assert len(req.documents) == 2
        
    def test_vector_upsert_empty_documents(self):
        with pytest.raises(ValidationError):
            VectorUpsertRequest(
                collection="test",
                documents=[]  # deve ter pelo menos 1 item
            )


class TestGraphModels:
    """Testa os modelos relacionados aos Grafos"""
    
    def test_graph_deploy_request_valid(self):
        yaml_definition = """
        name: test_graph
        nodes:
          - id: node1
            type: llm
        """
        
        req = GraphDeployRequest(
            name="test_pipeline",
            definition=yaml_definition,
            format="yaml"
        )
        
        assert req.name == "test_pipeline"
        assert req.format == "yaml"
        
    def test_graph_deploy_invalid_format(self):
        with pytest.raises(ValidationError):
            GraphDeployRequest(
                name="test",
                definition="{}",
                format="xml"  # deve ser yaml ou json
            )
            
    def test_graph_execute_request_valid(self):
        req = GraphExecuteRequest(
            graph_id="graph_123",
            inputs={"input1": "value1", "input2": 42},
            stream=True
        )
        
        assert req.graph_id == "graph_123"
        assert req.inputs["input1"] == "value1"
        assert req.stream is True


class TestErrorModels:
    """Testa os modelos de erro"""
    
    def test_error_response_valid(self):
        error_detail = ErrorDetail(
            code="FIELD_REQUIRED",
            message="Campo obrigatório",
            field="project_id"
        )
        
        error = ErrorResponse(
            error="validation_error",
            message="Dados inválidos fornecidos",
            details=[error_detail]
        )
        
        assert error.error == "validation_error"
        assert error.message == "Dados inválidos fornecidos"
        assert len(error.details) == 1
        assert error.details[0].field == "project_id"
        assert error.details[0].code == "FIELD_REQUIRED"


class TestSerializationDeserialization:
    """Testa serialização e deserialização JSON"""
    
    def test_auth_request_json_roundtrip(self):
        original = AuthRequest(
            project_id="test-project",
            api_key="bx_test_12345",
            scopes=["invoke_llm"]
        )
        
        # Serializar para JSON
        json_data = original.model_dump()
        
        # Deserializar de volta
        restored = AuthRequest(**json_data)
        
        assert restored.project_id == original.project_id
        assert restored.api_key == original.api_key
        assert restored.scopes == original.scopes
        
    def test_llm_response_json_roundtrip(self):
        usage = Usage(
            prompt_tokens=50,
            completion_tokens=100, 
            total_tokens=150,
            cost_usd=0.001
        )
        
        original = LLMResponse(
            content="Resposta do LLM",
            model="gpt-4o-mini",
            usage=usage
        )
        
        # Serializar
        json_data = original.model_dump()
        
        # Deserializar
        restored = LLMResponse(**json_data)
        
        assert restored.content == original.content
        assert restored.model == original.model
        assert restored.usage.total_tokens == original.usage.total_tokens


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
