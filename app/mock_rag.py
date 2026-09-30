from __future__ import annotations

import time

from .incidents import STATE
from .pii import summarize_text
from .tracing import observe, get_langfuse_client

CORPUS = {
    "refund": ["Refunds are available within 7 days with proof of purchase."],
    "monitoring": ["Metrics detect incidents, logs identify affected requests, traces localize the root cause."],
    "policy": ["Do not expose PII in logs. Use sanitized summaries only."],
}


@observe(name="retrieval", as_type="retriever", capture_input=False, capture_output=False)
def retrieve(message: str) -> list[str]:
    get_langfuse_client().update_current_span(input={"query_preview": summarize_text(message)}, metadata={"tool_name": "retrieval"})
    if STATE["tool_fail"]:
        get_langfuse_client().update_current_span(level="ERROR", status_message="Vector store timeout", metadata={"tool_success": False})
        raise RuntimeError("Vector store timeout")
    if STATE["rag_slow"]:
        time.sleep(2.5)
    lowered = message.lower()
    for key, docs in CORPUS.items():
        if key in lowered:
            get_langfuse_client().update_current_span(output={"doc_count": len(docs)}, metadata={"tool_success": True})
            return docs
    get_langfuse_client().update_current_span(output={"doc_count": 1}, metadata={"tool_success": True, "fallback": True})
    return ["No domain document matched. Use general fallback answer."]
