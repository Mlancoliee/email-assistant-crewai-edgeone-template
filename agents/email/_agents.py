"""CrewAI Agent definitions — three roles for the email draft sub-pipeline.

  ┌──────────────────────────┬────────────────┐
  │ Backend Agent            │ UI stage       │
  ├──────────────────────────┼────────────────┤
  │ Email Triage Analyst     │ analyze        │
  │ Reply Writer             │ draft          │
  │ Voice Polisher           │ polish         │
  └──────────────────────────┴────────────────┘

Each agent has the same LLM bound to AI Gateway (see ``_llm.get_crewai_llm``).
Tools are agent-specific so the trace makes the role boundary obvious.

Imports are deferred so this module loads in non-CrewAI test environments.
"""
from __future__ import annotations

from typing import Any

from _tools import TemplateTool, ThreadContextTool, ToneTool


# Map agent role string → UI stage id (used by EventBridge to render the
# stepper in the frontend; mirrors the marketing template pattern).
ROLE_TO_UI_STAGE: dict[str, str] = {
    "Email Triage Analyst": "analyze",
    "Reply Writer": "draft",
    "Voice Polisher": "polish",
}


def build_filter_agent(llm: Any) -> Any:
    """Stage 1 — read the incoming email and produce a structured analysis.

    Output (consumed by the writer): key points, recipient intent, must-address
    items, and any thread context worth carrying forward.
    """
    from crewai import Agent
    return Agent(
        role="Email Triage Analyst",
        goal=(
            "Read the incoming email, identify the sender's intent, and surface "
            "the 1–3 key points the reply MUST address. Pull thread history if "
            "it's relevant."
        ),
        backstory=(
            "You're a meticulous executive assistant with 10 years of experience. "
            "You read between the lines: a vendor follow-up is really asking for "
            "a price decision, a meeting invite is really asking for prep "
            "expectations. You never write replies yourself — you just hand the "
            "writer a clean brief."
        ),
        llm=llm,
        tools=[ThreadContextTool()],
        allow_delegation=False,
        verbose=False,
    )


def build_writer_agent(llm: Any) -> Any:
    """Stage 2 — given the analysis, draft a body that addresses every point.

    Picks a reply template when the scenario matches a stock one
    (``lookup_reply_template``). Otherwise writes from scratch.
    """
    from crewai import Agent
    return Agent(
        role="Reply Writer",
        goal=(
            "Compose a clear, polite reply that addresses every key point from "
            "the analyst. Reach for a stock template when the scenario fits "
            "(meeting-accept, customer-apology, polite-followup); otherwise "
            "write fresh. Keep it concise — under 200 words for routine replies."
        ),
        backstory=(
            "You're a senior business writer who has answered tens of thousands "
            "of emails. Your replies always lead with what the recipient cares "
            "about, never bury the ask, and never include filler ('I hope this "
            "email finds you well'). You write the body — the polisher handles "
            "tone & sign-off."
        ),
        llm=llm,
        tools=[TemplateTool()],
        allow_delegation=False,
        verbose=False,
    )


def build_polisher_agent(llm: Any) -> Any:
    """Stage 3 — apply the user's tone preset + signature, output ``DraftItem``.

    This is also where ``email-tone`` Skill knowledge is consulted via
    ``lookup_tone_guidance``. Output is a ``DraftItem`` JSON.
    """
    from crewai import Agent
    return Agent(
        role="Voice Polisher",
        goal=(
            "Apply the user's preferred tone preset and signature to the draft "
            "produced by the writer. Output a JSON object that matches the "
            "DraftItem schema exactly."
        ),
        backstory=(
            "You're an editor who never changes WHAT was said — only HOW. You "
            "match the user's writing voice (warm vs formal, brief vs "
            "explanatory) and add the canonical sign-off. You ship JSON, not prose."
        ),
        llm=llm,
        tools=[ToneTool()],
        allow_delegation=False,
        verbose=False,
    )
