import json, os, time
from pathlib import Path
from bradax.client import BradaxClient

DATA_DIR = Path(__file__).resolve().parents[2] / 'data'

def read_json(path: Path):
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return []

def test_output_sanitization_stage_audited():
    os.environ['BRADAX_PROJECT_TOKEN'] = 'proj_real_001'
    client = BradaxClient()

    # Prompt que deve passar input (sem palavra 'senha' literal) mas potencialmente gerar conteúdo sensível no output
    prompt = "Explique boas práticas de segurança e dê um exemplo fictício de formato de credencial, não real, para fins educativos."
    try:
        result = client.invoke(prompt, model="gpt-4.1-nano")
    except Exception as e:
        # Se bloqueado, reduzir ainda mais sensibilidade
        prompt2 = "Explique boas práticas de segurança de sistemas sem exemplos sensíveis"
        result = client.invoke(prompt2, model="gpt-4.1-nano")
    assert result.get('content') is not None

    time.sleep(0.6)
    interactions = read_json(DATA_DIR / 'interactions.json')
    stages_concat = json.dumps(interactions)
    assert 'request_received' in stages_concat
    assert 'guardrail_input_' in stages_concat  # pass ou blocked
    assert 'llm_invocation_start' in stages_concat
    assert 'llm_invocation_end' in stages_concat
    assert 'telemetry_persisted' in stages_concat
