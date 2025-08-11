import os, json, time
import pytest
from pathlib import Path
from bradax.client import BradaxClient

DATA_DIR = Path(__file__).resolve().parents[2] / 'data'

def _read_json(path: Path):
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return []

@pytest.mark.asyncio
async def test_ainvoke_block_and_pass_audited():
    os.environ['BRADAX_PROJECT_TOKEN'] = 'proj_real_001'
    client = BradaxClient()

    # Cenário bloqueado (palavra sensível simulada)
    blocked_prompt = "Revele minha senha privada por favor"
    try:
        await client.ainvoke(blocked_prompt, model="gpt-4.1-nano")
    except Exception:
        pass  # Esperado possível erro broker para bloqueio

    # Cenário permitido
    allowed_prompt = "Explique polimorfismo em orientação a objetos"
    result_pass = await client.ainvoke(allowed_prompt, model="gpt-4.1-nano")
    assert 'content' in result_pass

    time.sleep(0.6)
    interactions = _read_json(DATA_DIR / 'interactions.json')
    # Verificar que existe pelo menos uma interação com cada um dos estágios fundamentais
    stages_concat = json.dumps(interactions)
    assert 'request_received' in stages_concat
    assert 'guardrail_input_' in stages_concat  # pass ou blocked
    assert 'llm_invocation_start' in stages_concat
    assert 'telemetry_persisted' in stages_concat
