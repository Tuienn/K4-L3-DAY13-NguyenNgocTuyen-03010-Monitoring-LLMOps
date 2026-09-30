from __future__ import annotations

import json
import asyncio
from pathlib import Path

import httpx

from app import logging_config
from app.main import app


def test_chat_response_log_exposes_quality_for_dashboard(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post(
                "/chat",
                json={
                    "user_id": "student-01",
                    "session_id": "session-01",
                    "feature": "qa",
                    "message": "Explain observability",
                },
            )

    response = asyncio.run(send_request())

    assert response.status_code == 200
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    response_event = next(event for event in events if event["event"] == "response_sent")
    assert response_event["quality_score"] == response.json()["quality_score"]
    assert response_event["ttft_ms"] == response.json()["ttft_ms"]
    assert response_event["tool_name"] == "retrieval"
    assert response_event["tool_success"] is True


def test_concurrent_requests_keep_context_and_safe_headers(monkeypatch, tmp_path):
    import re
    from app.main import agent
    from app.agent import AgentResult
    monkeypatch.setattr(logging_config, "LOG_PATH", tmp_path / "logs.jsonl")
    monkeypatch.setattr(agent, "run", lambda **kw: AgentResult("safe answer", 1, 1, 20, 10, 0.001, 0.8))

    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await asyncio.gather(*[
                client.post("/chat", headers={"x-request-id": rid}, json={"user_id": f"student-{i}", "session_id": f"session-{i}", "feature": "qa", "message": "monitoring"})
                for i, rid in enumerate(["req-12345678", "invalid@example.test", "req-abcdef12"])
            ])

    responses = asyncio.run(send())
    assert responses[0].headers["x-request-id"] == "req-12345678"
    assert responses[2].headers["x-request-id"] == "req-abcdef12"
    for response in responses:
        assert re.fullmatch(r"req-[0-9a-f]{8}", response.headers["x-request-id"])
        assert response.json()["correlation_id"] == response.headers["x-request-id"]
        assert float(response.headers["x-response-time-ms"]) >= 0
    events = [json.loads(line) for line in (tmp_path / "logs.jsonl").read_text().splitlines()]
    received = [event for event in events if event["event"] == "request_received"]
    assert len({event["user_id_hash"] for event in received}) == 3
    for i, response in enumerate(responses):
        matching = [event for event in events if event["correlation_id"] == response.json()["correlation_id"]]
        assert len(matching) == 2
        assert all(event["session_id"] == f"session-{i}" for event in matching)
