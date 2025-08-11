import json, shutil, pathlib, datetime, sys

BASE = pathlib.Path(__file__).resolve().parent.parent / 'data'
TELEMETRY_FILE = BASE / 'telemetry.json'
GUARDRAIL_FILE = BASE / 'guardrail_events.json'
INTERACTIONS_FILE = BASE / 'interactions.json'
BACKUP_SUFFIX = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')

removed_telemetry = 0
removed_fields = 0
backfilled = 0

# 1. Backup
for f in [TELEMETRY_FILE, GUARDRAIL_FILE, INTERACTIONS_FILE]:
    if f.exists():
        shutil.copy2(f, f.with_suffix(f.suffix + f'.bak_{BACKUP_SUFFIX}'))

# 2. Limpar telemetry guardrail_triggered
if TELEMETRY_FILE.exists():
    with open(TELEMETRY_FILE, 'r', encoding='utf-8') as fh:
        try:
            telemetry = json.load(fh)
        except json.JSONDecodeError:
            telemetry = []
    new_telemetry = []
    for row in telemetry:
        if row.get('event_type') == 'guardrail_triggered':
            removed_telemetry += 1
            continue
        # Compactar se campos extensos legados existirem
        for legacy_key in ['system_info','metadata','user_id','client_ip','ip_address','sdk_version','guardrail_triggered','system_info_ref','request_size','response_size','duration_ms','error_type','error_code','cost_usd','tokens_consumed']:
            # Mantém somente chaves essenciais definidas pela nova TelemetryData
            # Não remove se a chave fizer parte do novo schema essencial
            pass
        new_telemetry.append(row)
    with open(TELEMETRY_FILE, 'w', encoding='utf-8') as fh:
        json.dump(new_telemetry, fh, ensure_ascii=False, indent=2)

# 3. Limpar guardrail_events: remover fallback_project_used
if GUARDRAIL_FILE.exists():
    with open(GUARDRAIL_FILE, 'r', encoding='utf-8') as fh:
        try:
            guards = json.load(fh)
        except json.JSONDecodeError:
            guards = []
    for ev in guards:
        details = ev.get('details')
        if isinstance(details, dict) and 'fallback_project_used' in details:
            details.pop('fallback_project_used')
            removed_fields += 1
    with open(GUARDRAIL_FILE, 'w', encoding='utf-8') as fh:
        json.dump(guards, fh, ensure_ascii=False, indent=2)

# 4. Backfill interactions result/action se nulos
if INTERACTIONS_FILE.exists():
    with open(INTERACTIONS_FILE, 'r', encoding='utf-8') as fh:
        try:
            interactions = json.load(fh)
        except json.JSONDecodeError:
            interactions = []
    for it in interactions:
        stage = it.get('stage')
        if it.get('result') is None:
            if stage in ('request_received','llm_invocation_start'):
                it['result'] = 'progress'
                it['action'] = it.get('action') or 'progress'
                backfilled += 1
            elif stage == 'llm_invocation_end':
                it['result'] = 'pass'
                it['action'] = it.get('action') or 'complete'
                backfilled += 1
            elif stage == 'telemetry_persisted':
                it['result'] = 'persisted'
                it['action'] = it.get('action') or 'store'
                backfilled += 1
        if stage == 'request_received' and it.get('guardrail_type') is None:
            it['guardrail_type'] = 'n/a'
    with open(INTERACTIONS_FILE, 'w', encoding='utf-8') as fh:
        json.dump(interactions, fh, ensure_ascii=False, indent=2)

print(json.dumps({
    'removed_legacy_guardrail_telemetry': removed_telemetry,
    'removed_fallback_project_used_fields': removed_fields,
    'backfilled_interaction_records': backfilled,
    'backup_suffix': BACKUP_SUFFIX
}, ensure_ascii=False, indent=2))
