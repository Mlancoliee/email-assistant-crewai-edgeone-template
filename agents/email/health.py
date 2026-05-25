"""POST /email/health — basic health probe."""
from __future__ import annotations

import time


async def handler(context):
    return {
        "status": "ok",
        "ts": int(time.time() * 1000),
        "conversationId": getattr(context, "conversation_id", None),
        "runId": getattr(context, "run_id", None),
        "framework": "langgraph+crewai",
        "agent": "email-assistant",
    }
