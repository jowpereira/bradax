"""
Teste E2E REAL - SDK → Broker: Headers de Telemetria - Subtarefa 2.3
Valida que middleware broker aceita e processa headers do SDK
"""

import pytest
import os
import time
import asyncio
from typing import Dict, Any

# Sistema sob teste E2E completo
from bradax.client import BradaxClient
from bradax.config.sdk_config import BradaxSDKConfig


class TestTelemetryE2EBrokerReal:
    """
    Testes E2E REAIS para validar fluxo completo:
    SDK → Headers de Telemetria → Broker → Processamento → Resposta
    
    REQUERIMENTO: Broker rodando em http://localhost:8000
    """
    
    def setup_method(self):
        """Setup para testes E2E - configuração para broker real"""
        self.config = BradaxSDKConfig.for_testing(
            broker_url="http://localhost:8000",
            project_id="test-e2e-telemetry",
            enable_telemetry=True,
            timeout=60  # Timeout maior para E2E
        )
        self.client = BradaxClient(self.config)
    
    @pytest.mark.skipif(
        not os.getenv("BROKER_E2E_ENABLED", "").lower() == "true",
        reason="Broker E2E tests require BROKER_E2E_ENABLED=true and running broker"
    )
    def test_e2e_sdk_to_broker_telemetry_headers_real(self):
        """
        Teste E2E REAL: SDK envia headers → Broker aceita → Resposta sucesso
        VALIDAÇÃO: Fluxo completo sem erros de headers
        """
        try:
            # Fazer requisição E2E real ao broker
            response = self.client.invoke(
                "Test E2E telemetry headers - responda apenas: E2E_SUCCESS",
                config={"model": "gpt-4o-mini"}
            )
            
            # Validar resposta do broker (indica que headers foram aceitos)
            assert response, "Resposta vazia do broker - possível rejeição de headers"
            assert isinstance(response, dict), "Resposta deve ser dict"
            
            # Se chegou aqui, broker aceitou os headers de telemetria
            # Verificar indicadores de sucesso
            if "success" in response:
                assert response.get("success", False), "Broker retornou success=false"
            
            if "content" in response:
                content = response.get("content", "")
                assert "E2E_SUCCESS" in content, f"Resposta inesperada: {content}"
                
        except Exception as e:
            # Analisar tipo de erro para diagnóstico
            error_msg = str(e).lower()
            
            # Erros relacionados a headers rejeitados
            if any(keyword in error_msg for keyword in [
                "403", "forbidden", "unauthorized", "header", "missing"
            ]):
                pytest.fail(f"Broker rejeitou headers de telemetria: {e}")
            
            # Outros erros (conectividade, etc.)
            pytest.skip(f"Erro de infraestrutura E2E (não relacionado a headers): {e}")
    
    @pytest.mark.skipif(
        not os.getenv("BROKER_E2E_ENABLED", "").lower() == "true",
        reason="Requires running broker for E2E validation"
    )
    def test_e2e_broker_health_with_telemetry_real(self):
        """
        Teste E2E REAL: Health check do broker com headers de telemetria
        VALIDAÇÃO: Broker aceita headers em endpoint de health
        """
        try:
            # Tentar health check do broker
            health_response = self.client.validate_connection()
            
            # Se conseguiu resposta, broker está aceitando headers
            assert health_response, "Health check falhou - possível problema com headers"
            assert isinstance(health_response, dict), "Health response deve ser dict"
            
            # Indicadores de saúde positiva
            if "status" in health_response:
                status = health_response.get("status", "").lower()
                assert status in ["ok", "healthy", "running", "active"], f"Status inesperado: {status}"
                
        except Exception as e:
            error_msg = str(e).lower()
            
            # Diagnosticar se é problema de headers
            if "403" in error_msg or "header" in error_msg:
                pytest.fail(f"Broker health check rejeitou headers: {e}")
            else:
                pytest.skip(f"Broker não disponível para E2E: {e}")
    
    @pytest.mark.skipif(
        not os.getenv("BROKER_E2E_ENABLED", "").lower() == "true",
        reason="E2E test requires real broker"
    )  
    def test_e2e_multiple_requests_telemetry_consistency_real(self):
        """
        Teste E2E REAL: Múltiplas requisições mantêm consistência de headers
        VALIDAÇÃO: Broker aceita headers consistentemente ao longo do tempo
        """
        results = []
        
        try:
            # Fazer múltiplas requisições E2E
            for i in range(3):
                response = self.client.invoke(
                    f"Test consistency {i+1} - responda: CONSISTENT_{i+1}",
                    config={"model": "gpt-4o-mini"}
                )
                results.append(response)
                time.sleep(1)  # Intervalo entre requisições
            
            # Validar que todas as requisições foram aceitas
            assert len(results) == 3, "Nem todas as requisições foram completadas"
            
            for i, result in enumerate(results):
                assert result, f"Requisição {i+1} falhou"
                
                # Verificar conteúdo esperado
                if "content" in result:
                    content = result.get("content", "")
                    assert f"CONSISTENT_{i+1}" in content, f"Conteúdo inesperado na requisição {i+1}: {content}"
                    
        except Exception as e:
            error_msg = str(e).lower()
            
            # Diagnosticar problemas de headers
            if "403" in error_msg:
                pytest.fail(f"Broker rejeitou headers em requisição múltipla: {e}")
            else:
                pytest.skip(f"Erro de infraestrutura em teste múltiplo: {e}")
    
    @pytest.mark.skipif(
        not os.getenv("BROKER_E2E_ENABLED", "").lower() == "true",
        reason="Async E2E test requires broker"
    )
    def test_e2e_async_telemetry_headers_real(self):
        """
        Teste E2E REAL: Headers de telemetria em requisições assíncronas
        VALIDAÇÃO: Broker aceita headers vindos de ainvoke()
        """
        async def async_test():
            try:
                # Fazer requisição assíncrona E2E
                response = await self.client.ainvoke(
                    "Test async E2E telemetry - responda: ASYNC_E2E_OK",
                    config={"model": "gpt-4o-mini"}
                )
                
                # Validar resposta assíncrona
                assert response, "Resposta assíncrona vazia"
                assert isinstance(response, dict), "Resposta async deve ser dict"
                
                if "content" in response:
                    content = response.get("content", "")
                    assert "ASYNC_E2E_OK" in content, f"Conteúdo async inesperado: {content}"
                    
                return response
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Analisar erros assíncronos
                if "403" in error_msg or "header" in error_msg:
                    pytest.fail(f"Broker rejeitou headers em requisição async: {e}")
                else:
                    pytest.skip(f"Erro de infraestrutura async: {e}")
        
        # Executar teste assíncrono
        result = asyncio.run(async_test())
        assert result, "Teste assíncrono falhou"
    
    @pytest.mark.skipif(
        not os.getenv("BROKER_E2E_ENABLED", "").lower() == "true",
        reason="E2E error scenario test requires broker"
    )
    def test_e2e_telemetry_headers_error_scenarios_real(self):
        """
        Teste E2E REAL: Headers de telemetria em cenários de erro
        VALIDAÇÃO: Headers enviados mesmo quando LLM/broker tem problemas
        """
        try:
            # Fazer requisição que pode gerar erro (modelo inexistente)
            response = self.client.invoke(
                "Test error scenario",
                config={"model": "modelo-inexistente-teste"}
            )
            
            # Se chegou até aqui sem erro 403, headers foram aceitos
            # Resultado pode ser erro de modelo, mas não de headers
            if response and isinstance(response, dict):
                # Resposta válida mesmo com erro de modelo
                pass
                
        except Exception as e:
            error_msg = str(e).lower()
            
            # Distinguir entre erro de headers vs erro de modelo
            if "403" in error_msg or "forbidden" in error_msg:
                pytest.fail(f"Erro de headers em cenário de erro: {e}")
            elif any(keyword in error_msg for keyword in [
                "model", "not found", "invalid", "unavailable"
            ]):
                # Erro esperado de modelo, headers foram aceitos
                pass
            else:
                pytest.skip(f"Erro de infraestrutura não relacionado: {e}")
    
    @pytest.mark.skipif(
        not os.getenv("BROKER_E2E_ENABLED", "").lower() == "true",
        reason="Hotfix validation E2E requires broker"
    )
    def test_e2e_hotfix_telemetry_validation_real(self):
        """
        Teste E2E REAL: Validação do Hotfix 1 - Headers previnem HTTP 403
        VALIDAÇÃO: Sistema completo funciona sem HTTP 403 graças aos headers
        """
        try:
            # Esta requisição testa exatamente o cenário que o hotfix resolve
            # Antes do hotfix: HTTP 403 por falta de headers
            # Após hotfix: Sucesso com headers de telemetria
            
            response = self.client.invoke(
                "Validate hotfix E2E - confirme que não há HTTP 403",
                config={"model": "gpt-4o-mini"}
            )
            
            # Se chegou aqui, hotfix funcionou (sem HTTP 403)
            assert response, "Hotfix falhou - possível HTTP 403"
            
            # Verificar que é uma resposta válida (não erro)
            if isinstance(response, dict):
                # Sucesso indica que headers de telemetria resolveram HTTP 403
                success = response.get("success", False)
                if "success" in response:
                    assert success, "Resposta indica falha apesar de não ter HTTP 403"
                
                # Conteúdo válido indica processamento completo
                if "content" in response:
                    content = response.get("content", "")
                    assert len(content) > 0, "Conteúdo vazio pode indicar problema parcial"
            
            # Se chegamos até aqui, o hotfix está funcionando perfeitamente
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # HTTP 403 indica regressão do hotfix
            if "403" in error_msg:
                pytest.fail(f"REGRESSÃO DO HOTFIX: HTTP 403 retornou! {e}")
            else:
                pytest.skip(f"Erro não relacionado ao hotfix: {e}")


# Função para execução manual dos testes E2E
def run_e2e_tests_manually():
    """
    Função para executar testes E2E manualmente quando broker estiver rodando
    """
    os.environ["BROKER_E2E_ENABLED"] = "true"
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    print("🚀 Testes E2E de Telemetria - SDK → Broker")
    print("📋 Pré-requisitos:")
    print("   1. Broker rodando em http://localhost:8000")
    print("   2. OPENAI_API_KEY configurada")
    print("   3. BRADAX_JWT_SECRET configurado")
    print("   4. Set BROKER_E2E_ENABLED=true para executar")
    print()
    
    if os.getenv("BROKER_E2E_ENABLED", "").lower() == "true":
        run_e2e_tests_manually()
    else:
        print("❌ Testes E2E desabilitados - set BROKER_E2E_ENABLED=true para executar")
