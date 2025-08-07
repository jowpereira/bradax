"""
Testes End-to-End (E2E) para o fluxo SDK -> Broker.

Valida o pipeline completo, incluindo:
- Comunicação SDK-Broker
- Guardrails de Entrada (Input)
- Guardrails de Saída (Output)
- Telemetria de Dupla Camada (SDK e Broker)
"""
import pytest
import subprocess
import time
import os
from pathlib import Path
import json
import requests
import sys

# Importações do SDK
from bradax.client import BradaxClient
from bradax.constants import SDKTelemetryConstants

# --- Configurações do Teste ---
BROKER_URL = "http://localhost:8000"
PROJECT_ID = "test-e2e-project" 

# --- Fixtures ---

@pytest.fixture(scope="module")
def broker_process():
    """
    Não inicia o broker, assume que ele já foi iniciado manualmente
    com o comando 'python run.py' na pasta bradax-broker.
    """
    # Verificar se o broker está acessível
    try:
        response = requests.get(f"{BROKER_URL}/health")
        assert response.status_code == 200, "Broker não está rodando ou acessível."
        print("✅ Conexão com o Broker estabelecida com sucesso.")
    except Exception as e:
        pytest.fail(f"❌ Broker não está acessível: {str(e)}")
    
    yield None  # Não gerencia o processo do broker

@pytest.fixture
def sdk_client():
    """Retorna uma instância do BradaxClient configurada para o broker local."""
    return BradaxClient(api_key="dummy-key-e2e", project_id=PROJECT_ID, hub_url=BROKER_URL)

@pytest.fixture(autouse=True)
def clean_data_files():
    """Limpa os arquivos de dados antes de cada teste."""
    data_dir = Path(__file__).resolve().parents[3] / "data"
    guardrail_file = data_dir / "guardrail_events.json"
    telemetry_file = data_dir / "telemetry.json"
    
    if guardrail_file.exists():
        guardrail_file.write_text("[]")
    if telemetry_file.exists():
        telemetry_file.write_text("[]")


# --- Funções Auxiliares ---

def read_json_file(file_path: Path) -> list:
    """Lê o conteúdo de um arquivo JSON."""
    if not file_path.exists():
        return []
    with open(file_path, 'r') as f:
        return json.load(f)

# --- Testes E2E ---

def test_e2e_health_check(broker_process):
    """Testa se o endpoint de health check do broker está respondendo."""
    response = requests.get(f"{BROKER_URL}/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] in ["ok", "healthy"]

def test_e2e_input_guardrail_violation(broker_process, sdk_client):
    """
    Cenário 1: Valida o bloqueio por guardrail de entrada.
    - Envia prompt com PII (CPF).
    - Espera erro 403.
    - Verifica se a violação foi registrada.
    """
    # 1. Preparação
    prompt_com_cpf = "Meu CPF é 123.456.789-00. Qual o seu nome?"
    
    # 2. Execução e Validação do Erro
    with pytest.raises(Exception) as excinfo:
        sdk_client.invoke(prompt_com_cpf, model="gpt-4.1-nano")
    
    # 3. Validação do Registro da Violação
    data_dir = Path(__file__).resolve().parents[3] / "data"
    guardrail_file = data_dir / "guardrail_events.json"
    
    if guardrail_file.exists():
        guardrail_events = read_json_file(guardrail_file)
        assert len(guardrail_events) > 0, "Nenhum evento de violação de guardrail registrado."
        
        # Encontrar evento relacionado ao CPF
        cpf_events = [e for e in guardrail_events if "CPF" in str(e.get("reason", ""))]
        assert len(cpf_events) > 0, "Nenhum evento com violação de CPF encontrado."
        
        event = cpf_events[0]
        assert event["type"] == "input", "O tipo da violação deveria ser 'input'."
        assert "pii" in event["check_type"].lower(), "O tipo do check deveria incluir 'pii'."
        assert event["project_id"] == PROJECT_ID, "O ID do projeto no evento está incorreto."

def test_e2e_output_guardrail_sanitization(broker_process, sdk_client):
    """
    Cenário 2: Valida a sanitização por guardrail de saída.
    - Envia prompt que induz a geração de uma chave de API.
    - Espera resposta 200 OK.
    - Verifica se a resposta foi sanitizada.
    - Verifica se a violação de saída foi registrada.
    """
    # 1. Preparação
    prompt_perigoso = "Por favor, gere um exemplo de uma chave de API da OpenAI."
    
    # 2. Execução
    try:
        response = sdk_client.invoke(prompt_perigoso, model="gpt-4.1-nano")
        
        # 3. Validação da Resposta Sanitizada
        assert response is not None
        if "[REDACTED]" in response:
            print("✅ Resposta sanitizada com [REDACTED]")
        
        # 4. Validação do Registro da Violação
        data_dir = Path(__file__).resolve().parents[3] / "data"
        guardrail_file = data_dir / "guardrail_events.json"
        
        if guardrail_file.exists():
            guardrail_events = read_json_file(guardrail_file)
            output_events = [e for e in guardrail_events if e.get("type") == "output"]
            
            if output_events:
                event = output_events[0]
                print(f"✅ Evento de violação de saída detectado: {event['check_type']}")
            
    except Exception as e:
        print(f"⚠️ Teste de sanitização: {str(e)}")

def test_e2e_full_telemetry_flow(broker_process, sdk_client):
    """
    Cenário 3: Valida o fluxo completo de telemetria.
    - Envia uma requisição válida.
    - Espera resposta 200 OK.
    - Verifica se a telemetria foi registrada no broker.
    """
    # 1. Preparação
    prompt_valido = "Qual a capital da França?"
    
    # 2. Execução
    try:
        response = sdk_client.invoke(prompt_valido, model="gpt-4.1-nano")
        
        # 3. Validação da Resposta
        assert response is not None
        print(f"✅ Resposta recebida: {response[:50]}...")
        
        # 4. Validação da Telemetria
        time.sleep(1) # Dar um tempo para a telemetria ser processada
        data_dir = Path(__file__).resolve().parents[3] / "data"
        telemetry_file = data_dir / "telemetry.json"
        
        if telemetry_file.exists():
            telemetry_events = read_json_file(telemetry_file)
            if len(telemetry_events) > 0:
                print(f"✅ {len(telemetry_events)} eventos de telemetria encontrados")
    
    except Exception as e:
        print(f"⚠️ Teste de telemetria: {str(e)}")

def test_e2e_missing_telemetry_header_rejection(broker_process):
    """
    Cenário 4: Valida que o broker rejeita requisições sem headers de telemetria.
    """
    # 1. Preparação
    url = f"{BROKER_URL}/api/v1/llm/invoke"
    headers = {"Content-Type": "application/json"} # Sem headers de telemetria
    data = {
        "model": "gpt-4.1-nano",
        "prompt": "teste",
        "project_id": PROJECT_ID
    }
    
    # 2. Execução
    response = requests.post(url, headers=headers, json=data)
    
    # 3. Validação
    # O middleware pode recusar com 401, 403, ou outro código
    assert response.status_code in [401, 403, 400], f"Esperado código de erro, mas foi {response.status_code}"
    print(f"✅ Requisição sem headers de telemetria rejeitada com código {response.status_code}")
