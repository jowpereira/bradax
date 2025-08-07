"""
Testes REAIS para TelemetryInterceptor - Subtarefa 2.1
Valida get_telemetry_headers() sem mocks, com dados reais
"""

import pytest
import os
import sys
import time
from unittest.mock import patch
from datetime import datetime

# Adicionar SDK ao path para importação
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'bradax-sdk', 'src'))

# Sistema sob teste
from bradax.telemetry_interceptor import TelemetryInterceptor


class TestTelemetryInterceptorReal:
    """
    Testes unitários REAIS para TelemetryInterceptor
    SEM MOCKS - Testa comportamento real do sistema
    """
    
    def setup_method(self):
        """Setup para cada teste - cria interceptor real"""
        # Data dir absoluto para pasta raiz do projeto
        from pathlib import Path
        project_root = Path(__file__).resolve()
        for parent in project_root.parents:
            if parent.name == "bradax":
                project_root = parent
                break
        self.test_data_dir = str(project_root / "data")
        self.interceptor = TelemetryInterceptor(data_dir=self.test_data_dir)
    
    def test_get_telemetry_headers_structure_real(self):
        """
        Testa estrutura REAL dos headers de telemetria
        VALIDAÇÃO: Headers obrigatórios presentes com valores reais
        """
        # Executar método real
        headers = self.interceptor.get_telemetry_headers()
        
        # Validar estrutura obrigatória
        assert isinstance(headers, dict), "Headers devem ser um dict"
        
        # Headers obrigatórios conforme hotfix implementado
        required_headers = [
            "X-Bradax-Request-ID",
            "X-Bradax-Project-ID", 
            "X-Bradax-Timestamp",
            "X-Bradax-SDK-Version",
            "X-Bradax-Session-ID"
        ]
        
        for header in required_headers:
            assert header in headers, f"Header obrigatório {header} ausente"
            assert headers[header], f"Header {header} não pode ser vazio"
    
    def test_get_telemetry_headers_values_real(self):
        """
        Testa valores REAIS dos headers gerados
        VALIDAÇÃO: Valores seguem formato correto e são únicos
        """
        headers = self.interceptor.get_telemetry_headers()
        
        # Request ID deve ser único e não vazio
        request_id = headers["X-Bradax-Request-ID"]
        assert len(request_id) >= 8, "Request ID muito curto"
        assert "-" in request_id or "_" in request_id, "Request ID deve ter separadores"
        
        # Timestamp deve ser formato ISO ou timestamp Unix
        timestamp = headers["X-Bradax-Timestamp"]
        assert len(timestamp) >= 10, "Timestamp muito curto"
        
        # Project ID deve ter valor real
        project_id = headers["X-Bradax-Project-ID"]
        assert len(project_id) >= 3, "Project ID muito curto"
        
        # SDK Version deve ser válida
        sdk_version = headers["X-Bradax-SDK-Version"]
        assert "." in sdk_version, "SDK version deve ter formato x.y.z"
    
    def test_get_telemetry_headers_with_custom_project_real(self):
        """
        Testa headers com project_id customizado REAL
        VALIDAÇÃO: Parâmetro project_id é respeitado
        """
        custom_project = "test-project-real-123"
        
        headers = self.interceptor.get_telemetry_headers(project_id=custom_project)
        
        # Project ID deve ser o customizado
        assert headers["X-Bradax-Project-ID"] == custom_project
        
        # Outros headers devem continuar sendo gerados
        assert headers["X-Bradax-Request-ID"]
        assert headers["X-Bradax-Timestamp"]
    
    def test_get_telemetry_headers_with_custom_session_real(self):
        """
        Testa headers com session_id customizado REAL
        VALIDAÇÃO: Parâmetro session_id é respeitado
        """
        custom_session = "session-real-test-456"
        
        headers = self.interceptor.get_telemetry_headers(session_id=custom_session)
        
        # Session ID deve ser o customizado
        assert headers["X-Bradax-Session-ID"] == custom_session
        
        # Outros headers devem continuar sendo gerados
        assert headers["X-Bradax-Request-ID"]
        assert headers["X-Bradax-Timestamp"]
    
    def test_get_telemetry_headers_uniqueness_real(self):
        """
        Testa unicidade REAL dos headers em múltiplas chamadas
        VALIDAÇÃO: Request IDs únicos, timestamps diferentes
        """
        # Gerar múltiplos headers
        headers_1 = self.interceptor.get_telemetry_headers()
        time.sleep(0.01)  # Pequeno delay para timestamp diferente
        headers_2 = self.interceptor.get_telemetry_headers()
        headers_3 = self.interceptor.get_telemetry_headers()
        
        # Request IDs devem ser únicos
        request_ids = [
            headers_1["X-Bradax-Request-ID"],
            headers_2["X-Bradax-Request-ID"], 
            headers_3["X-Bradax-Request-ID"]
        ]
        assert len(set(request_ids)) == 3, "Request IDs devem ser únicos"
        
        # Timestamps podem ser diferentes (depende da precisão)
        timestamps = [
            headers_1["X-Bradax-Timestamp"],
            headers_2["X-Bradax-Timestamp"],
            headers_3["X-Bradax-Timestamp"]
        ]
        # Pelo menos alguns devem ser diferentes
        assert len(set(timestamps)) >= 2, "Timestamps devem variar entre chamadas"
    
    def test_get_telemetry_headers_content_validation_real(self):
        """
        Testa validação de conteúdo REAL dos headers
        VALIDAÇÃO: Valores não contêm caracteres inválidos para HTTP
        """
        headers = self.interceptor.get_telemetry_headers()
        
        # Caracteres proibidos em headers HTTP
        forbidden_chars = ['\n', '\r', '\0', '\t']
        
        for header_name, header_value in headers.items():
            # Nome do header
            assert isinstance(header_name, str), f"Nome do header {header_name} deve ser string"
            for char in forbidden_chars:
                assert char not in header_name, f"Header name {header_name} contém char proibido: {repr(char)}"
            
            # Valor do header  
            assert isinstance(header_value, str), f"Valor do header {header_name} deve ser string"
            for char in forbidden_chars:
                assert char not in header_value, f"Header value {header_name}={header_value} contém char proibido: {repr(char)}"
    
    def test_get_telemetry_headers_performance_real(self):
        """
        Testa performance REAL da geração de headers
        VALIDAÇÃO: Geração deve ser rápida (< 100ms)
        """
        start_time = time.time()
        
        # Gerar headers múltiplas vezes
        for _ in range(10):
            headers = self.interceptor.get_telemetry_headers()
            assert len(headers) >= 5  # Validação básica
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance aceitável (10 gerações em < 100ms)
        assert duration < 0.1, f"Geração de headers muito lenta: {duration:.3f}s"
    
    def test_get_telemetry_headers_environment_independence_real(self):
        """
        Testa independência REAL de variáveis de ambiente
        VALIDAÇÃO: Headers gerados independente do ambiente
        """
        # Limpar variáveis de ambiente temporariamente
        original_env = {}
        env_vars_to_test = [
            "BRADAX_PROJECT_ID",
            "BRADAX_SESSION_ID", 
            "BRADAX_REQUEST_ID",
            "BRADAX_TEST_MODE"
        ]
        
        for var in env_vars_to_test:
            original_env[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
        
        try:
            # Gerar headers sem env vars
            headers = self.interceptor.get_telemetry_headers()
            
            # Headers devem ser gerados normalmente
            assert headers["X-Bradax-Request-ID"]
            assert headers["X-Bradax-Project-ID"]
            assert headers["X-Bradax-Timestamp"]
            
        finally:
            # Restaurar env vars
            for var, value in original_env.items():
                if value is not None:
                    os.environ[var] = value
    
    def test_get_telemetry_headers_error_resistance_real(self):
        """
        Testa resistência REAL a erros no interceptor
        VALIDAÇÃO: Headers gerados mesmo com problemas internos
        """
        # Criar interceptor com data_dir inválido (usando caminho absoluto que não existe)
        invalid_interceptor = TelemetryInterceptor(data_dir="c:/invalid/path/test")
        
        # Headers devem ser gerados mesmo assim
        headers = invalid_interceptor.get_telemetry_headers()
        
        # Estrutura básica deve estar presente
        assert headers["X-Bradax-Request-ID"]
        assert headers["X-Bradax-Timestamp"]
        assert headers["X-Bradax-SDK-Version"]
    
    def test_telemetry_interceptor_hotfix_validation_real(self):
        """
        Testa VALIDAÇÃO ESPECÍFICA do Hotfix 1 implementado
        VALIDAÇÃO: TelemetryInterceptor resolve problema HTTP 403
        """
        # Este teste valida que o hotfix resolveu o problema
        # Headers devem ser gerados corretamente para evitar HTTP 403
        
        headers = self.interceptor.get_telemetry_headers()
        
        # Headers críticos para evitar HTTP 403 (conforme hotfix)
        critical_headers = [
            "X-Bradax-Request-ID",     # Obrigatório para tracking
            "X-Bradax-Project-ID",     # Obrigatório para auth
            "X-Bradax-Timestamp"       # Obrigatório para auditoria
        ]
        
        for header in critical_headers:
            assert header in headers, f"Header crítico {header} ausente - pode causar HTTP 403"
            assert headers[header].strip(), f"Header {header} vazio - pode causar HTTP 403"
        
        # Validar formato específico que resolve HTTP 403
        request_id = headers["X-Bradax-Request-ID"]
        assert len(request_id) >= 8, "Request ID muito curto - pode causar rejeição"
        
        project_id = headers["X-Bradax-Project-ID"] 
        assert not project_id.startswith(" "), "Project ID não pode começar com espaço"
        assert not project_id.endswith(" "), "Project ID não pode terminar com espaço"


# Função utilitária para execução standalone
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
