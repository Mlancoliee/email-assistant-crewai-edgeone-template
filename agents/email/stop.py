"""POST /email/stop — abort the active run for a given conversation.

Mirrors the marketing template's ``stop.py`` contract: ``ctx.utils
.abortActiveRun(conversation_id)`` raises ``CancelledError`` inside the
running handler's task. The SSE generator notices ``request.signal.is_set()``
on its next iteration and bails cleanly.

CrewAI itself has no native AbortSignal — when an active task is cancelled,
the SSE generator closes but the Crew worker thread continues until the
next task boundary. Week 2+ may add a cancel_flag check between tasks for
faster shutdown.
"""
from __future__ import annotations


async def handler(context):
    body = getattr(getattr(context, "request", None), "body", None) or {}
    if not isinstance(body, dict):
        body = {}

    target = (
        body.get("conversationId")
        or body.get("conversation_id")
        or getattr(context, "conversation_id", None)
    )
    if not target:
        return {"status_code": 400, "body": {"error": "Missing conversationId"}}

    utils = getattr(context, "utils", None)
    if utils is None:
        return {"status": "noop", "reason": "ctx.utils unavailable", "conversationId": target}

    result = utils.abortActiveRun(target)
    return {
        "status": "aborted" if getattr(result, "aborted", False) else "idle",
        "conversationId": getattr(result, "conversation_id", None) or target,
        "runId": getattr(result, "run_id", None),
    }
