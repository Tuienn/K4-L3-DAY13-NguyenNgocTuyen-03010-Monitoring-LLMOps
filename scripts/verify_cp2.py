"""Generate real CP2 evidence in the configured personal Langfuse project.

Run from the repository root: .venv/bin/python scripts/verify_cp2.py
Creates missing lab prompts, promotes production, then rolls it back to baseline.
Never reads config/challenge.json. Credentials are loaded but never printed.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv

load_dotenv(ROOT / '.env')
from app.main import app
from app.dashboard import dashboard_snapshot, dashboard_html
from app.prompt_management import DEFAULT_PROMPT_TEMPLATE
from app.tracing import get_langfuse_client, tracing_enabled
from app.pii import scrub_text
import httpx

EVIDENCE = ROOT / 'submission/evidence'


def save(name: str, data) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def managed_prompt(client, name, label, template):
    try:
        prompt = client.get_prompt(name, label=label, cache_ttl_seconds=0)
    except Exception as exc:
        if getattr(exc, 'status_code', None) != 404:
            raise
        prompt = client.create_prompt(name=name, prompt=template, type='text', labels=[label] + (['production'] if label == 'baseline' else []), commit_message=f'Day13 CP2 {label}')
    for variable in ('feature', 'docs', 'message'):
        assert '{{' + variable + '}}' in prompt.prompt, f'Missing variable: {variable}'
    return prompt


async def workload(client, label, payloads):
    os.environ['LANGFUSE_PROMPT_LABEL'] = label
    client.clear_prompt_cache()
    results = []
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://lab') as api:
        health = await api.get('/health')
        assert health.json()['ok']
        for payload in payloads:
            response = await api.post('/chat', json=payload)
            assert response.status_code == 200, response.text
            data = response.json()
            assert response.headers['x-request-id'] == data['correlation_id']
            results.append({'label': label, 'correlation_id': data['correlation_id'], 'latency_ms': data['latency_ms'], 'ttft_ms': data['ttft_ms'], 'status_code': response.status_code, 'response_headers': {key: response.headers[key] for key in ('x-request-id', 'x-response-time-ms')}})
    return results


def main():
    assert tracing_enabled(), 'Langfuse keys/SDK missing'
    client = get_langfuse_client()
    projects = client.api.projects.get().data
    project_info = [{'id': p.id, 'name': p.name} for p in projects]
    save('cp2-project.json', project_info)
    assert len(project_info) == 1, 'Use keys scoped to one personal project'
    name = os.getenv('LANGFUSE_PROMPT_NAME', 'day13-chat')
    baseline = managed_prompt(client, name, 'baseline', DEFAULT_PROMPT_TEMPLATE)
    candidate = managed_prompt(client, name, 'candidate', 'Answer concisely using the retrieved context.\n' + DEFAULT_PROMPT_TEMPLATE)
    assert baseline.version != candidate.version
    payloads = [json.loads(line) for line in (ROOT / 'data/sample_queries.jsonl').read_text().splitlines() if line.strip()]
    transitions = []
    def production(version, stage):
        client.update_prompt(name=name, version=version, new_labels=['production'])
        resolved = client.get_prompt(name, label='production', cache_ttl_seconds=0)
        assert resolved.version == version
        transitions.append({'stage': stage, 'label': 'production', 'version': resolved.version, 'timestamp': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()})
        save('cp2-prompt-rollback.json', transitions)
    if '--resume' in sys.argv:
        results = json.loads((EVIDENCE / 'cp2-workload.json').read_text())
    else:
        results = []
        production(baseline.version, 'before')
        try:
            results += asyncio.run(workload(client, 'baseline', payloads))
            results += asyncio.run(workload(client, 'candidate', payloads))
            production(candidate.version, 'promote')
            results += asyncio.run(workload(client, 'production', payloads[:1]))
        finally:
            production(baseline.version, 'rollback')
            os.environ['LANGFUSE_PROMPT_LABEL'] = 'production'
            client.clear_prompt_cache()
        results += asyncio.run(workload(client, 'production', payloads[:1]))
        save('cp2-prompt-versions.json', [{'name': name, 'version': p.version, 'labels': client.get_prompt(name, version=p.version, cache_ttl_seconds=0).labels, 'template': p.prompt} for p in (baseline, candidate)])
        save('cp2-workload.json', results)
        client.flush()
    log_path = EVIDENCE / 'cp2-structured-log.jsonl' if '--resume' in sys.argv else ROOT / 'data/logs.jsonl'
    rows = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
    logs = {row['correlation_id']: row for row in rows if row.get('event') == 'response_sent'}
    traces = []
    for result in results:
        trace_id = logs[result['correlation_id']]['trace_id']
        logged_at = datetime.fromisoformat(logs[result['correlation_id']]['ts'].replace('Z', '+00:00'))
        assert trace_id, 'Missing exported trace ID'
        # Ingestion can take a few seconds after flush. Bounded retry for evidence.
        for attempt in range(12):
            try:
                batch = client.api.observations.get_many(trace_id=trace_id, from_start_time=logged_at-timedelta(minutes=5), to_start_time=logged_at+timedelta(minutes=5), fields='core,basic,time,io,metadata,model,usage,prompt,metrics,trace_context', limit=100)
                roots = [o for o in batch.data if o.name == 'lab-agent-run']
                if any(o.name == 'generation' and o.prompt_name for o in batch.data) and roots and isinstance(roots[0].metadata, dict) and roots[0].metadata.get('correlation_id'):
                    break
            except Exception as exc:
                if getattr(exc, 'status_code', None) != 404:
                    raise
            time.sleep(2)
        else:
            raise RuntimeError(f'Trace not ingested: {trace_id}')
        observations = [o.model_dump(mode='json', by_alias=True) for o in batch.data]
        agent = next(o for o in observations if o['name'] == 'lab-agent-run')
        retriever = next(o for o in observations if o['name'] == 'retrieval')
        generation = next(o for o in observations if o['name'] == 'generation')
        assert retriever['parentObservationId'] == agent['id']
        assert generation['parentObservationId'] == agent['id']
        assert generation['type'] == 'GENERATION'
        assert generation['promptName'] == name
        expected = baseline.version if result['label'] == 'baseline' else candidate.version if result['label'] == 'candidate' else (candidate.version if len(traces) == 20 else baseline.version)
        assert generation['promptVersion'] == expected
        metadata = agent['metadata']
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        assert metadata['correlation_id'] == result['correlation_id']
        log_row = logs[result['correlation_id']]
        assert generation['usageDetails']['input'] == log_row['tokens_in']
        assert generation['usageDetails']['output'] == log_row['tokens_out']
        assert abs(generation['costDetails']['total'] - log_row['cost_usd']) < 1e-6
        # SDK resource metadata includes its public key; export only lab attributes.
        def safe_metadata(value):
            if not isinstance(value, dict):
                return value
            return {k: v for k, v in value.items() if not k.startswith(('scope.', 'resourceAttributes.'))}
        metadata = safe_metadata(metadata)
        for observation in observations:
            observation['metadata'] = safe_metadata(observation.get('metadata'))
            for field in ('input', 'output'):
                value = observation.get(field)
                if value is not None:
                    serialized = json.dumps(value, ensure_ascii=False)
                    assert scrub_text(serialized) == serialized, f'Unscrubbed observation {field}' 
        safe_keys = ('id', 'name', 'type', 'parentObservationId', 'startTime', 'endTime', 'level', 'input', 'output', 'metadata', 'model', 'promptName', 'promptVersion', 'usageDetails', 'costDetails', 'totalCost', 'completionStartTime', 'timeToFirstToken', 'latency', 'inputUsage', 'outputUsage', 'totalUsage')
        traces.append({**result, 'trace_id': trace_id, 'trace_url': client.get_trace_url(trace_id=trace_id), 'metadata': metadata, 'observations': [{k: o[k] for k in safe_keys if k in o} for o in observations]})
        save('cp2-traces.json', traces)
    snapshot = dashboard_snapshot()
    save('cp2-dashboard-data.json', snapshot)
    (EVIDENCE / '11-dashboard-overview.html').write_text(dashboard_html(snapshot), encoding='utf-8')
    print(f'Project: {project_info[0]["name"]}; verified {len(traces)} traces; prompt versions {baseline.version}/{candidate.version}; production rolled back to {baseline.version}')


if __name__ == '__main__':
    main()
