"""Six-panel dashboard from the lab JSONL contract, without extra dependencies."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

import yaml
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from .logging_config import LOG_PATH
from .metrics import percentile

ROOT = Path(__file__).resolve().parents[1]
router = APIRouter()


def dashboard_snapshot(log_path: Path = LOG_PATH, now: datetime | None = None) -> dict:
    contract = yaml.safe_load((ROOT / 'config/dashboard.yaml').read_text())['dashboard']
    now = now or datetime.now(timezone.utc)
    start = now - timedelta(minutes=contract['time_range_minutes'])
    rows = []
    invalid = 0
    for line in log_path.read_text(encoding='utf-8').splitlines() if log_path.exists() else []:
        try:
            row = json.loads(line)
            ts = datetime.fromisoformat(row['ts'].replace('Z', '+00:00'))
            if start <= ts <= now:
                row['_minute'] = ts.strftime('%Y-%m-%dT%H:%M:00Z')
                rows.append(row)
        except (ValueError, KeyError, TypeError):
            invalid += 1
    requests = [r for r in rows if r.get('event') == 'request_received']
    responses = [r for r in rows if r.get('event') == 'response_sent']
    failures = [r for r in rows if r.get('event') == 'request_failed']
    retrieval = [r for r in responses + failures if r.get('tool_name') == 'retrieval' and isinstance(r.get('tool_success'), bool)]
    count = len(requests)
    pct = lambda n, d: round(100 * n / d, 2) if d else None
    values = {
        'latency': {**{f'p{p}': percentile([r['latency_ms'] for r in responses], p) if responses else None for p in (50, 95, 99)}, 'ttft_p95': percentile([r['ttft_ms'] for r in responses], 95) if responses else None},
        'traffic': {'count': count, 'rate_per_minute': count / contract['time_range_minutes']},
        'errors': {'error_rate_pct': pct(len(failures), count), 'count_by_value': dict(Counter(r['error_type'] for r in failures)), 'tool_success_rate_pct': pct(sum(r['tool_success'] for r in retrieval), len(retrieval))},
        'cost': {'total': sum(r['cost_usd'] for r in responses)},
        'tokens': {'tokens_in': sum(r['tokens_in'] for r in responses), 'tokens_out': sum(r['tokens_out'] for r in responses)},
        'quality': {'mean': mean(r['quality_score'] for r in responses) if responses else None},
    }
    timeline = []
    # Include zero-traffic minutes so sparse workload does not exaggerate rates.
    minute = start.replace(second=0, microsecond=0)
    while minute <= now:
        key = minute.strftime('%Y-%m-%dT%H:%M:00Z')
        rec = [r for r in requests if r['_minute'] == key]
        sent = [r for r in responses if r['_minute'] == key]
        failed = [r for r in failures if r['_minute'] == key]
        timeline.append({'minute': key, 'traffic': len(rec), 'cost': sum(r['cost_usd'] for r in sent), 'latency_p95': percentile([r['latency_ms'] for r in sent], 95) if sent else None, 'error_rate_pct': pct(len(failed), len(rec))})
        minute += timedelta(minutes=1)
    return {'title': contract['title'], 'source': 'data/logs.jsonl', 'start': start.isoformat(), 'end': now.isoformat(), 'refresh_seconds': contract['refresh_seconds'], 'invalid_lines': invalid, 'panels': [{**panel, 'values': values[panel['id']]} for panel in contract['panels']], 'timeline': timeline}


def dashboard_html(snapshot: dict | None = None) -> str:
    html = (ROOT / 'app/dashboard.html').read_text(encoding='utf-8')
    return html.replace('__SNAPSHOT__', json.dumps(snapshot).replace('<', '\\u003c') if snapshot else 'null')


@router.get('/dashboard', response_class=HTMLResponse)
def dashboard() -> str:
    return dashboard_html()


@router.get('/dashboard/data')
def data() -> dict:
    return dashboard_snapshot()
