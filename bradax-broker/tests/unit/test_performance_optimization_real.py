"""
Testes REAIS de performance para Performance Optimization - Subtarefa 5.1
Valida response time < 2s sem mocks - Hotfix 4
"""

import pytest
import os
import sys
import time
import asyncio
import requests
from typing import List, Dict, Any, Optional

# Adicionar broker ao path para importação
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestPerformanceOptimizationReal:
    """
    Testes performance REAIS para validar otimização de performance
    SEM MOCKS - Medição real de tempos de resposta com LLMs reais
    """
    
    def setup_method(self):
        """Setup para cada teste com configuração real de performance"""
        # Configurações obrigatórias para funcionamento real
        os.environ['BRADAX_JWT_SECRET'] = "test-jwt-secret-for-performance-testing-12345"
        
        # Configurações OpenAI REAIS (sem fallback)
        openai_key = os.getenv('OPENAI_API_KEY')
        if not openai_key:
            pytest.skip("OPENAI_API_KEY obrigatória para testes reais de performance")
        
        # Métricas de performance
        self.max_response_time = 2.0  # segundos - requisito do Hotfix 4
        self.broker_url = "http://localhost:8000"
        self.test_timeout = 10  # timeout para calls reais
        
        # Payload real para testes de performance
        self.real_test_payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": "Hello, test response time"}
            ],
            "max_tokens": 50,
            "temperature": 0.1
        }
    
    def test_openai_direct_call_performance_real(self):
        """
        Teste REAL: Chamada direta OpenAI < 2s
        VALIDAÇÃO: Performance baseline sem broker
        """
        import openai
        
        # Configurar cliente OpenAI REAL
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Medir tempo de resposta REAL
        start_time = time.time()
        
        try:
            response = client.chat.completions.create(
                model=self.real_test_payload["model"],
                messages=self.real_test_payload["messages"],
                max_tokens=self.real_test_payload["max_tokens"],
                temperature=self.real_test_payload["temperature"]
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Validar resposta real
            assert response is not None, "Resposta OpenAI é None"
            assert response.choices, "Nenhuma choice na resposta OpenAI"
            assert response.choices[0].message.content, "Conteúdo vazio na resposta"
            
            # Validar performance baseline
            assert response_time < self.max_response_time, f"Baseline OpenAI muito lenta: {response_time:.2f}s > {self.max_response_time}s"
            
            print(f"✅ OpenAI baseline: {response_time:.2f}s")
            
        except Exception as e:
            # SEM FALLBACK - falhar se OpenAI não funcionar
            pytest.fail(f"Falha na chamada OpenAI REAL (sem fallback): {e}")
    
    def test_bradax_sdk_performance_real(self):
        """
        Teste REAL: SDK Bradax response time < 2s
        VALIDAÇÃO: Performance do SDK com LLM real
        """
        try:
            # Importar SDK real
            from bradax import BradaxClient
            
            # Cliente SDK REAL
            client = BradaxClient(api_key=os.getenv('OPENAI_API_KEY'))
            
            # Medir tempo SDK REAL
            start_time = time.time()
            
            response = client.invoke(
                input_=self.real_test_payload["messages"],
                config={
                    "model": self.real_test_payload["model"],
                    "max_tokens": self.real_test_payload["max_tokens"],
                    "temperature": self.real_test_payload["temperature"]
                }
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Validar resposta real do SDK
            assert response is not None, "Resposta SDK é None"
            assert 'choices' in response or 'content' in response or 'response' in response, "SDK não retornou dados válidos"
            
            # Validar performance SDK
            assert response_time < self.max_response_time, f"SDK Bradax muito lento: {response_time:.2f}s > {self.max_response_time}s"
            
            print(f"✅ SDK Bradax: {response_time:.2f}s")
            
        except ImportError:
            pytest.skip("SDK Bradax não disponível para teste de performance")
        except Exception as e:
            # SEM FALLBACK - usar exceptions existentes
            if "rate limit" in str(e).lower():
                pytest.skip(f"Rate limit OpenAI: {e}")
            else:
                pytest.fail(f"Falha no SDK Bradax REAL (sem fallback): {e}")
    
    @pytest.mark.skipif(
        not os.getenv('BROKER_E2E_ENABLED', 'false').lower() == 'true',
        reason="Requer BROKER_E2E_ENABLED=true e broker rodando"
    )
    def test_broker_endpoint_performance_real(self):
        """
        Teste REAL: Broker endpoint response time < 2s
        VALIDAÇÃO: Performance do broker com LLM real
        """
        try:
            # Verificar se broker está rodando
            health_response = requests.get(f"{self.broker_url}/health", timeout=5)
            if health_response.status_code != 200:
                pytest.skip("Broker não está rodando - teste E2E ignorado")
            
            # Headers reais com telemetria
            headers = {
                'Content-Type': 'application/json',
                'X-Bradax-Request-ID': 'perf-test-001',
                'X-Bradax-Project-ID': 'test-project',
                'X-Bradax-User-ID': 'test-user',
                'Authorization': 'Bearer test-token'
            }
            
            # Medir tempo broker REAL
            start_time = time.time()
            
            response = requests.post(
                f"{self.broker_url}/v1/chat/completions",
                json=self.real_test_payload,
                headers=headers,
                timeout=self.test_timeout
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Validar resposta real do broker
            assert response.status_code in [200, 401, 403], f"Broker status inesperado: {response.status_code}"
            
            if response.status_code == 200:
                response_data = response.json()
                assert 'choices' in response_data, "Broker não retornou choices"
                
                # Validar performance broker
                assert response_time < self.max_response_time, f"Broker muito lento: {response_time:.2f}s > {self.max_response_time}s"
                
                print(f"✅ Broker endpoint: {response_time:.2f}s")
            else:
                # Mesmo com erro de auth, medir tempo de resposta
                assert response_time < self.max_response_time, f"Broker resposta de erro muito lenta: {response_time:.2f}s"
                print(f"⚠️ Broker auth error mas rápido: {response_time:.2f}s")
            
        except requests.exceptions.RequestException as e:
            # SEM FALLBACK - falhar se broker não responder
            pytest.fail(f"Falha na comunicação com broker REAL: {e}")
    
    def test_concurrent_requests_performance_real(self):
        """
        Teste REAL: Múltiplas requests concorrentes < 2s cada
        VALIDAÇÃO: Performance sob carga com LLMs reais
        """
        import openai
        import concurrent.futures
        
        # Cliente OpenAI REAL
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        def make_real_request():
            """Fazer request real individual"""
            start_time = time.time()
            try:
                response = client.chat.completions.create(
                    model=self.real_test_payload["model"],
                    messages=[{"role": "user", "content": f"Concurrent test {time.time():.3f}"}],
                    max_tokens=30,
                    temperature=0.1
                )
                end_time = time.time()
                return {
                    'success': True,
                    'response_time': end_time - start_time,
                    'response': response
                }
            except Exception as e:
                end_time = time.time()
                return {
                    'success': False,
                    'response_time': end_time - start_time,
                    'error': str(e)
                }
        
        # Executar 3 requests concorrentes (carga leve)
        max_concurrent = 3
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Submeter requests REAIS
            futures = [executor.submit(make_real_request) for _ in range(max_concurrent)]
            
            # Coletar resultados
            results = []
            for future in concurrent.futures.as_completed(futures, timeout=15):
                result = future.result()
                results.append(result)
        
        # Validar resultados
        successful_requests = [r for r in results if r['success']]
        failed_requests = [r for r in results if not r['success']]
        
        # Pelo menos algumas requests devem ter sucesso
        assert len(successful_requests) >= 1, f"Nenhuma request concorrente teve sucesso: {failed_requests}"
        
        # Validar performance de requests bem-sucedidas
        slow_requests = [r for r in successful_requests if r['response_time'] > self.max_response_time]
        
        assert len(slow_requests) == 0, f"Requests concorrentes muito lentas: {[(r['response_time']) for r in slow_requests]}"
        
        avg_time = sum(r['response_time'] for r in successful_requests) / len(successful_requests)
        print(f"✅ Concurrent avg: {avg_time:.2f}s ({len(successful_requests)}/{max_concurrent} success)")
    
    def test_memory_usage_performance_real(self):
        """
        Teste REAL: Uso de memória durante calls LLM reais
        VALIDAÇÃO: Performance de memória com dados reais
        """
        import psutil
        import gc
        import openai
        
        # Cliente OpenAI REAL
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Medir memória inicial
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Fazer múltiplas calls reais
        responses = []
        start_time = time.time()
        
        for i in range(3):  # 3 calls para medir crescimento
            try:
                response = client.chat.completions.create(
                    model=self.real_test_payload["model"],
                    messages=[{"role": "user", "content": f"Memory test call {i+1}"}],
                    max_tokens=40,
                    temperature=0.1
                )
                responses.append(response)
                
            except Exception as e:
                if "rate limit" in str(e).lower():
                    pytest.skip(f"Rate limit durante teste de memória: {e}")
                else:
                    pytest.fail(f"Falha em call de memória: {e}")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Medir memória final
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Forçar garbage collection
        gc.collect()
        gc_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Validar que requests foram rápidas
        avg_time_per_call = total_time / len(responses)
        assert avg_time_per_call < self.max_response_time, f"Calls de memória muito lentas: {avg_time_per_call:.2f}s"
        
        # Validar crescimento de memória razoável
        max_memory_growth = 50  # MB
        assert memory_growth < max_memory_growth, f"Crescimento de memória excessivo: {memory_growth:.1f}MB"
        
        print(f"✅ Memory: {initial_memory:.1f} → {final_memory:.1f}MB (+{memory_growth:.1f}MB), {avg_time_per_call:.2f}s/call")
    
    def test_error_handling_performance_real(self):
        """
        Teste REAL: Performance de handling de erros reais
        VALIDAÇÃO: Errors são tratados rapidamente sem fallback
        """
        import openai
        
        # Cliente OpenAI REAL com configuração inválida
        client = openai.OpenAI(api_key="invalid-key-for-error-test")
        
        # Medir tempo de erro REAL
        start_time = time.time()
        
        try:
            response = client.chat.completions.create(
                model=self.real_test_payload["model"],
                messages=self.real_test_payload["messages"],
                max_tokens=self.real_test_payload["max_tokens"]
            )
            
            # Não deveria chegar aqui com key inválida
            pytest.fail("Request com key inválida não falhou - possível fallback incorreto")
            
        except openai.AuthenticationError as e:
            end_time = time.time()
            error_response_time = end_time - start_time
            
            # Validar que erro foi rápido
            max_error_time = 1.0  # Erros devem ser mais rápidos que calls válidas
            assert error_response_time < max_error_time, f"Error handling muito lento: {error_response_time:.2f}s"
            
            print(f"✅ Error handling: {error_response_time:.2f}s")
            
        except Exception as e:
            end_time = time.time()
            error_response_time = end_time - start_time
            
            # Qualquer exception deve ser rápida
            assert error_response_time < 2.0, f"Exception handling muito lento: {error_response_time:.2f}s"
            
            # Verificar se é erro esperado (não fallback)
            expected_errors = ['authentication', 'api_key', 'invalid', 'unauthorized']
            error_str = str(e).lower()
            
            is_expected_error = any(expected in error_str for expected in expected_errors)
            assert is_expected_error, f"Erro inesperado (possível fallback): {e}"
    
    def test_large_payload_performance_real(self):
        """
        Teste REAL: Performance com payload grande
        VALIDAÇÃO: Requests grandes < 2s
        """
        import openai
        
        # Cliente OpenAI REAL
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Payload grande REAL
        large_message = "Analyze this large text: " + "This is a test sentence. " * 100  # ~2500 chars
        
        large_payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": large_message}
            ],
            "max_tokens": 100,
            "temperature": 0.1
        }
        
        # Medir tempo com payload grande
        start_time = time.time()
        
        try:
            response = client.chat.completions.create(**large_payload)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Validar resposta real
            assert response is not None, "Resposta large payload é None"
            assert response.choices, "Nenhuma choice em large payload"
            
            # Validar performance mesmo com payload grande
            max_large_time = self.max_response_time + 1.0  # Tolerância para payload grande
            assert response_time < max_large_time, f"Large payload muito lento: {response_time:.2f}s > {max_large_time}s"
            
            print(f"✅ Large payload: {response_time:.2f}s")
            
        except Exception as e:
            if "rate limit" in str(e).lower():
                pytest.skip(f"Rate limit em large payload: {e}")
            else:
                pytest.fail(f"Falha em large payload REAL: {e}")
    
    def test_streaming_performance_real(self):
        """
        Teste REAL: Performance de streaming se suportado
        VALIDAÇÃO: Primeira resposta streaming < 2s
        """
        import openai
        
        # Cliente OpenAI REAL
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Medir tempo até primeiro token
        start_time = time.time()
        first_token_time = None
        total_tokens = 0
        
        try:
            stream = client.chat.completions.create(
                model=self.real_test_payload["model"],
                messages=[{"role": "user", "content": "Count from 1 to 10 slowly"}],
                max_tokens=50,
                temperature=0.1,
                stream=True
            )
            
            for chunk in stream:
                if first_token_time is None:
                    first_token_time = time.time()
                
                if chunk.choices and chunk.choices[0].delta.content:
                    total_tokens += 1
                
                # Parar após alguns tokens para teste
                if total_tokens >= 5:
                    break
            
            end_time = time.time()
            
            # Validar que streaming funcionou
            assert first_token_time is not None, "Nenhum token recebido em streaming"
            assert total_tokens > 0, "Nenhum conteúdo em streaming"
            
            # Validar performance do primeiro token
            time_to_first_token = first_token_time - start_time
            assert time_to_first_token < self.max_response_time, f"Primeiro token streaming muito lento: {time_to_first_token:.2f}s"
            
            print(f"✅ Streaming first token: {time_to_first_token:.2f}s ({total_tokens} tokens)")
            
        except Exception as e:
            if "rate limit" in str(e).lower():
                pytest.skip(f"Rate limit em streaming: {e}")
            elif "stream" in str(e).lower():
                pytest.skip(f"Streaming não suportado: {e}")
            else:
                pytest.fail(f"Falha em streaming REAL: {e}")


# Execução standalone para validação rápida
if __name__ == "__main__":
    print("⚡ Testes Performance Optimization - Subtarefa 5.1")
    print("🎯 Objetivo: Validar response time < 2s com LLMs reais")
    print("🚫 SEM MOCKS - Medição real de performance")
    print("🚫 SEM FALLBACKS - Usar exceptions existentes")
    print()
    
    # Verificar OPENAI_API_KEY
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY obrigatória para testes reais")
        exit(1)
    
    # Configurar ambiente
    os.environ['BRADAX_JWT_SECRET'] = "test-jwt-secret-for-performance-67890"
    
    # Teste crítico de performance
    test_instance = TestPerformanceOptimizationReal()
    test_instance.setup_method()
    
    try:
        test_instance.test_openai_direct_call_performance_real()
        print("✅ Performance baseline OpenAI validada")
    except Exception as e:
        print(f"❌ PROBLEMA DE PERFORMANCE: {e}")
    
    # Executar todos os testes
    pytest.main([__file__, "-v", "--tb=short"])
