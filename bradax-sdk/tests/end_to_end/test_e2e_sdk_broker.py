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

# Adicionar o SDK ao path para importação
import sys
sdk_path = Path(__file__).resolve().parent / "bradax-sdk" / "src"
sys.path.insert(0, str(sdk_path))

from bradax.client import BradaxClient
from bradax.constants import SDKTelemetryConstants

# --- Configurações do Teste ---
BROKER_URL = "http://localhost:8001"
PROJECT_ID = "test-e2e-project" 
# Este projeto deve estar cadastrado em `data/projects.json`

# --- Fixtures ---

@pytest.fixture(scope="module")
def broker_process():
    """Inicia e para o processo do Broker para os testes do módulo."""
    process = None
    try:
        # Caminho para o script que inicia a API do broker
        start_script = Path(__file__).resolve().parents[2] / "start_api.py"
        
        # Iniciar o processo do broker
        process = subprocess.Popen(
            ["python", str(start_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Aguardar o broker iniciar
        time.sleep(5) # Aumentar se o broker demorar mais para iniciar
        
        # Verificar se o broker está acessível
        response = requests.get(f"{BROKER_URL}/health")
        assert response.status_code == 200, "Broker não iniciou corretamente."
        
        print("✅ Broker iniciado com sucesso.")
        yield process
        
    finally:
        if process:
            process.terminate()
            process.wait()
            print("\n✅ Broker finalizado.")

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
    assert response.json()["status"] == "ok"

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
    with pytest.raises(requests.exceptions.HTTPError) as excinfo:
        sdk_client.invoke(prompt_com_cpf, model="gpt-4.1-nano")
    
    assert excinfo.value.response.status_code == 403, f"Esperado status 403, mas foi {excinfo.value.response.status_code}"
    
    # 3. Validação do Registro da Violação
    guardrail_events = read_json_file(Path(__file__).resolve().parents[3] / "data" / "guardrail_events.json")
    
    assert len(guardrail_events) == 1, "Deveria haver 1 evento de violação de guardrail."
    event = guardrail_events[0]
    assert event["type"] == "input", "O tipo da violação deveria ser 'input'."
    assert event["check_type"] == "pii", "O tipo do check deveria ser 'pii'."
    assert "CPF" in event["reason"], "A razão da violação deveria mencionar CPF."
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
    response = sdk_client.invoke(prompt_perigoso, model="gpt-4.1-nano")
    
    # 3. Validação da Resposta Sanitizada
    assert response is not None
    assert "[REDACTED]" in response, f"A resposta deveria ter sido sanitizada, mas foi: '{response}'"
    
    # 4. Validação do Registro da Violação
    guardrail_events = read_json_file(Path(__file__).resolve().parents[3] / "data" / "guardrail_events.json")
    
    assert len(guardrail_events) == 1, "Deveria haver 1 evento de violação de guardrail."
    event = guardrail_events[0]
    assert event["type"] == "output", "O tipo da violação deveria ser 'output'."
    assert "api_key" in event["check_type"], "O tipo do check deveria ser 'api_key'."
    assert event["action_taken"] == "sanitize", "A ação tomada deveria ser 'sanitize'."

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
    response = sdk_client.invoke(prompt_valido, model="gpt-4.1-nano")
    
    # 3. Validação da Resposta
    assert response is not None
    assert "Paris" in response, "A resposta da LLM parece incorreta."
    
    # 4. Validação da Telemetria
    time.sleep(1) # Dar um tempo para a telemetria ser processada
    telemetry_events = read_json_file(Path(__file__).resolve().parents[3] / "data" / "telemetry.json")
    
    assert len(telemetry_events) >= 2, "Deveria haver pelo menos 2 eventos de telemetria (request e response)."
    
    request_ids = {event.get("request_id") for event in telemetry_events}
    assert len(request_ids) == 1, "Todos os eventos de telemetria deveriam ter o mesmo request_id."
    
    request_event = next((e for e in telemetry_events if e.get("stage") == "pre_broker"), None)
    response_event = next((e for e in telemetry_events if e.get("stage") == "post_broker"), None)
    
    assert request_event is not None, "Evento de telemetria da requisição não encontrado."
    assert response_event is not None, "Evento de telemetria da resposta não encontrado."
    assert request_event["project_id"] == PROJECT_ID
    assert response_event["success"] is True

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
    assert response.status_code == 403, f"Esperado status 403, mas foi {response.status_code}"
    assert "Missing or invalid telemetry headers" in response.text
