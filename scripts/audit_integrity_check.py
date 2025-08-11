import json, sys, pathlib, collections, datetime

BASE = pathlib.Path(__file__).resolve().parent.parent / 'data'
FILES = {
    'interactions': BASE / 'interactions.json',
    'telemetry': BASE / 'telemetry.json',
    'guardrail_events': BASE / 'guardrail_events.json'
}

def load(name, path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        print(f"ERRO JSON {name}: {e}")
        return []

interactions = load('interactions', FILES['interactions'])
telemetry = load('telemetry', FILES['telemetry'])
guardrails = load('guardrail_events', FILES['guardrail_events'])

# Index by request_id
idx = collections.defaultdict(lambda: {'interactions': [], 'telemetry': [], 'guardrails': []})
for it in interactions:
    idx[it.get('request_id')]['interactions'].append(it)
for t in telemetry:
    rid = t.get('request_id') or t.get('telemetry_id')
    idx[rid]['telemetry'].append(t)
for g in guardrails:
    idx[g.get('request_id')]['guardrails'].append(g)

issues = []
for rid, bucket in idx.items():
    if not rid:
        continue
    stages = {i.get('stage') for i in bucket['interactions']}
    if 'request_received' not in stages:
        issues.append((rid, 'missing_stage', 'request_received'))
    # If telemetry exists ensure at least one llm_invocation_end OR guardrail_input_blocked
    if bucket['telemetry'] and not ({'llm_invocation_end','guardrail_input_blocked'} & stages):
        issues.append((rid, 'missing_completion_stage', 'llm_invocation_end'))
    # If guardrail blocked event, expect guardrail_input_blocked interaction stage
    blocked = any(g.get('action') == 'blocked' for g in bucket['guardrails'])
    if blocked and 'guardrail_input_blocked' not in stages and 'guardrail_output_modified' not in stages:
        issues.append((rid, 'blocked_without_stage', 'guardrail_input_blocked'))

# Telemetry guardrail_triggered legacy presence check
legacy_guardrail_events = [t for t in telemetry if t.get('event_type') == 'guardrail_triggered']

# Contagem de tipos de eventos de guardrail
guardrail_stats = {
    'blocked': 0,
    'modified': 0,
    'pass': 0
}
for g in guardrails:
    action = g.get('action')
    if action == 'blocked':
        guardrail_stats['blocked'] += 1
    elif action in ('modified','sanitized'):
        guardrail_stats['modified'] += 1
    elif action == 'pass':
        guardrail_stats['pass'] += 1

# Se flag de PASS desativada no ambiente, mas eventos pass existem, registrar issue
import os
pass_flag_env = os.getenv('BRADAX_LOG_GUARDRAIL_PASS', 'false').strip().lower() in ('1','true','yes','on')
if not pass_flag_env and guardrail_stats['pass'] > 0:
    issues.append(('__global__','unexpected_pass_events', guardrail_stats['pass']))

summary = {
    'total_request_ids': len([k for k in idx.keys() if k]),
    'with_interactions': sum(1 for b in idx.values() if b['interactions']),
    'with_telemetry': sum(1 for b in idx.values() if b['telemetry']),
    'with_guardrail_events': sum(1 for b in idx.values() if b['guardrails']),
    'legacy_guardrail_telemetry_entries': len(legacy_guardrail_events),
    'guardrail_event_stats': guardrail_stats,
    'issues_found': len(issues)
}

print(json.dumps({'summary': summary, 'issues': issues[:50]}, indent=2, ensure_ascii=False))

# Exit code !=0 if issues
if issues:
    sys.exit(1)
