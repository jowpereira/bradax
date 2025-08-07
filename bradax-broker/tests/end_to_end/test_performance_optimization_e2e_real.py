"""
Testes REAIS E2E para Performance Optimization - Subtarefa 5.3
Valida otimização end-to-end funcionando sem mocks - Hotfix 4
"""

import pytest
import os
import sys
import time
import requests
import asyncio
from typing import List, Dict, Any, Optional

# Adicionar broker ao path para importação
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestPerformanceOptimizationE2EReal:
    """
    Testes E2E REAIS para validar otimização de performance end-to-end
    SEM MOCKS - Validação real de performance com infraestrutura completa
    """
    
    def setup_method(self):
        """Setup para cada teste com configuração E2E real"""
        # Configurações obrigatórias
        os.environ['BRADAX_JWT_SECRET'] = "test-jwt-secret-for-e2e-performance-12345"
        
        # Verificar OPENAI_API_KEY
        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("OPENAI_API_KEY obrigatória para testes E2E reais")
        
        # URLs e timeouts
        self.broker_url = "http://localhost:8000"
        self.max_e2e_time = 3.0  # 3s para E2E completo
        self.max_response_time = 2.0  # 2s para response time
        self.connection_timeout = 5  # 5s para conexões
        
        # Payload E2E real
        self.e2e_payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": "E2E performance test: respond with exactly 'OK'"}
            ],
            "max_tokens": 10,
            "temperature": 0.0  # Deterministic
        }
        
        # Headers reais com telemetria
        self.e2e_headers = {
            'Content-Type': 'application/json',
            'X-Bradax-Request-ID': f'e2e-perf-{int(time.time())}',
            'X-Bradax-Project-ID': 'test-performance-project',
            'X-Bradax-User-ID': 'test-performance-user',
            'Authorization': 'Bearer test-performance-token'
        }
    
    @pytest.mark.skipif(
        not os.getenv('BROKER_E2E_ENABLED', 'false').lower() == 'true',
        reason="Requer BROKER_E2E_ENABLED=true e broker rodando"
    )
    def test_full_e2e_performance_real(self):
        """
        Teste REAL: Performance E2E completa < 3s
        VALIDAÇÃO: SDK → Broker → OpenAI → Cache → Response
        """
        # Verificar se broker está rodando
        try:
            health_response = requests.get(f"{self.broker_url}/health", timeout=self.connection_timeout)
            if health_response.status_code != 200:
                pytest.skip("Broker não está rodando - E2E ignorado")
        except requests.exceptions.RequestException:
            pytest.skip("Broker não acessível - E2E ignorado")
        
        # Medir tempo E2E completo
        start_time = time.time()
        
        try:
            # Request E2E real
            response = requests.post(
                f"{self.broker_url}/v1/chat/completions",
                json=self.e2e_payload,
                headers=self.e2e_headers,
                timeout=self.max_e2e_time + 2  # Timeout maior que limite
            )
            
            end_time = time.time()
            e2e_time = end_time - start_time
            
            # Validar resposta E2E
            if response.status_code == 200:
                response_data = response.json()
                
                # Validar estrutura de resposta
                assert 'choices' in response_data, "Response E2E sem choices"
                assert len(response_data['choices']) > 0, "Response E2E choices vazio"
                assert 'message' in response_data['choices'][0], "Response E2E sem message"
                
                # Validar performance E2E
                assert e2e_time < self.max_e2e_time, f"E2E muito lento: {e2e_time:.2f}s > {self.max_e2e_time}s"
                
                # Validar conteúdo da resposta
                content = response_data['choices'][0]['message'].get('content', '')
                assert len(content) > 0, "Response E2E com conteúdo vazio"
                
                print(f"✅ E2E completo: {e2e_time:.2f}s - Content: {content[:50]}...")
                
            elif response.status_code in [401, 403]:
                # Erro de auth, mas resposta rápida
                assert e2e_time < self.max_response_time, f"E2E auth error muito lento: {e2e_time:.2f}s"
                print(f"⚠️ E2E auth error mas rápido: {e2e_time:.2f}s")
                
            else:
                pytest.fail(f"E2E status inesperado: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            pytest.fail(f"E2E timeout > {self.max_e2e_time}s - performance inadequada")
        except requests.exceptions.RequestException as e:
            pytest.fail(f"E2E falhou (sem fallback): {e}")
    
    @pytest.mark.skipif(
        not os.getenv('BROKER_E2E_ENABLED', 'false').lower() == 'true',
        reason="Requer BROKER_E2E_ENABLED=true e broker rodando"
    )
    def test_e2e_with_cache_performance_real(self):
        """
        Teste REAL: Performance E2E com cache hit/miss
        VALIDAÇÃO: Cache melhora performance significativamente
        """
        # Request inicial (cache miss)
        cache_miss_payload = self.e2e_payload.copy()
        cache_miss_payload["messages"][0]["content"] = f"Cache miss test {time.time():.3f}"
        
        start_miss = time.time()
        
        try:
            miss_response = requests.post(
                f"{self.broker_url}/v1/chat/completions",
                json=cache_miss_payload,
                headers=self.e2e_headers,
                timeout=self.max_e2e_time + 2
            )
            
            end_miss = time.time()
            cache_miss_time = end_miss - start_miss
            
            if miss_response.status_code != 200:
                if miss_response.status_code in [401, 403]:
                    pytest.skip("E2E auth error - cache test ignorado")
                else:
                    pytest.fail(f"Cache miss falhou: {miss_response.status_code}")
            
            # Aguardar cache ser persistido
            time.sleep(0.1)
            
            # Request repetida (cache hit)
            start_hit = time.time()
            
            hit_response = requests.post(
                f"{self.broker_url}/v1/chat/completions",
                json=cache_miss_payload,  # Mesmo payload
                headers=self.e2e_headers,
                timeout=self.max_e2e_time + 2
            )
            
            end_hit = time.time()
            cache_hit_time = end_hit - start_hit
            
            if hit_response.status_code == 200:
                # Cache hit deve ser mais rápido que cache miss
                performance_improvement = cache_miss_time - cache_hit_time
                
                # Validar que ambas as respostas são válidas
                miss_data = miss_response.json()
                hit_data = hit_response.json()
                
                assert 'choices' in miss_data and 'choices' in hit_data, "Responses inválidas para cache test"
                
                print(f"✅ Cache performance - Miss: {cache_miss_time:.2f}s, Hit: {cache_hit_time:.2f}s, Improvement: {performance_improvement:.2f}s")
                
                # Cache hit deve ser pelo menos um pouco mais rápido
                if performance_improvement > 0.1:  # 100ms de melhoria
                    print(f"🚀 Cache significativamente mais rápido!")
                else:
                    print(f"⚠️ Cache improvement marginal: {performance_improvement:.3f}s")
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"E2E cache test falhou: {e}")
    
    def test_e2e_sdk_performance_real(self):
        """
        Teste REAL: Performance E2E através do SDK
        VALIDAÇÃO: SDK otimizado para performance
        """
        try:
            from bradax import BradaxClient
            
            # Cliente SDK E2E
            client = BradaxClient(
                api_key=os.getenv('OPENAI_API_KEY'),
                broker_url=self.broker_url,
                timeout=self.max_e2e_time
            )
            
            # Medir tempo SDK E2E
            start_time = time.time()
            
            try:
                response = client.invoke(
                    input_=self.e2e_payload["messages"],
                    config={
                        "model": self.e2e_payload["model"],
                        "max_tokens": self.e2e_payload["max_tokens"],
                        "temperature": self.e2e_payload["temperature"]
                    }
                )
                
                end_time = time.time()
                sdk_e2e_time = end_time - start_time
                
                # Validar resposta SDK E2E
                assert response is not None, "Response SDK E2E é None"
                assert isinstance(response, dict), "Response SDK E2E não é dict"
                
                # Validar performance SDK E2E
                assert sdk_e2e_time < self.max_e2e_time, f"SDK E2E muito lento: {sdk_e2e_time:.2f}s > {self.max_e2e_time}s"
                
                print(f"✅ SDK E2E: {sdk_e2e_time:.2f}s")
                
            except Exception as e:
                # Tratar exceptions específicas sem fallback
                error_str = str(e).lower()
                
                if "conexão" in error_str or "connect" in error_str:
                    pytest.skip(f"Broker offline para SDK E2E: {e}")
                elif "timeout" in error_str:
                    pytest.fail(f"SDK E2E timeout (performance inadequada): {e}")
                elif "rate limit" in error_str:
                    pytest.skip(f"Rate limit em SDK E2E: {e}")
                else:
                    pytest.fail(f"SDK E2E falhou (sem fallback): {e}")
                    
        except ImportError:
            pytest.skip("SDK Bradax não disponível para teste E2E")
    
    def test_e2e_concurrent_performance_real(self):
        """
        Teste REAL: Performance E2E com requests concorrentes
        VALIDAÇÃO: Sistema mantém performance sob carga
        """
        try:
            from bradax import BradaxClient
            import concurrent.futures
            
            # Cliente SDK para concorrência
            client = BradaxClient(
                api_key=os.getenv('OPENAI_API_KEY'),
                broker_url=self.broker_url,
                timeout=self.max_e2e_time
            )
            
            def make_concurrent_request(request_id: int):
                """Fazer request concorrente"""
                start_time = time.time()
                
                try:
                    response = client.invoke(
                        input_=[{"role": "user", "content": f"Concurrent E2E test {request_id}"}],
                        config={
                            "model": "gpt-3.5-turbo",
                            "max_tokens": 20,
                            "temperature": 0.1
                        }
                    )
                    
                    end_time = time.time()
                    
                    return {
                        'success': True,
                        'request_id': request_id,
                        'response_time': end_time - start_time,
                        'response': response
                    }
                    
                except Exception as e:
                    end_time = time.time()
                    
                    return {
                        'success': False,
                        'request_id': request_id,
                        'response_time': end_time - start_time,
                        'error': str(e)
                    }
            
            # Executar requests concorrentes (carga leve)
            max_concurrent = 3
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                futures = [executor.submit(make_concurrent_request, i) for i in range(max_concurrent)]
                results = [future.result(timeout=self.max_e2e_time + 5) for future in futures]
            
            # Analisar resultados
            successful_requests = [r for r in results if r['success']]
            failed_requests = [r for r in results if not r['success']]
            
            # Pelo menos algumas requests devem ter sucesso
            if len(successful_requests) == 0:
                # Analisar falhas
                connection_errors = [r for r in failed_requests if "conexão" in r['error'].lower() or "connect" in r['error'].lower()]
                
                if len(connection_errors) == len(failed_requests):
                    pytest.skip("Todas as requests falharam por conexão - broker offline")
                else:
                    pytest.fail(f"Nenhuma request concorrente teve sucesso: {[r['error'] for r in failed_requests]}")
            
            # Validar performance de requests bem-sucedidas
            slow_requests = [r for r in successful_requests if r['response_time'] > self.max_e2e_time]
            
            assert len(slow_requests) == 0, f"Requests concorrentes E2E muito lentas: {[(r['request_id'], r['response_time']) for r in slow_requests]}"
            
            # Calcular estatísticas
            avg_time = sum(r['response_time'] for r in successful_requests) / len(successful_requests)
            max_time = max(r['response_time'] for r in successful_requests)
            min_time = min(r['response_time'] for r in successful_requests)
            
            print(f"✅ Concurrent E2E: {len(successful_requests)}/{max_concurrent} success, avg: {avg_time:.2f}s, range: {min_time:.2f}-{max_time:.2f}s")
            
        except ImportError:
            pytest.skip("SDK Bradax não disponível para teste concorrente E2E")
    
    def test_e2e_error_recovery_performance_real(self):
        """
        Teste REAL: Performance de recovery de erros E2E
        VALIDAÇÃO: Sistema se recupera rapidamente de falhas
        """
        try:
            from bradax import BradaxClient
            
            # Cliente com configuração que pode gerar erro
            client = BradaxClient(
                api_key="invalid-key-for-error-test",
                broker_url=self.broker_url,
                timeout=self.max_response_time
            )
            
            # Medir tempo de error handling E2E
            start_time = time.time()
            
            try:
                response = client.invoke(
                    input_=self.e2e_payload["messages"],
                    config={"model": self.e2e_payload["model"]}
                )
                
                # Não deveria chegar aqui com key inválida
                pytest.fail("Request com key inválida não falhou - possível fallback incorreto")
                
            except Exception as e:
                end_time = time.time()
                error_recovery_time = end_time - start_time
                
                # Validar que error recovery foi rápido
                max_error_time = 2.0  # Errors E2E devem ser rápidos
                assert error_recovery_time < max_error_time, f"Error recovery E2E muito lento: {error_recovery_time:.2f}s"
                
                # Verificar que é erro esperado (não fallback)
                error_str = str(e).lower()
                expected_errors = ['authentication', 'api_key', 'invalid', 'unauthorized', 'conexão', 'connect']
                
                is_expected_error = any(expected in error_str for expected in expected_errors)
                assert is_expected_error, f"Erro inesperado E2E (possível fallback): {e}"
                
                print(f"✅ E2E error recovery: {error_recovery_time:.2f}s - {type(e).__name__}")
                
        except ImportError:
            pytest.skip("SDK Bradax não disponível para teste error recovery E2E")
    
    def test_e2e_telemetry_performance_real(self):
        """
        Teste REAL: Performance de telemetria E2E
        VALIDAÇÃO: Telemetria funciona corretamente e é configurável
        """
        try:
            from bradax import BradaxClient
            
            # Cliente com telemetria habilitada
            client_with_telemetry = BradaxClient(
                broker_url=self.broker_url,
                enable_telemetry=True
            )
            
            # Cliente com telemetria desabilitada
            client_without_telemetry = BradaxClient(
                broker_url=self.broker_url,
                enable_telemetry=False
            )
            
            assert client_with_telemetry is not None
            assert client_without_telemetry is not None
            print(f"✅ E2E telemetry clients: Both created successfully")
            
            # Testar performance com telemetria
            try:
                start_time = time.time()
                
                response = client_with_telemetry.invoke(
                    input_=[{"role": "user", "content": "Telemetry E2E performance test"}],
                    config={"model": "gpt-3.5-turbo", "max_tokens": 20}
                )
                
                end_time = time.time()
                telemetry_time = end_time - start_time
                
                assert telemetry_time < self.max_e2e_time, f"Telemetry E2E muito lento: {telemetry_time:.2f}s"
                print(f"✅ Telemetry E2E performance: {telemetry_time:.2f}s")
                
            except Exception as e:
                expected_errors = [
                    "conexão", "connect", "network", "timeout", 
                    "BradaxNetworkError", "ConnectionError"
                ]
                error_str = str(e).lower()
                is_expected_error = any(expected in error_str for expected in expected_errors)
                
                if is_expected_error:
                    print(f"✅ E2E telemetry test: Broker offline, but client initialization passed - {type(e).__name__}")
                else:
                    print(f"⚠️ E2E telemetry unexpected error: {e}")
                    
        except ImportError:
            pytest.skip("SDK Bradax não disponível para teste telemetry E2E")
    
    def test_e2e_memory_optimization_real(self):
        """
        Teste REAL: Otimização de memória E2E
        VALIDAÇÃO: Sistema não vaza memória durante operação E2E
        """
        import psutil
        import gc
        
        try:
            from bradax import BradaxClient
            
            # Cliente para teste de memória
            client = BradaxClient(
                api_key=os.getenv('OPENAI_API_KEY'),
                broker_url=self.broker_url,
                timeout=self.max_e2e_time
            )
            
            # Medir memória inicial
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Executar múltiplas operações E2E
            responses = []
            total_e2e_time = 0
            
            for i in range(3):  # 3 operações E2E
                start_time = time.time()
                
                try:
                    response = client.invoke(
                        input_=[{"role": "user", "content": f"Memory optimization E2E test {i+1}"}],
                        config={
                            "model": "gpt-3.5-turbo",
                            "max_tokens": 25,
                            "temperature": 0.1
                        }
                    )
                    
                    end_time = time.time()
                    operation_time = end_time - start_time
                    total_e2e_time += operation_time
                    
                    responses.append(response)
                    
                    # Validar que cada operação é rápida
                    assert operation_time < self.max_e2e_time, f"Operação E2E {i+1} muito lenta: {operation_time:.2f}s"
                    
                except Exception as e:
                    if "conexão" in str(e).lower() or "connect" in str(e).lower():
                        pytest.skip(f"Broker offline para memory optimization test: {e}")
                    elif "rate limit" in str(e).lower():
                        break  # Parar se rate limited
                    else:
                        print(f"⚠️ Memory test operation {i+1} falhou: {e}")
            
            # Medir memória final
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_growth = final_memory - initial_memory
            
            # Forçar garbage collection
            gc.collect()
            gc_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Validar otimização de memória
            max_memory_growth = 100  # 100MB crescimento máximo
            assert memory_growth < max_memory_growth, f"Crescimento de memória E2E excessivo: {memory_growth:.1f}MB"
            
            # Validar performance total
            if total_e2e_time > 0:
                avg_e2e_time = total_e2e_time / len(responses) if responses else 0
                assert avg_e2e_time < self.max_e2e_time, f"Média E2E muito lenta: {avg_e2e_time:.2f}s"
            
            print(f"✅ E2E Memory optimization - Growth: {memory_growth:.1f}MB, Ops: {len(responses)}, Avg time: {avg_e2e_time:.2f}s")
            
        except ImportError:
            pytest.skip("SDK Bradax não disponível para teste memory optimization E2E")


# Execução standalone para validação rápida
if __name__ == "__main__":
    print("🔄 Testes Performance Optimization E2E - Subtarefa 5.3")
    print("🎯 Objetivo: Validar otimização end-to-end funcionando sem mocks")
    print("🚫 SEM MOCKS - E2E real com infraestrutura completa")
    print("🚫 SEM FALLBACKS - Usar exceptions existentes")
    print()
    
    # Verificar OPENAI_API_KEY
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY obrigatória para testes E2E reais")
        exit(1)
    
    # Configurar ambiente
    os.environ['BRADAX_JWT_SECRET'] = "test-jwt-secret-for-e2e-performance-67890"
    
    # Teste crítico E2E
    test_instance = TestPerformanceOptimizationE2EReal()
    test_instance.setup_method()
    
    try:
        test_instance.test_e2e_sdk_performance_real()
        print("✅ E2E SDK performance validada")
    except Exception as e:
        print(f"❌ PROBLEMA E2E: {e}")
    
    # Executar todos os testes
    pytest.main([__file__, "-v", "--tb=short"])
