"""Unit tests for ``_nodes._normalize_draft`` — post-LLM safety net.

When the polisher LLM returns malformed drafts (empty subject, just "Re:",
blank body, etc.), the user shouldn't see broken cards in the HITL UI.
``_normalize_draft`` patches these from the source email.

Run with::

    pytest agents/email/tests/test_normalize_draft.py -v
"""
from __future__ import annotations

from datetime import datetime, timezone

from _models import ClassifiedEmail, DraftItem, Email
from _nodes import _normalize_draft


def _ce(subject: str = "Production 500", sender: str = "ops@bigcustomer.com") -> ClassifiedEmail:
    return ClassifiedEmail(
        email=Email(
            id="m1",
            from_=sender,
            to=["me@x.com"],
            subject=subject,
            body_text="hello",
            received_at=datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc),
            thread_id="thr_m1",
        ),
        category="urgent_customer",
        needs_reply=True,
        priority=95,
        reason="VIP outage",
    )


def _draft(**overrides) -> DraftItem:
    base = dict(
        email_id="m1",
        to=["ops@bigcustomer.com"],
        subject="Re: Production 500",
        body="Working on it.",
        tone="urgent",
        confidence=0.85,
        rationale="",
    )
    base.update(overrides)
    return DraftItem(**base)


# ─── subject patching ───────────────────────────────────────────────────────


def test_empty_subject_falls_back_to_re_plus_original():
    out = _normalize_draft(_draft(subject=""), _ce(subject="Production 500"))
    assert out.subject == "Re: Production 500"


def test_just_re_falls_back():
    out = _normalize_draft(_draft(subject="Re:"), _ce(subject="Production 500"))
    assert out.subject == "Re: Production 500"


def test_just_re_with_space_falls_back():
    out = _normalize_draft(_draft(subject="Re: "), _ce(subject="Production 500"))
    assert out.subject == "Re: Production 500"


def test_real_subject_left_alone():
    out = _normalize_draft(
        _draft(subject="Re: Production 500 — Working on it"),
        _ce(subject="Production 500"),
    )
    assert out.subject == "Re: Production 500 — Working on it"


def test_subject_when_original_also_empty():
    out = _normalize_draft(_draft(subject=""), _ce(subject=""))
    assert out.subject == "Re: (无主题)"


# ─── body patching ──────────────────────────────────────────────────────────


def test_empty_body_gets_placeholder():
    out = _normalize_draft(_draft(body=""), _ce())
    assert "草稿生成失败" in out.body
    # Other fields preserved
    assert out.email_id == "m1"
    assert out.subject == "Re: Production 500"


def test_whitespace_only_body_gets_placeholder():
    out = _normalize_draft(_draft(body="   \n  "), _ce())
    assert "草稿生成失败" in out.body


# ─── email_id / to patching ─────────────────────────────────────────────────


def test_missing_email_id_filled_in():
    out = _normalize_draft(_draft(email_id=""), _ce())
    assert out.email_id == "m1"


def test_empty_to_falls_back_to_sender():
    out = _normalize_draft(
        _draft(to=[]),
        _ce(sender="ceo@vipclient.com"),
    )
    assert out.to == ["ceo@vipclient.com"]


# ─── no-op when everything is fine ──────────────────────────────────────────


def test_perfect_draft_passes_through_unchanged():
    d = _draft()
    out = _normalize_draft(d, _ce())
    # Same content (model_copy with no patch returns the same instance)
    assert out is d


def test_multiple_problems_all_fixed_at_once():
    out = _normalize_draft(
        _draft(subject="Re:", body="", to=[], email_id=""),
        _ce(subject="Q3 报告", sender="boss@company.com"),
    )
    assert out.subject == "Re: Q3 报告"
    assert "草稿生成失败" in out.body
    assert out.to == ["boss@company.com"]
    assert out.email_id == "m1"
