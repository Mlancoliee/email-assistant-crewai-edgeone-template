"""SKILL.md loader for LangGraph nodes.

CrewAI 1.14+ has native ``Crew(skills=[...])`` support — Skill files placed
in declared directories are auto-loaded into agent system prompts. LangGraph
has no equivalent built-in (it's a lower-level graph framework, not an Agent
framework), so this loader bridges the gap: it parses the YAML frontmatter
+ Markdown body of any ``SKILL.md`` and lets a LangGraph node concatenate
the body into its LLM prompt on demand.

Used by ``classify`` / ``summarize`` / future LangGraph nodes that want
the same Skill knowledge available inside the CrewAI sub-pipeline.

Format:
    ---
    name: <skill-name>
    description: <one-paragraph trigger description>
    license: ...
    metadata: {...}
    ---

    # Skill Body
    ...

The frontmatter parser is intentionally minimal — no YAML library
dependency, just enough to extract the documented fields. Keep SKILL.md
files simple (no nested mappings beyond ``metadata: {...}``).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_SKILLS_DEFAULT_ROOT = Path(__file__).resolve().parent / "skills"

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def parse_skill(md_path: Path | str) -> tuple[dict[str, Any], str]:
    """Read a SKILL.md file and return ``(frontmatter, body)``.

    Frontmatter is a simple ``key: value`` mapping (one level deep). If
    the file has no ``---`` block, returns ``({}, full_text)``.

    Returns ``({"name": "..."}, "")`` if the file doesn't exist.
    """
    path = Path(md_path)
    if not path.is_file():
        return ({"name": path.parent.name if path.parent else "unknown",
                 "missing": True}, "")

    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text.lstrip("﻿"))  # tolerate BOM
    if not match:
        return ({}, text)

    raw_fm, body = match.group(1), match.group(2).lstrip("\n")
    frontmatter = _parse_frontmatter(raw_fm)
    return frontmatter, body


def load_skill(name: str, *, base: Path | str | None = None) -> tuple[dict[str, Any], str]:
    """Look up a Skill by directory name.

    Args:
        name: directory name under ``base``, e.g. ``"email-tone"``.
        base: directory containing skill subdirs. Defaults to ``./skills/``
            relative to this module (the email-assistant template).

    Returns:
        ``(frontmatter, body)``. Falls back to ``({"missing": True}, "")``
        if the skill doesn't exist.
    """
    root = Path(base) if base is not None else _SKILLS_DEFAULT_ROOT
    return parse_skill(root / name / "SKILL.md")


def render_skill_for_prompt(name: str, *, base: Path | str | None = None,
                            max_chars: int = 4000) -> str:
    """Render a Skill as a prompt-ready snippet.

    Output:

        ## Skill: <name>
        <description>

        <body, truncated as needed to fit max_chars total>

    The total returned string is bounded by ``max_chars`` (header +
    description + body all count). Falls back to a single-line
    ``"(skill <name> not installed)"`` if the SKILL.md is missing — keeps
    the LLM call working in degraded environments.
    """
    fm, body = load_skill(name, base=base)
    if fm.get("missing"):
        return f"(skill {name!r} not installed)"

    description = (fm.get("description") or "").strip()
    name_str = fm.get("name", name)
    header = f"## Skill: {name_str}"

    # Build with the header always present; clip description + body if needed.
    pieces: list[str] = [header]
    if description:
        pieces.append(description)
    if body:
        pieces.append(body.strip())

    rendered = "\n\n".join(pieces)
    if len(rendered) <= max_chars:
        return rendered

    suffix = "\n\n[...truncated for prompt budget...]"
    keep = max(0, max_chars - len(suffix))
    return rendered[:keep].rstrip() + suffix


def list_skills(*, base: Path | str | None = None) -> list[dict[str, Any]]:
    """Discover all SKILL.md files under ``base``. Returns frontmatter dicts
    augmented with the resolved directory path under key ``_dir``.
    """
    root = Path(base) if base is not None else _SKILLS_DEFAULT_ROOT
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for skill_dir in sorted(root.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        fm, _ = parse_skill(skill_md)
        if fm.get("missing"):
            continue
        fm = dict(fm)
        fm["_dir"] = str(skill_dir)
        out.append(fm)
    return out


# ─── Frontmatter parser ─────────────────────────────────────────────────────


def _parse_frontmatter(raw: str) -> dict[str, Any]:
    """Tiny YAML-ish parser — handles only the shapes we use in SKILL.md.

    Supported:
      - ``key: value``     → string value
      - ``key:`` followed by indented ``  subkey: value`` lines → dict
      - ``key: ["a", "b"]`` (single-line lists, optional)

    Strips quoted strings.
    """
    result: dict[str, Any] = {}
    current_dict_key: str | None = None
    for raw_line in raw.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            current_dict_key = None
            continue

        # Indented continuation (sub-dict)
        if raw_line.startswith("  ") and current_dict_key is not None:
            sub_line = raw_line.strip()
            if ":" in sub_line:
                k, _, v = sub_line.partition(":")
                if not isinstance(result.get(current_dict_key), dict):
                    result[current_dict_key] = {}
                result[current_dict_key][k.strip()] = _coerce_scalar(v.strip())
            continue

        if ":" not in raw_line:
            current_dict_key = None
            continue

        key, _, value = raw_line.partition(":")
        key = key.strip()
        value = value.strip()
        if not value:
            # Header for a sub-dict that follows
            current_dict_key = key
            result[key] = {}
            continue

        result[key] = _coerce_scalar(value)
        current_dict_key = None
    return result


def _coerce_scalar(value: str) -> Any:
    """Strip surrounding quotes and recognize boolean / null sentinels."""
    if not value:
        return ""
    if value.startswith("[") and value.endswith("]"):
        # Single-line list e.g. ["a", "b"]
        inner = value[1:-1].strip()
        if not inner:
            return []
        items = [_coerce_scalar(p.strip()) for p in inner.split(",")]
        return items
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in ("null", "~"):
        return None
    return value
