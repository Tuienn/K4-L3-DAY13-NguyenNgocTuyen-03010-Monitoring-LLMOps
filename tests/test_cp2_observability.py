from datetime import datetime, timedelta, timezone
import json

from app.dashboard import dashboard_snapshot
from app import mock_llm, mock_rag
from app.metrics import percentile


def test_dashboard_counts_failures_and_filters_time_window(tmp_path):
    now = datetime(2026, 9, 30, 3, 0, tzinfo=timezone.utc)
    base = {'ts': (now - timedelta(minutes=1)).isoformat()}
    rows = [
        {**base, 'event': 'request_received', 'correlation_id': 'req-00000001'},
        {**base, 'event': 'request_received', 'correlation_id': 'req-00000002'},
        {**base, 'event': 'response_sent', 'correlation_id': 'req-00000001', 'latency_ms': 100, 'ttft_ms': 20, 'cost_usd': .003, 'tokens_in': 20, 'tokens_out': 100, 'quality_score': .8, 'tool_name': 'retrieval', 'tool_success': True},
        {**base, 'event': 'request_failed', 'correlation_id': 'req-00000002', 'error_type': 'RuntimeError', 'tool_name': 'retrieval', 'tool_success': False},
        {'ts': (now - timedelta(hours=2)).isoformat(), 'event': 'request_received'},
        {'ts': (now + timedelta(minutes=1)).isoformat(), 'event': 'request_received'},
    ]
    path = tmp_path / 'logs.jsonl'
    path.write_text('\n'.join(json.dumps(r) for r in rows)+'\ninvalid')
    result = dashboard_snapshot(path, now)
    values = {p['id']: p['values'] for p in result['panels']}
    assert len(result['panels']) == 6
    assert values['traffic']['count'] == 2
    assert values['errors']['error_rate_pct'] == 50
    assert values['errors']['tool_success_rate_pct'] == 50
    assert values['errors']['count_by_value'] == {'RuntimeError': 1}
    assert values['cost']['total'] == .003
    assert values['tokens'] == {'tokens_in': 20, 'tokens_out': 100}
    assert values['quality']['mean'] == .8
    assert values['latency']['ttft_p95'] == 20
    assert sum(r['traffic'] for r in result['timeline']) == 2
    assert result['invalid_lines'] == 1


def test_generation_records_scrubbed_preview_usage_and_cost(monkeypatch):
    updates = []
    class Client:
        def update_current_generation(self, **kwargs):
            updates.append(kwargs)
    monkeypatch.setattr(mock_llm, 'get_langfuse_client', lambda: Client())
    monkeypatch.setattr(mock_llm.time, 'sleep', lambda seconds: None)
    result = mock_llm.FakeLLM.generate.__wrapped__(mock_llm.FakeLLM(), 'Contact student@example.test at 0901234567')
    text = json.dumps(updates, default=str)
    assert 'student@example.test' not in text
    assert '0901234567' not in text
    assert 'REDACTED_EMAIL' in text
    assert updates[0]['model'] == result.model
    assert updates[-1]['usage_details'] == {'input': result.usage.input_tokens, 'output': result.usage.output_tokens}
    assert abs(sum(updates[-1]['cost_details'].values()) - (result.usage.input_tokens * 3 + result.usage.output_tokens * 15) / 1_000_000) < 1e-12
    assert 'completion_start_time' in updates[1]


def test_nearest_rank_percentiles_do_not_round_median_up():
    assert percentile([100, 200, 300, 400], 50) == 200
    assert percentile([100, 200, 300, 400], 95) == 400
