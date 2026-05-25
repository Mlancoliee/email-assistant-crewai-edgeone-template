"""CrewAI Task definitions — three tasks chained sequentially.

Task flow:

    analyze_task  →  EmailAnalysis (intermediate, consumed by writer)
    draft_task    →  raw draft body (intermediate, consumed by polisher)
    polish_task   →  DraftItem (FINAL, output_pydantic)

Only ``polish_task`` declares ``output_pydantic=DraftItem`` — that's what the
``draft`` LangGraph node reads via ``CrewOutput.pydantic`` (or
``CrewOutput.json_dict`` as fallback).

Substitution strategy:

    All values are interpolated AT BUILD TIME via Python f-strings — the
    final task ``description`` strings are plain text with no ``{...}``
    placeholders. This avoids fragile CrewAI runtime substitution (where
    nested access like ``{email[sender]}`` works inconsistently across
    versions) and matches the sibling marketing template's pattern.

    Trade-off: tasks must be (re)built per email, not once per crew. The
    ``draft`` LangGraph node therefore calls ``build_email_draft_crew`` on
    every iteration with the current email's data.
"""
from __future__ import annotations

from typing import Any

from _models import DraftItem


# Task name → UI card id (mirrors marketing template's TASK_TO_CARD_ID).
TASK_TO_CARD_ID: dict[str, str] = {
    "analyze_task": "analyze",
    "draft_task": "draft",
    "polish_task": "polish",
}


def _shorten(text: str, limit: int = 4000) -> str:
    """Trim very long bodies before stuffing into a prompt — keeps tokens bounded."""
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n…(truncated)"


def build_analyze_task(
    filter_agent: Any,
    *,
    email_sender: str,
    email_subject: str,
    email_body: str,
    email_thread_id: str,
    has_ics: bool,
    category: str,
    reason: str,
) -> Any:
    """Stage 1 — analyst reads the email and produces a structured brief.

    All email/category fields are inlined via f-string at build time. The
    final ``description`` contains no Python format placeholders.
    """
    from crewai import Task

    description = (
        "Read this incoming email and produce a structured analysis.\n\n"
        "EMAIL\n-----\n"
        f"From: {email_sender}\n"
        f"Subject: {email_subject}\n"
        f"Has calendar invite: {'yes' if has_ics else 'no'}\n"
        f"Body:\n{_shorten(email_body)}\n\n"
        "CLASSIFIER OUTPUT\n-----------------\n"
        f"Category: {category}\n"
        f"Why it needs reply: {reason}\n\n"
        f"Use the ``fetch_thread_history`` tool with thread_id "
        f"``{email_thread_id or '(none)'}`` to check for prior context.\n\n"
        "Produce a markdown brief with these sections:\n"
        "  1. Sender's true intent (1–2 sentences)\n"
        "  2. Key points the reply MUST address (numbered list, max 3)\n"
        "  3. Suggested reply template name if applicable (one of: "
        "meeting-accept, meeting-decline, polite-followup, "
        "customer-apology, or 'none')\n"
        "  4. Tone recommendation (formal | friendly_professional | "
        "apologetic | urgent | concise) — explain why in one sentence\n"
    )
    return Task(
        name="analyze_task",
        description=description,
        expected_output="A markdown brief with the four sections.",
        agent=filter_agent,
    )


def build_draft_task(
    writer_agent: Any,
    analyze: Any,
    *,
    language: str,
    regenerate_feedback: str | None = None,
) -> Any:
    """Stage 2 — writer produces a draft body that satisfies the brief.

    If ``regenerate_feedback`` is supplied (HITL re-write), it's injected
    into the draft instructions so the LLM knows what to change.
    """
    from crewai import Task

    feedback_block = ""
    if regenerate_feedback and regenerate_feedback.strip():
        feedback_block = (
            "\nUSER FEEDBACK ON THE PREVIOUS DRAFT (highest priority — apply it):\n"
            f"  >>> {regenerate_feedback.strip()} <<<\n"
        )

    description = (
        "Using the analyst's brief, draft the reply body.\n\n"
        "If the brief's suggested template is not 'none', call "
        "``lookup_reply_template`` first and adapt it to this specific "
        "email. Otherwise write from scratch.\n\n"
        "Rules:\n"
        "  - Address every key point from the brief\n"
        "  - Lead with what the recipient cares about most\n"
        "  - No filler openers ('I hope this finds you well', 'Thanks for "
        "reaching out')\n"
        "  - Stay under 200 words for routine replies, under 350 for "
        "complex ones\n"
        f"  - Reply in {language} (override the original email's language "
        "if the user feedback below requests a specific language)\n"
        "  - Do NOT add a sign-off / signature — the polisher handles that\n"
        f"{feedback_block}"
    )
    return Task(
        name="draft_task",
        description=description,
        expected_output="Plain markdown body text. No sign-off, no JSON.",
        agent=writer_agent,
        context=[analyze],
    )


def build_polish_task(
    polisher_agent: Any,
    draft: Any,
    analyze: Any,
    *,
    email_id: str,
    email_sender: str,
    email_subject: str,
    default_tone: str,
    signature: str,
) -> Any:
    """Stage 3 — apply tone + signature, emit a JSON ``DraftItem``.

    The required JSON fields are inlined as f-string values so the LLM
    sees the exact ``email_id`` / ``to`` / ``subject`` to copy verbatim
    (no placeholder leakage).
    """
    from crewai import Task

    fallback_subject = f"Re: {email_subject}" if email_subject else "Re: (no subject)"

    description = (
        "Polish the writer's draft and emit a final JSON DraftItem.\n\n"
        "Steps:\n"
        f"  1. Call ``lookup_tone_guidance`` with the analyst's recommended "
        f"tone (or '{default_tone}' if 'none').\n"
        "  2. Adjust phrasing to match the tone — keep the SAME content; "
        "only change HOW it's said.\n"
        f"  3. Append the user's signature on its own line: '{signature}'\n"
        "  4. Output ONLY a JSON object with these EXACT field values "
        "(copy the email_id / to / subject as-is):\n"
        "{\n"
        f'  "email_id": "{email_id}",\n'
        f'  "to": ["{email_sender}"],\n'
        f'  "subject": "{fallback_subject}",\n'
        '  "body": "<polished body + signature>",\n'
        '  "tone": "<the tone you applied>",\n'
        '  "template_used": "<template name or null>",\n'
        '  "confidence": <0.0 to 1.0>,\n'
        '  "rationale": "<one sentence why this reply works>"\n'
        "}\n\n"
        "Output ONLY the JSON. No markdown fences. No prose."
    )
    return Task(
        name="polish_task",
        description=description,
        expected_output="A JSON object matching the DraftItem schema.",
        agent=polisher_agent,
        context=[draft, analyze],
        output_pydantic=DraftItem,
    )
