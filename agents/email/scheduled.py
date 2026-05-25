"""POST /email/scheduled — cron entry point.

Runs the full pipeline non-interactively and persists the digest to
``ctx.kv``. The crontab service injects ``_schedule: true`` in the body
when invoking the configured cron path; the handler also accepts manual
invocations (without ``_schedule``) which behave the same — useful for
local testing without waiting for the next cron tick.

Differences from ``/email/run``:

  - No SSE — returns a single JSON object (status + digest + summary).
  - ``auto_approve=True`` is forced, so HITL is bypassed and the pipeline
    runs to completion in one shot.
  - The final digest is persisted to ``ctx.kv["digest:YYYY-MM-DD"]``
    so the morning summary is reachable later (e.g. by a future
    /email/history endpoint) without re-running the pipeline.

Same-day idempotency: each invocation uses a fresh ``thread_id`` so
LangGraph doesn't short-circuit on the cached END state, but the kv key
``digest:{today}`` is overwritten — the latest run wins.
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import date
from pathlib import Path
from typing import Any

CURRENT = Path(__file__).resolve().parent
if str(CURRENT) not in sys.path:
    sys.path.insert(0, str(CURRENT))

from _graph import get_graph  # noqa: E402
from _llm import DEFAULT_MODEL, get_crewai_llm, get_env, get_openai_client  # noqa: E402
from _providers import get_provider  # noqa: E402


def _digest_kv_key(today: str) -> str:
    return f"digest:{today}"


async def _persist_digest(kv: Any, today: str, digest: dict) -> bool:
    """Write the digest to the per-route KV. Returns True on success."""
    if kv is None:
        return False
    try:
        payload = json.dumps(digest, ensure_ascii=False, separators=(",", ":"))
        result = kv.set(_digest_kv_key(today), payload)
        # Tolerate sync stubs (test fakes that aren't async)
        if hasattr(result, "__await__"):
            await result
        return True
    except Exception:
        return False


async def handler(context):
    body = (getattr(getattr(context, "request", None), "body", None) or {})
    if not isinstance(body, dict):
        body = {}

    is_cron = body.get("_schedule") is True
    task = body.get("task") or "daily_digest"
    today = date.today().isoformat()

    try:
        env = get_env(getattr(context, "env", None))
        llm = get_crewai_llm(env)
        openai_client = get_openai_client(env)
    except Exception as exc:
        return {"status_code": 500, "body": {"error": str(exc)}}

    try:
        provider = get_provider(
            getattr(context, "env", None) or {},
            getattr(context, "kv", None),
        )
        rules_bundle = await provider.load_user_rules()
    except Exception as exc:
        return {"status_code": 500, "body": {"error": f"provider init failed: {exc}"}}

    try:
        checkpointer = context.store.langgraph_checkpointer
    except Exception as exc:
        return {"status_code": 500, "body": {"error": f"checkpointer unavailable: {exc}"}}

    app = get_graph(
        checkpointer=checkpointer,
        provider=provider,
        llm=llm,
        openai_client=openai_client,
        model=DEFAULT_MODEL,
    )

    # Fresh thread_id per invocation — prevents same-day reruns from
    # short-circuiting on a cached END state. The kv key is the day, so the
    # digest gets overwritten (idempotent from the consumer's POV).
    run_part = (
        getattr(context, "run_id", None)
        or uuid.uuid4().hex[:12]
    )
    thread_id = f"scheduled:{today}:{run_part}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "task": task,
        "user_rules": rules_bundle.to_rules(),
        "auto_approve": True,
    }

    try:
        final_state = await app.ainvoke(initial_state, config=config)
    except Exception as exc:
        return {"status_code": 500, "body": {"error": f"pipeline failed: {exc}"}}

    final_state = final_state or {}
    summary = final_state.get("summary", "")
    drafts = final_state.get("drafts", []) or []
    actions = final_state.get("final_actions", []) or []
    errors = final_state.get("errors", []) or []

    digest = {
        "date": today,
        "task": task,
        "trigger": "schedule" if is_cron else "manual",
        "summary": summary,
        "thread_id": thread_id,
        "drafts_count": len(drafts),
        "actions_count": len(actions),
        "errors": errors,
    }

    persisted = await _persist_digest(getattr(context, "kv", None), today, digest)

    return {
        "status": "ok",
        "stored": persisted,
        **digest,
    }
