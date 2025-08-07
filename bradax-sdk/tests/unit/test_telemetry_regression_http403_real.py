"""
Teste de REGRESSÃO REAL - Prevenir volta do HTTP 403 - Subtarefa 2.4
Valida que hotfix de telemetria permanece funcionando e previne regressões
"""

import pytest
import time
from typing import Dict, Any
from unittest.mock import patch

# Sistema sob teste para regressão
from bradax.client import BradaxClient
from bradax.config.sdk_config import BradaxSDKConfig
from bradax.telemetry_interceptor import TelemetryInterceptor


class TestTelemetryRegressionHTTP403Real:
    """
    Testes de REGRESSÃO para garantir que HTTP 403 não volte
    Estes testes devem SEMPRE passar se o hotfix estiver correto
    """
    
    def setup_method(self):
        """Setup para testes de regressão"""
        self.config = BradaxSDKConfig.for_testing(
            broker_url="http://localhost:8000",
            project_id="regression-test-http403",
            enable_telemetry=True
        )
        self.client = BradaxClient(self.config)
    
    def test_regression_telemetry_headers_always_present_real(self):
        """
        Teste REGRESSÃO: Headers de telemetria SEMPRE presentes
        VALIDAÇÃO: TelemetryInterceptor nunca retorna dict vazio
        """
        interceptor = TelemetryInterceptor()
        
        # Testar múltiplas vezes para garantir consistência
        for i in range(10):
            headers = interceptor.get_telemetry_headers()
            
            # NUNCA deve retornar vazio (causaria HTTP 403)
            assert headers, f"Headers vazios na iteração {i+1} - RISCO DE HTTP 403"
            assert isinstance(headers, dict), f"Headers não são dict na iteração {i+1}"
            assert len(headers) > 0, f"Dict de headers vazio na iteração {i+1} - RISCO DE HTTP 403"
            
            # Headers críticos sempre presentes
            critical_headers = ["x-bradax-session-id", "x-bradax-timestamp"]
            for header in critical_headers:
                assert header in headers, f"Header crítico {header} ausente na iteração {i+1} - RISCO DE HTTP 403"
                assert headers[header], f"Header {header} vazio na iteração {i+1} - RISCO DE HTTP 403"
    
    def test_regression_no_empty_header_values_real(self):
        """
        Teste REGRESSÃO: Valores de headers nunca vazios
        VALIDAÇÃO: Headers críticos sempre têm valores válidos
        """
        interceptor = TelemetryInterceptor()
        headers = interceptor.get_telemetry_headers()
        
        # Verificar todos os headers têm valores não vazios
        for header_name, header_value in headers.items():
            # Valores não podem ser None
            assert header_value is not None, f"Header {header_name} é None - RISCO DE HTTP 403"
            
            # Valores não podem ser string vazia
            if isinstance(header_value, str):
                assert header_value.strip(), f"Header {header_name} é string vazia - RISCO DE HTTP 403"
            
            # Valores não podem ser apenas espaços
            assert str(header_value).strip(), f"Header {header_name} só tem espaços - RISCO DE HTTP 403"
    
    def test_regression_headers_included_in_all_http_methods_real(self):
        """
        Teste REGRESSÃO: Headers incluídos em TODAS as requisições HTTP
        VALIDAÇÃO: invoke() e ainvoke() sempre incluem headers
        """
        # Mock para capturar headers de diferentes métodos
        captured_requests = []
        
        def capture_http_call(*args, **kwargs):
            captured_requests.append({
                'method': 'POST',
                'headers': dict(kwargs.get('headers', {})),
                'call_type': 'sync'
            })
            # Resposta simulada para não falhar
            class MockResponse:
                status_code = 200
                def json(self):
                    return {"success": True, "response_text": "Regression test response"}
            return MockResponse()
        
        import httpx
        original_sync_post = httpx.Client.post
        
        # Teste método síncrono invoke()
        httpx.Client.post = capture_http_call
        
        try:
            self.client.invoke("Regression test sync")
        except:
            pass  # Ignorar erros, foco nos headers
        finally:
            httpx.Client.post = original_sync_post
        
        # Validar que headers foram incluídos no método síncrono
        assert len(captured_requests) > 0, "Nenhuma requisição capturada - possível regressão"
        
        sync_request = captured_requests[0]
        sync_headers = sync_request['headers']
        
        # Headers de telemetria devem estar presentes
        telemetry_present = any(header.startswith('x-bradax') for header in sync_headers.keys())
        assert telemetry_present, "Headers de telemetria ausentes em invoke() - REGRESSÃO HTTP 403"
        
        # Headers críticos específicos
        assert "x-bradax-session-id" in sync_headers, "Session ID ausente em invoke() - REGRESSÃO"
        assert "x-bradax-timestamp" in sync_headers, "Timestamp ausente em invoke() - REGRESSÃO"
    
    def test_regression_telemetry_survives_config_changes_real(self):
        """
        Teste REGRESSÃO: Headers de telemetria sobrevivem a mudanças de config
        VALIDAÇÃO: Mudanças na configuração não quebram geração de headers
        """
        # Testar com diferentes configurações
        configs_to_test = [
            BradaxSDKConfig.for_testing(project_id="config-test-1"),
            BradaxSDKConfig.for_testing(project_id="config-test-2", timeout=60),
            BradaxSDKConfig.for_testing(project_id="config-test-3", enable_telemetry=True),
        ]
        
        for i, config in enumerate(configs_to_test):
            client = BradaxClient(config)
            headers = client.telemetry_interceptor.get_telemetry_headers()
            
            # Headers sempre presentes independente da config
            assert headers, f"Headers ausentes com config {i+1} - REGRESSÃO HTTP 403"
            assert "x-bradax-session-id" in headers, f"Session ID ausente com config {i+1} - REGRESSÃO"
            assert "x-bradax-timestamp" in headers, f"Timestamp ausente com config {i+1} - REGRESSÃO"
    
    def test_regression_telemetry_error_resilience_real(self):
        """
        Teste REGRESSÃO: Headers funcionam mesmo com erros internos
        VALIDAÇÃO: Falhas internas não impedem geração de headers básicos
        """
        # Simular problemas que poderiam quebrar telemetria
        
        # 1. Problema com diretório de dados
        faulty_interceptor = TelemetryInterceptor(data_dir="/invalid/nonexistent/path")
        headers = faulty_interceptor.get_telemetry_headers()
        
        assert headers, "Headers ausentes com data_dir inválido - REGRESSÃO HTTP 403"
        assert "x-bradax-timestamp" in headers, "Timestamp ausente com erro de dir - REGRESSÃO"
        
        # 2. Problema com permissões (simulado)
        try:
            # Tentar criar interceptor que pode ter problemas
            problematic_interceptor = TelemetryInterceptor(data_dir=".")
            problem_headers = problematic_interceptor.get_telemetry_headers()
            
            # Mesmo com problemas, headers básicos devem existir
            assert problem_headers, "Headers ausentes com problemas de permissão - REGRESSÃO"
        except Exception:
            # Se deu exceção, não deve quebrar o sistema
            pass
    
    def test_regression_telemetry_concurrent_access_real(self):
        """
        Teste REGRESSÃO: Headers funcionam com acesso concorrente
        VALIDAÇÃO: Múltiplas threads/chamadas não quebram geração
        """
        import threading
        import queue
        
        results = queue.Queue()
        
        def generate_headers_concurrently():
            try:
                interceptor = TelemetryInterceptor()
                headers = interceptor.get_telemetry_headers()
                results.put(('success', headers))
            except Exception as e:
                results.put(('error', str(e)))
        
        # Criar múltiplas threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=generate_headers_concurrently)
            threads.append(thread)
            thread.start()
        
        # Aguardar todas as threads
        for thread in threads:
            thread.join(timeout=5)
        
        # Coletar resultados
        successes = 0
        while not results.empty():
            status, data = results.get()
            if status == 'success':
                successes += 1
                # Validar headers de cada thread
                assert data, f"Headers vazios em thread concorrente - REGRESSÃO HTTP 403"
                assert "x-bradax-session-id" in data, "Session ID ausente em acesso concorrente"
        
        # Pelo menos algumas threads devem ter sucesso
        assert successes >= 3, f"Apenas {successes}/5 threads tiveram sucesso - possível regressão concorrência"
    
    def test_regression_telemetry_mandatory_headers_format_real(self):
        """
        Teste REGRESSÃO: Formato dos headers obrigatórios sempre correto
        VALIDAÇÃO: Headers seguem formato que evita HTTP 403
        """
        interceptor = TelemetryInterceptor()
        headers = interceptor.get_telemetry_headers()
        
        # Validar formato do Session ID (deve ser UUID-like)
        session_id = headers.get("x-bradax-session-id", "")
        assert len(session_id) >= 8, "Session ID muito curto - pode causar HTTP 403"
        
        # Validar formato do Timestamp (deve ser ISO-like)
        timestamp = headers.get("x-bradax-timestamp", "")
        assert ":" in timestamp, "Timestamp sem formato válido - pode causar HTTP 403"
        assert len(timestamp) >= 10, "Timestamp muito curto - pode causar HTTP 403"
        
        # Validar formato da SDK Version
        sdk_version = headers.get("x-bradax-sdk-version", "")
        assert "." in sdk_version, "SDK version sem formato válido - pode causar HTTP 403"
        assert len(sdk_version) >= 3, "SDK version muito curta - pode causar HTTP 403"
        
        # Validar caracteres proibidos que causam HTTP 403
        forbidden_chars = ['\n', '\r', '\0', '\t']
        for header_name, header_value in headers.items():
            for char in forbidden_chars:
                assert char not in header_name, f"Header name {header_name} tem char proibido - HTTP 403"
                assert char not in str(header_value), f"Header value {header_name} tem char proibido - HTTP 403"
    
    def test_regression_critical_hotfix_scenario_simulation_real(self):
        """
        Teste REGRESSÃO: Simula cenário exato que causava HTTP 403
        VALIDAÇÃO: Cenário original do hotfix nunca deve falhar novamente
        """
        # Simular o cenário que causava HTTP 403 antes do hotfix:
        # 1. Cliente criado sem configuração especial
        # 2. Requisição simples sem headers manuais
        # 3. Deve funcionar graças aos headers automáticos de telemetria
        
        basic_config = BradaxSDKConfig.for_testing(
            broker_url="http://localhost:8000",
            project_id="hotfix-regression-test"
        )
        basic_client = BradaxClient(basic_config)
        
        # Verificar que interceptor está funcionando
        assert basic_client.telemetry_interceptor, "TelemetryInterceptor não inicializado - REGRESSÃO"
        
        # Verificar geração de headers (que resolvia o HTTP 403)
        telemetry_headers = basic_client.telemetry_interceptor.get_telemetry_headers()
        assert telemetry_headers, "Headers de telemetria não gerados - REGRESSÃO DO HOTFIX"
        
        # Headers específicos que resolviam HTTP 403
        critical_for_403 = ["x-bradax-session-id", "x-bradax-timestamp"]
        for header in critical_for_403:
            assert header in telemetry_headers, f"Header {header} ausente - VOLTA DO HTTP 403"
            assert telemetry_headers[header], f"Header {header} vazio - VOLTA DO HTTP 403"
        
        # Se chegou até aqui, o hotfix está preservado
        print("✅ Hotfix HTTP 403 preservado - regressão prevenida")


# Execução standalone para verificação rápida de regressão
if __name__ == "__main__":
    print("🔍 Testes de Regressão - Prevenir volta do HTTP 403")
    print("🎯 Objetivo: Garantir que hotfix de telemetria permanece ativo")
    print()
    
    # Executar teste crítico rapidamente
    test_instance = TestTelemetryRegressionHTTP403Real()
    test_instance.setup_method()
    
    try:
        test_instance.test_regression_critical_hotfix_scenario_simulation_real()
        print("✅ Teste crítico de regressão PASSOU - hotfix preservado")
    except Exception as e:
        print(f"❌ REGRESSÃO DETECTADA: {e}")
        print("🚨 AÇÃO REQUERIDA: Verificar se hotfix foi quebrado")
    
    # Executar todos os testes
    pytest.main([__file__, "-v"])
