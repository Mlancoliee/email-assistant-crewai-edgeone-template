"""Conditional edge functions for the LangGraph email-assistant pipeline.

Each function returns a string key that maps (in ``_graph.build_graph``)
to a node name. Pure: no side-effects, no LLM calls, just inspect state.

Edges:
  - ``after_prioritize`` → "draft" | "summarize"
       Skip the loop entirely if no email survived prioritize.
  - ``after_review``     → "apply" | "draft"
       Loop back to draft on regenerate; otherwise commit via apply.
  - ``next_or_done``     → "draft" | "summarize"
       Re-enter the per-email loop or finalize.
"""
from __future__ import annotations

from _state import EmailAssistantState


def after_prioritize(state: EmailAssistantState) -> str:
    """Decide what to do after prioritize.

    Routing:
      - ``task == "triage_only"`` → "summarize" — user only wants
        classification + the day's summary, NOT drafted replies. This is
        the ⚡ fast preview path.
      - no prioritized emails (auto-archive ate everything) → "summarize"
      - otherwise → "draft" — start the per-email HITL loop.
    """
    if state.get("task") == "triage_only":
        return "summarize"
    return "draft" if state.get("prioritized") else "summarize"


def after_review(state: EmailAssistantState) -> str:
    """Branch on the latest review decision.

    ``regenerate`` → "draft" (rewrite the same email's draft from scratch)
    everything else (approve / edit / reject / skip) → "apply"
    """
    decisions = state.get("review_decisions") or []
    if not decisions:
        # No decision found — defensive: continue to apply (will no-op)
        return "apply"
    last = decisions[-1]
    return "draft" if last.action == "regenerate" else "apply"


def next_or_done(state: EmailAssistantState) -> str:
    """After apply, more emails to process? Or are we done?"""
    cursor = state.get("cursor", 0)
    prioritized = state.get("prioritized") or []
    return "draft" if cursor < len(prioritized) else "summarize"
