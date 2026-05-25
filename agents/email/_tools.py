"""CrewAI BaseTool subclasses for the ``EmailDraftCrew``.

Three tools — each a thin filesystem-backed lookup so the agents have
something concrete to call (and the trace shows useful tool invocations
in the SSE stream):

  - ``ToneTool`` — read ``skills/email-tone/SKILL.md`` + few-shot examples
  - ``TemplateTool`` — read ``skills/email-templates/templates/{name}.md``
  - ``ThreadContextTool`` — return prior emails on the same thread

In Week 2 D3 we wire ``Crew(skills=[...])`` for native skill loading, but
exposing them as **tools** too is useful: the LLM can selectively call
``lookup_tone_guidance`` for one email and skip it for another.

The module imports gracefully when ``crewai`` isn't installed (returns
sentinel ``HAS_CREWAI = False``) so unit tests in environments without
the heavy dep can still import this file.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# Defer the BaseTool import so non-CrewAI environments (e.g. parsing tests)
# can still import this module — they just can't instantiate the tools.
try:
    from crewai.tools import BaseTool as _BaseTool  # type: ignore[import-not-found]
    HAS_CREWAI = True
except ImportError:
    HAS_CREWAI = False

    class _BaseTool:  # type: ignore[no-redef]
        """Fallback BaseTool stub for environments without crewai installed."""

        name: str = ""
        description: str = ""
        args_schema: type[BaseModel] | None = None

        def _run(self, *args: Any, **kwargs: Any) -> str:
            raise RuntimeError("crewai is not installed; cannot run tools")


SKILLS_DIR = Path(__file__).resolve().parent / "skills"


# ─── Tool argument schemas ──────────────────────────────────────────────────


class ToneArgs(BaseModel):
    tone: str = Field(
        "friendly_professional",
        description="Target tone preset: formal | friendly_professional | apologetic | urgent | concise",
    )


class TemplateArgs(BaseModel):
    template_name: str = Field(
        ...,
        description="Template stem name (e.g. meeting-accept, polite-followup, customer-apology)",
    )


class ThreadContextArgs(BaseModel):
    thread_id: str = Field(..., description="Thread id from Email.thread_id")


# ─── Pure helper functions (testable without crewai) ────────────────────────


def lookup_tone(tone: str = "friendly_professional") -> str:
    """Return the SKILL.md body + a peek at few-shot examples."""
    skill_dir = SKILLS_DIR / "email-tone"
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return f"(no tone skill installed for '{tone}')"
    body = skill_md.read_text(encoding="utf-8")
    examples_dir = skill_dir / "examples"
    examples_text = ""
    if examples_dir.is_dir():
        for f in sorted(examples_dir.glob("*.eml")):
            snippet = f.read_text(encoding="utf-8", errors="replace")[:400]
            examples_text += f"\n\n---\nExample: {f.name}\n{snippet}"
    return f"# Tone preset: {tone}\n\n{body}{examples_text}"


def lookup_template(template_name: str) -> str:
    """Return the body of a template by stem name."""
    path = SKILLS_DIR / "email-templates" / "templates" / f"{template_name}.md"
    if not path.is_file():
        templates_dir = SKILLS_DIR / "email-templates" / "templates"
        available = []
        if templates_dir.is_dir():
            available = sorted(f.stem for f in templates_dir.glob("*.md"))
        return f"(no template '{template_name}'; available: {available})"
    return path.read_text(encoding="utf-8")


def lookup_thread_context(thread_id: str) -> str:
    """Return prior thread history.

    Mock provider has none (each fixture is standalone). The real IMAP
    provider in W3 will query messages on this thread_id here.
    """
    return f"(no prior history available for {thread_id} in this demo)"


# ─── CrewAI tool wrappers ────────────────────────────────────────────────────


class ToneTool(_BaseTool):
    name: str = "lookup_tone_guidance"
    description: str = (
        "Return guidance + few-shot examples for a target email tone "
        "(formal, friendly_professional, apologetic, urgent, concise). "
        "Use when matching the user's voice in a draft."
    )
    args_schema: type[BaseModel] = ToneArgs

    def _run(self, tone: str = "friendly_professional") -> str:
        return lookup_tone(tone)


class TemplateTool(_BaseTool):
    name: str = "lookup_reply_template"
    description: str = (
        "Return the body of a pre-approved reply template by name "
        "(meeting-accept, meeting-decline, polite-followup, customer-apology). "
        "Use when an inbound email matches a standard scenario."
    )
    args_schema: type[BaseModel] = TemplateArgs

    def _run(self, template_name: str) -> str:
        return lookup_template(template_name)


class ThreadContextTool(_BaseTool):
    name: str = "fetch_thread_history"
    description: str = (
        "Return prior emails on the same thread. Use to ground replies in "
        "what's been said before. Returns a 'no prior history' note for new "
        "threads — that's expected for the mock provider."
    )
    args_schema: type[BaseModel] = ThreadContextArgs

    def _run(self, thread_id: str) -> str:
        return lookup_thread_context(thread_id)
