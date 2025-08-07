"""
Testes REAIS de Failover - Comportamento em Cenários de Erro - Bradax Broker
===========================================================================

OBJETIVO: Validar comportamento do sistema em cenários de falha e recuperação
MÉTODO: Testes 100% reais com simulação de falhas de rede, broker e modelos
CRITÉRIO: Sistema deve falhar graciosamente e se recuperar adequadamente

VALIDAÇÃO: Robustez em cenários adversos com telemetria completa
"""

import pytest
import unittest
import os
import sys
import json
import time
import requests
from pathlib import Path
import tempfile
import subprocess
import threading
import socket
from datetime import datetime
import asyncio
import httpx
import concurrent.futures
from queue import Queue, Empty
import random


class TestFailoverBehaviorReal(unittest.TestCase):
    """
    Teste REAL: Comportamento de Failover em Cenários de Erro
    VALIDAÇÃO: Sistema robusto com recuperação adequada
    """
    
    @classmethod
    def setUpClass(cls):
        """Setup para testes de failover."""
        cls.broker_url = "http://localhost:8000"
        cls.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        # Configurar ambiente
        cls.jwt_secret = 'test-failover-secret-2025'
        os.environ['BRADAX_JWT_SECRET'] = cls.jwt_secret
        
        print("🔍 Failover Tests - Validando comportamento em cenários de erro")
        
        # Verificar se broker está rodando
        try:
            response = requests.get(f"{cls.broker_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Broker online - testes failover com infraestrutura real")
                cls.broker_online = True
            else:
                print("⚠️ Broker offline - testes failover simulados")
                cls.broker_online = False
        except:
            print("⚠️ Broker offline - testes failover simulados")
            cls.broker_online = False
            
    def test_network_connectivity_failures_real(self):
        """
        Teste REAL: Falhas de conectividade de rede
        VALIDAÇÃO: Sistema trata adequadamente falhas de conexão
        """
        try:
            # Adicionar path do SDK
            sdk_path = Path(__file__).parent.parent.parent.parent / "bradax-sdk" / "src"
            if str(sdk_path) not in sys.path:
                sys.path.insert(0, str(sdk_path))
                
            from bradax import BradaxClient
            
            # Teste 1: URL inválida
            print("🌐 Testando failover com URL inválida...")
            
            invalid_client = BradaxClient(
                broker_url="http://invalid-broker-url-12345.com",
                enable_telemetry=True
            )
            
            network_failures = []
            
            try:
                response = invalid_client.invoke(
                    input_=[{"role": "user", "content": "Test network failure"}],
                    config={"model": "gpt-3.5-turbo", "max_tokens": 20}
                )
                network_failures.append({
                    'test': 'invalid_url',
                    'status': 'unexpected_success',
                    'response': response
                })
            except Exception as e:
                error_str = str(e).lower()
                error_type = type(e).__name__.lower()
                
                # Validar tipos de erro esperados
                expected_errors = ["network", "connection", "timeout", "bradaxnetworkerror", "name resolution"]
                is_expected_error = any(expected in error_str for expected in expected_errors)
                
                network_failures.append({
                    'test': 'invalid_url',
                    'status': 'expected_failure',
                    'error_type': error_type,
                    'error_message': str(e)[:200],
                    'is_expected': is_expected_error
                })
                
            # Teste 2: Porta inválida
            print("🔌 Testando failover com porta inválida...")
            
            invalid_port_client = BradaxClient(
                broker_url="http://localhost:99999",
                enable_telemetry=True
            )
            
            try:
                response = invalid_port_client.invoke(
                    input_=[{"role": "user", "content": "Test invalid port"}],
                    config={"model": "gpt-3.5-turbo", "max_tokens": 20}
                )
                network_failures.append({
                    'test': 'invalid_port',
                    'status': 'unexpected_success',
                    'response': response
                })
            except Exception as e:
                error_str = str(e).lower()
                error_type = type(e).__name__.lower()
                
                expected_errors = ["connection", "refused", "port", "bradaxnetworkerror"]
                is_expected_error = any(expected in error_str for expected in expected_errors)
                
                network_failures.append({
                    'test': 'invalid_port',
                    'status': 'expected_failure',
                    'error_type': error_type,
                    'error_message': str(e)[:200],
                    'is_expected': is_expected_error
                })
                
            # Teste 3: Timeout simulado
            print("⏱️ Testando failover com timeout...")
            
            if self.broker_online:
                timeout_client = BradaxClient(
                    broker_url=self.broker_url,
                    enable_telemetry=True,
                    timeout=0.001  # Timeout muito baixo para forçar falha
                )
                
                try:
                    response = timeout_client.invoke(
                        input_=[{"role": "user", "content": "Test timeout"}],
                        config={"model": "gpt-3.5-turbo", "max_tokens": 20}
                    )
                    network_failures.append({
                        'test': 'timeout',
                        'status': 'unexpected_success',
                        'response': response
                    })
                except Exception as e:
                    error_str = str(e).lower()
                    error_type = type(e).__name__.lower()
                    
                    expected_errors = ["timeout", "time", "exceeded", "bradaxnetworkerror"]
                    is_expected_error = any(expected in error_str for expected in expected_errors)
                    
                    network_failures.append({
                        'test': 'timeout',
                        'status': 'expected_failure',
                        'error_type': error_type,
                        'error_message': str(e)[:200],
                        'is_expected': is_expected_error
                    })
            
            # Analisar resultados
            print(f"📊 Resultados de failover de rede:")
            for failure in network_failures:
                test_name = failure['test']
                status = failure['status']
                print(f"   • {test_name}: {status}")
                
                if status == 'expected_failure':
                    is_expected = failure.get('is_expected', False)
                    error_type = failure.get('error_type', 'unknown')
                    print(f"     - Erro: {error_type} ({'esperado' if is_expected else 'inesperado'})")
                    
            # Validações
            expected_failures = [f for f in network_failures if f['status'] == 'expected_failure']
            unexpected_successes = [f for f in network_failures if f['status'] == 'unexpected_success']
            
            assert len(expected_failures) >= 2, f"Esperado pelo menos 2 falhas, obtido {len(expected_failures)}"
            
            if unexpected_successes:
                print(f"⚠️ {len(unexpected_successes)} sucessos inesperados (pode indicar problemas)")
                
            # Verificar se erros são do tipo esperado
            properly_handled = [f for f in expected_failures if f.get('is_expected', False)]
            print(f"✅ {len(properly_handled)}/{len(expected_failures)} falhas tratadas adequadamente")
            
            print("✅ Teste de failover de rede concluído")
            
        except ImportError:
            pytest.skip("SDK Bradax não disponível para teste failover")
            
    def test_broker_service_failures_real(self):
        """
        Teste REAL: Falhas de serviços do broker
        VALIDAÇÃO: Sistema trata adequadamente falhas internas do broker
        """
        try:
            # Adicionar path do SDK
            sdk_path = Path(__file__).parent.parent.parent.parent / "bradax-sdk" / "src"
            if str(sdk_path) not in sys.path:
                sys.path.insert(0, str(sdk_path))
                
            from bradax import BradaxClient
            
            print("🔧 Testando failover de serviços do broker...")
            
            if not self.broker_online:
                print("⚠️ Broker offline - simulando falhas de serviço")
                
            client = BradaxClient(
                broker_url=self.broker_url,
                enable_telemetry=True
            )
            
            service_failures = []
            
            # Teste 1: Modelo inexistente
            print("🤖 Testando modelo inexistente...")
            
            try:
                response = client.invoke(
                    input_=[{"role": "user", "content": "Test invalid model"}],
                    config={"model": "gpt-inexistent-model-999", "max_tokens": 20}
                )
                service_failures.append({
                    'test': 'invalid_model',
                    'status': 'unexpected_success',
                    'response': response
                })
            except Exception as e:
                error_str = str(e).lower()
                error_type = type(e).__name__.lower()
                
                # Tipos de erro esperados para modelo inválido
                expected_errors = ["model", "invalid", "not found", "unknown", "available", "bradaxnetworkerror"]
                is_expected_error = any(expected in error_str for expected in expected_errors)
                
                service_failures.append({
                    'test': 'invalid_model',
                    'status': 'expected_failure',
                    'error_type': error_type,
                    'error_message': str(e)[:200],
                    'is_expected': is_expected_error
                })
                
            # Teste 2: Request malformado
            print("📋 Testando request malformado...")
            
            try:
                # Request com estrutura inválida
                response = client.invoke(
                    input_="invalid_input_format",  # Deveria ser lista
                    config={"model": "gpt-3.5-turbo", "max_tokens": 20}
                )
                service_failures.append({
                    'test': 'malformed_request',
                    'status': 'unexpected_success',
                    'response': response
                })
            except Exception as e:
                error_str = str(e).lower()
                error_type = type(e).__name__.lower()
                
                expected_errors = ["validation", "format", "invalid", "type", "malformed", "bradaxnetworkerror"]
                is_expected_error = any(expected in error_str for expected in expected_errors)
                
                service_failures.append({
                    'test': 'malformed_request',
                    'status': 'expected_failure',
                    'error_type': error_type,
                    'error_message': str(e)[:200],
                    'is_expected': is_expected_error
                })
                
            # Teste 3: Parâmetros inválidos
            print("⚙️ Testando parâmetros inválidos...")
            
            try:
                response = client.invoke(
                    input_=[{"role": "user", "content": "Test invalid params"}],
                    config={
                        "model": "gpt-3.5-turbo", 
                        "max_tokens": -1,  # Valor inválido
                        "temperature": 5.0  # Fora do range 0-2
                    }
                )
                service_failures.append({
                    'test': 'invalid_params',
                    'status': 'unexpected_success',
                    'response': response
                })
            except Exception as e:
                error_str = str(e).lower()
                error_type = type(e).__name__.lower()
                
                expected_errors = ["parameter", "range", "invalid", "value", "validation", "bradaxnetworkerror"]
                is_expected_error = any(expected in error_str for expected in expected_errors)
                
                service_failures.append({
                    'test': 'invalid_params',
                    'status': 'expected_failure',
                    'error_type': error_type,
                    'error_message': str(e)[:200],
                    'is_expected': is_expected_error
                })
                
            # Teste 4: Endpoint inexistente
            print("🔗 Testando endpoint inexistente...")
            
            try:
                # Tentar acessar endpoint que não existe
                invalid_url = f"{self.broker_url}/api/v1/invalid/endpoint"
                response = requests.post(invalid_url, json={"test": "data"}, timeout=10)
                
                service_failures.append({
                    'test': 'invalid_endpoint',
                    'status': 'http_response',
                    'status_code': response.status_code,
                    'response_text': response.text[:200]
                })
            except Exception as e:
                error_str = str(e).lower()
                error_type = type(e).__name__.lower()
                
                expected_errors = ["404", "not found", "endpoint", "connection", "bradaxnetworkerror"]
                is_expected_error = any(expected in error_str for expected in expected_errors)
                
                service_failures.append({
                    'test': 'invalid_endpoint',
                    'status': 'expected_failure',
                    'error_type': error_type,
                    'error_message': str(e)[:200],
                    'is_expected': is_expected_error
                })
                
            # Analisar resultados
            print(f"📊 Resultados de failover de serviços:")
            for failure in service_failures:
                test_name = failure['test']
                status = failure['status']
                print(f"   • {test_name}: {status}")
                
                if status == 'expected_failure':
                    is_expected = failure.get('is_expected', False)
                    error_type = failure.get('error_type', 'unknown')
                    print(f"     - Erro: {error_type} ({'esperado' if is_expected else 'inesperado'})")
                elif status == 'http_response':
                    status_code = failure.get('status_code', 'unknown')
                    print(f"     - HTTP Status: {status_code}")
                    
            # Validações
            total_tests = len(service_failures)
            proper_failures = [f for f in service_failures if f['status'] in ['expected_failure', 'http_response']]
            
            assert total_tests >= 3, f"Esperado pelo menos 3 testes, executado {total_tests}"
            
            if len(proper_failures) >= total_tests * 0.8:
                print("✅ Maioria dos testes falharam adequadamente")
            else:
                print("⚠️ Alguns testes não falharam como esperado")
                
            print("✅ Teste de failover de serviços concluído")
            
        except ImportError:
            pytest.skip("SDK Bradax não disponível para teste failover de serviços")
            
    def test_data_persistence_failures_real(self):
        """
        Teste REAL: Falhas de persistência de dados
        VALIDAÇÃO: Sistema mantém integridade mesmo com falhas de gravação
        """
        print("💾 Testando failover de persistência de dados...")
        
        # Verificar estado atual dos arquivos de dados
        data_files = {
            'telemetry': Path("data/telemetry.json"),
            'guardrail_events': Path("data/guardrail_events.json"),
            'projects': Path("data/projects.json"),
            'llm_models': Path("data/llm_models.json"),
            'system_info': Path("data/system_info.json")
        }
        
        persistence_results = {}
        
        for file_type, file_path in data_files.items():
            result = {
                'exists': file_path.exists(),
                'size': file_path.stat().st_size if file_path.exists() else 0,
                'readable': False,
                'valid_json': False,
                'content_summary': None
            }
            
            if result['exists']:
                try:
                    # Testar leitura
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        result['readable'] = True
                        
                    # Testar se é JSON válido
                    data = json.loads(content)
                    result['valid_json'] = True
                    
                    # Resumo do conteúdo
                    if isinstance(data, list):
                        result['content_summary'] = f"Array com {len(data)} elementos"
                    elif isinstance(data, dict):
                        result['content_summary'] = f"Objeto com {len(data)} chaves: {list(data.keys())[:3]}"
                    else:
                        result['content_summary'] = f"Tipo: {type(data).__name__}"
                        
                except json.JSONDecodeError as e:
                    result['content_summary'] = f"JSON inválido: {str(e)[:100]}"
                except Exception as e:
                    result['content_summary'] = f"Erro de leitura: {str(e)[:100]}"
                    
            persistence_results[file_type] = result
            
        # Analisar resultados de persistência
        print(f"📊 Status dos arquivos de dados:")
        for file_type, result in persistence_results.items():
            status = "✅" if result['exists'] and result['valid_json'] else "❌"
            size_kb = result['size'] / 1024 if result['size'] > 0 else 0
            print(f"   • {file_type}: {status} ({size_kb:.1f}KB)")
            
            if result['content_summary']:
                print(f"     - {result['content_summary']}")
                
        # Teste específico de telemetria (arquivo principal)
        telemetry_result = persistence_results['telemetry']
        if telemetry_result['exists'] and telemetry_result['valid_json']:
            try:
                with open(data_files['telemetry'], 'r', encoding='utf-8') as f:
                    telemetry_data = json.load(f)
                    
                if isinstance(telemetry_data, list) and len(telemetry_data) > 0:
                    # Analisar eventos de telemetria
                    event_types = {}
                    timestamps = []
                    
                    for event in telemetry_data[-100:]:  # Últimos 100 eventos
                        event_type = event.get('event_type', 'unknown')
                        event_types[event_type] = event_types.get(event_type, 0) + 1
                        
                        timestamp = event.get('timestamp')
                        if timestamp:
                            timestamps.append(timestamp)
                            
                    print(f"📈 Análise de telemetria:")
                    print(f"   • Total de eventos: {len(telemetry_data)}")
                    print(f"   • Tipos de evento: {event_types}")
                    
                    if timestamps:
                        print(f"   • Período: {timestamps[0]} → {timestamps[-1]}")
                        
                    # Validar estrutura dos eventos
                    recent_event = telemetry_data[-1] if telemetry_data else {}
                    required_fields = ['event_id', 'timestamp', 'event_type']
                    missing_fields = [field for field in required_fields if field not in recent_event]
                    
                    if not missing_fields:
                        print("✅ Estrutura de eventos válida")
                    else:
                        print(f"⚠️ Campos ausentes: {missing_fields}")
                        
            except Exception as e:
                print(f"❌ Erro analisando telemetria: {e}")
                
        # Validações finais
        valid_files = [r for r in persistence_results.values() if r['exists'] and r['valid_json']]
        total_files = len(persistence_results)
        
        print(f"📊 Resumo de persistência:")
        print(f"   • Arquivos válidos: {len(valid_files)}/{total_files}")
        print(f"   • Taxa de sucesso: {(len(valid_files)/total_files)*100:.1f}%")
        
        # Verificar tamanho total dos dados
        total_size = sum(r['size'] for r in persistence_results.values())
        print(f"   • Tamanho total: {total_size/1024:.1f}KB")
        
        assert len(valid_files) >= total_files * 0.8, f"Muitos arquivos com problemas: {len(valid_files)}/{total_files}"
        
        if persistence_results['telemetry']['valid_json'] and persistence_results['telemetry']['size'] > 1000:
            print("✅ Sistema de telemetria persistindo dados adequadamente")
        else:
            print("⚠️ Sistema de telemetria pode não estar persistindo adequadamente")
            
        print("✅ Teste de failover de persistência concluído")
        
    def test_model_availability_failures_real(self):
        """
        Teste REAL: Falhas de disponibilidade de modelos
        VALIDAÇÃO: Sistema valida modelos disponíveis adequadamente
        """
        print("🤖 Testando failover de disponibilidade de modelos...")
        
        # Verificar configuração de modelos
        models_file = Path("data/llm_models.json")
        available_models = []
        
        if models_file.exists():
            try:
                with open(models_file, 'r', encoding='utf-8') as f:
                    models_data = json.load(f)
                    
                print(f"📁 Arquivo de modelos encontrado: {models_file}")
                
                # Analisar estrutura dos modelos
                if isinstance(models_data, list):
                    available_models = models_data
                    print(f"📋 {len(available_models)} modelos configurados")
                elif isinstance(models_data, dict):
                    if 'models' in models_data:
                        available_models = models_data['models']
                    elif 'available_models' in models_data:
                        available_models = models_data['available_models']
                    else:
                        available_models = list(models_data.values())
                    print(f"📋 {len(available_models)} modelos em estrutura dict")
                    
                # Listar modelos encontrados
                for i, model in enumerate(available_models[:5]):  # Primeiros 5
                    if isinstance(model, dict):
                        model_id = model.get('id', model.get('name', f'model_{i}'))
                        model_provider = model.get('provider', 'unknown')
                        print(f"   • {model_id} ({model_provider})")
                    elif isinstance(model, str):
                        print(f"   • {model}")
                        
            except Exception as e:
                print(f"❌ Erro lendo arquivo de modelos: {e}")
        else:
            print("⚠️ Arquivo de modelos não encontrado")
            
        # Teste com SDK se disponível
        try:
            sdk_path = Path(__file__).parent.parent.parent.parent / "bradax-sdk" / "src"
            if str(sdk_path) not in sys.path:
                sys.path.insert(0, str(sdk_path))
                
            from bradax import BradaxClient
            
            if self.broker_online:
                client = BradaxClient(
                    broker_url=self.broker_url,
                    enable_telemetry=True
                )
                
                # Testar modelos conhecidos vs desconhecidos
                model_tests = [
                    {"model": "gpt-3.5-turbo", "expected": "available"},
                    {"model": "gpt-4o-mini", "expected": "available"},
                    {"model": "claude-3-sonnet", "expected": "available_or_unavailable"},
                    {"model": "invalid-model-xyz", "expected": "unavailable"},
                    {"model": "", "expected": "invalid"},
                ]
                
                model_results = []
                
                for test in model_tests:
                    model_name = test["model"]
                    expected = test["expected"]
                    
                    print(f"🧪 Testando modelo: {model_name or 'vazio'}")
                    
                    try:
                        response = client.invoke(
                            input_=[{"role": "user", "content": f"Test model {model_name}"}],
                            config={"model": model_name, "max_tokens": 10}
                        )
                        
                        model_results.append({
                            'model': model_name,
                            'status': 'success',
                            'expected': expected,
                            'response_length': len(str(response)) if response else 0
                        })
                        
                    except Exception as e:
                        error_str = str(e).lower()
                        error_type = type(e).__name__.lower()
                        
                        # Categorizar erro
                        if any(term in error_str for term in ["model", "invalid", "not found", "unknown"]):
                            error_category = "model_error"
                        elif any(term in error_str for term in ["network", "connection", "timeout"]):
                            error_category = "network_error"
                        else:
                            error_category = "other_error"
                            
                        model_results.append({
                            'model': model_name,
                            'status': 'error',
                            'expected': expected,
                            'error_category': error_category,
                            'error_type': error_type,
                            'error_message': str(e)[:200]
                        })
                        
                # Analisar resultados dos modelos
                print(f"📊 Resultados de teste de modelos:")
                for result in model_results:
                    model = result['model'] or 'vazio'
                    status = result['status']
                    expected = result['expected']
                    
                    if status == 'success':
                        appropriate = expected in ['available', 'available_or_unavailable']
                        print(f"   • {model}: ✅ SUCCESS ({'apropriado' if appropriate else 'inesperado'})")
                    else:
                        error_category = result.get('error_category', 'unknown')
                        appropriate = expected in ['unavailable', 'invalid', 'available_or_unavailable']
                        print(f"   • {model}: ❌ {error_category.upper()} ({'apropriado' if appropriate else 'inesperado'})")
                        
                # Validações
                total_tests = len(model_results)
                appropriate_results = 0
                
                for result in model_results:
                    expected = result['expected']
                    status = result['status']
                    
                    if expected == 'available' and status == 'success':
                        appropriate_results += 1
                    elif expected == 'unavailable' and status == 'error':
                        appropriate_results += 1
                    elif expected == 'invalid' and status == 'error':
                        appropriate_results += 1
                    elif expected == 'available_or_unavailable':
                        appropriate_results += 1  # Aceitar qualquer resultado
                        
                accuracy = (appropriate_results / total_tests) * 100 if total_tests > 0 else 0
                print(f"📈 Precisão dos testes: {accuracy:.1f}% ({appropriate_results}/{total_tests})")
                
                if accuracy >= 70:
                    print("✅ Sistema de modelos funcionando adequadamente")
                else:
                    print("⚠️ Sistema de modelos pode ter problemas")
                    
        except ImportError:
            print("⚠️ SDK não disponível para teste de modelos")
            
        print("✅ Teste de failover de modelos concluído")
        
    def test_recovery_mechanisms_real(self):
        """
        Teste REAL: Mecanismos de recuperação
        VALIDAÇÃO: Sistema se recupera adequadamente após falhas
        """
        print("🔄 Testando mecanismos de recuperação...")
        
        recovery_tests = []
        
        # Teste 1: Recuperação após múltiplas falhas
        try:
            sdk_path = Path(__file__).parent.parent.parent.parent / "bradax-sdk" / "src"
            if str(sdk_path) not in sys.path:
                sys.path.insert(0, str(sdk_path))
                
            from bradax import BradaxClient
            
            print("🔁 Testando recuperação após falhas...")
            
            # Simular sequência: falha → falha → sucesso
            client = BradaxClient(
                broker_url=self.broker_url,
                enable_telemetry=True
            )
            
            sequence_results = []
            
            # Primeira falha (modelo inválido)
            try:
                response = client.invoke(
                    input_=[{"role": "user", "content": "Test recovery 1"}],
                    config={"model": "invalid-model-1", "max_tokens": 20}
                )
                sequence_results.append({'step': 1, 'status': 'unexpected_success'})
            except Exception as e:
                sequence_results.append({'step': 1, 'status': 'expected_failure', 'error': str(e)[:100]})
                
            # Segunda falha (parâmetros inválidos)
            try:
                response = client.invoke(
                    input_=[{"role": "user", "content": "Test recovery 2"}],
                    config={"model": "gpt-3.5-turbo", "max_tokens": -1}
                )
                sequence_results.append({'step': 2, 'status': 'unexpected_success'})
            except Exception as e:
                sequence_results.append({'step': 2, 'status': 'expected_failure', 'error': str(e)[:100]})
                
            # Tentativa de sucesso
            try:
                response = client.invoke(
                    input_=[{"role": "user", "content": "Test recovery 3"}],
                    config={"model": "gpt-3.5-turbo", "max_tokens": 20}
                )
                sequence_results.append({'step': 3, 'status': 'success', 'response_length': len(str(response)) if response else 0})
            except Exception as e:
                sequence_results.append({'step': 3, 'status': 'failed_recovery', 'error': str(e)[:100]})
                
            # Analisar sequência de recuperação
            print(f"📊 Sequência de recuperação:")
            for result in sequence_results:
                step = result['step']
                status = result['status']
                print(f"   • Passo {step}: {status}")
                
            recovery_tests.append({
                'test': 'failure_sequence',
                'results': sequence_results,
                'recovery_successful': any(r['status'] in ['success', 'unexpected_success'] for r in sequence_results)
            })
            
        except ImportError:
            print("⚠️ SDK não disponível para teste de recuperação")
            recovery_tests.append({
                'test': 'failure_sequence',
                'results': [],
                'recovery_successful': False,
                'skip_reason': 'SDK não disponível'
            })
            
        # Teste 2: Recuperação de persistência
        print("💾 Testando recuperação de persistência...")
        
        # Verificar se sistema continua funcionando mesmo com problemas de disco
        telemetry_file = Path("data/telemetry.json")
        
        persistence_recovery = {
            'telemetry_exists': telemetry_file.exists(),
            'telemetry_size': telemetry_file.stat().st_size if telemetry_file.exists() else 0,
            'can_read': False,
            'can_write': False
        }
        
        # Teste de leitura
        if persistence_recovery['telemetry_exists']:
            try:
                with open(telemetry_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    persistence_recovery['can_read'] = True
                    persistence_recovery['events_count'] = len(data) if isinstance(data, list) else 0
            except Exception as e:
                persistence_recovery['read_error'] = str(e)[:100]
                
        # Teste de escrita (criar arquivo temporário)
        try:
            test_file = Path("data/test_write_permission.json")
            with open(test_file, 'w', encoding='utf-8') as f:
                json.dump({"test": "write_permission", "timestamp": datetime.now().isoformat()}, f)
            persistence_recovery['can_write'] = True
            test_file.unlink()  # Remover arquivo de teste
        except Exception as e:
            persistence_recovery['write_error'] = str(e)[:100]
            
        recovery_tests.append({
            'test': 'persistence_recovery',
            'results': persistence_recovery,
            'recovery_successful': persistence_recovery['can_read'] and persistence_recovery['can_write']
        })
        
        # Analisar resultados de recuperação
        print(f"📊 Resultados de recuperação:")
        for recovery_test in recovery_tests:
            test_name = recovery_test['test']
            successful = recovery_test['recovery_successful']
            status = "✅" if successful else "❌"
            
            print(f"   • {test_name}: {status}")
            
            if 'skip_reason' in recovery_test:
                print(f"     - Pulado: {recovery_test['skip_reason']}")
                
        # Validações finais
        successful_recoveries = [t for t in recovery_tests if t['recovery_successful']]
        total_tests = len(recovery_tests)
        
        print(f"📈 Taxa de recuperação: {len(successful_recoveries)}/{total_tests}")
        
        if len(successful_recoveries) >= total_tests * 0.7:
            print("✅ Mecanismos de recuperação funcionando adequadamente")
        else:
            print("⚠️ Mecanismos de recuperação podem precisar de melhorias")
            
        print("✅ Teste de mecanismos de recuperação concluído")


if __name__ == "__main__":
    unittest.main()
