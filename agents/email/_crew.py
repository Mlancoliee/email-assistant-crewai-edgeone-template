"""CrewAI Crew assembly — the email draft sub-pipeline.

The ``draft`` LangGraph node calls ``build_email_draft_crew(...)`` once per
email needing a reply, then runs ``crew.kickoff()`` inside ``asyncio.to_thread``.

Why per-email crews? Tasks are built with f-string interpolation at build
time (see ``_tasks.py``) so the prompts have no runtime placeholders. The
trade-off vs reusing a single crew is one extra builder pass per email —
negligible compared to the LLM call.

P0 boundaries:
  - ``Process.sequential`` — three tasks run in order, no early-exit
  - ``memory=False`` — we use ``ctx.store`` for cross-run state, not the
    CrewAI internal memory (matches sibling templates)
  - ``skills=[...]`` points to the local SKILL.md directories so CrewAI
    1.14+ loads the tone / template skills natively
  - ``verbose=False`` — events go via ``crewai_event_bus`` to ``_events``,
    not stdout
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from _agents import build_filter_agent, build_polisher_agent, build_writer_agent
from _models import ClassifiedEmail, UserRulesBundle
from _tasks import build_analyze_task, build_draft_task, build_polish_task


_SKILLS_DIR = Path(__file__).resolve().parent / "skills"


def _resolve_skill_dirs() -> list[str]:
    """Return absolute paths to local skill directories that exist on disk."""
    dirs: list[str] = []
    for name in ("email-tone", "email-templates"):
        candidate = _SKILLS_DIR / name
        if candidate.is_dir():
            dirs.append(str(candidate))
    return dirs


def build_email_draft_crew(
    llm: Any,
    *,
    classified: ClassifiedEmail,
    rules: UserRulesBundle,
    regenerate_feedback: str | None = None,
) -> Any:
    """Assemble the three-role Sequential Crew for drafting one reply.

    Args:
        llm: pre-configured CrewAI ``LLM`` (see ``_llm.get_crewai_llm``).
        classified: the email + classifier output to draft a reply for.
        rules: aggregated user rules (tone / signature / language).
        regenerate_feedback: optional user feedback from a previous review
            decision with action="regenerate" — fed into the draft task so
            the writer knows what to change (e.g. "用英文重写").

    Returns:
        A ready-to-kickoff ``Crew``. Call ``crew.kickoff()`` with no inputs;
        all data is already baked into the task descriptions.
    """
    from crewai import Crew, Process

    email = classified.email
    filter_a = build_filter_agent(llm)
    writer_a = build_writer_agent(llm)
    polisher = build_polisher_agent(llm)

    analyze = build_analyze_task(
        filter_a,
        email_sender=email.sender,
        email_subject=email.subject,
        email_body=email.body_text,
        email_thread_id=email.thread_id or "",
        has_ics=email.has_ics,
        category=classified.category,
        reason=classified.reason,
    )
    draft = build_draft_task(
        writer_a,
        analyze,
        language=rules.language,
        regenerate_feedback=regenerate_feedback,
    )
    polish = build_polish_task(
        polisher,
        draft,
        analyze,
        email_id=email.id,
        email_sender=email.sender,
        email_subject=email.subject,
        default_tone=rules.default_tone,
        signature=rules.signature,
    )

    crew_kwargs: dict[str, Any] = {
        "agents": [filter_a, writer_a, polisher],
        "tasks": [analyze, draft, polish],
        "process": Process.sequential,
        "memory": False,
        "verbose": False,
    }
    skills = _resolve_skill_dirs()
    if skills:
        crew_kwargs["skills"] = skills

    return Crew(**crew_kwargs)
