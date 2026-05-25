"""Pydantic data models for the email-assistant template.

These models live in the LangGraph state (``_state.EmailAssistantState``) and
are used at three boundaries:

  1. Mock fixture deserialization (``_providers.MockProvider``)
  2. CrewAI Crew structured output (``_crew``/``_tasks`` use ``output_pydantic``)
  3. SSE frames sent to the frontend (``model_dump()`` on these classes)

Schema is intentionally minimal. Storage / serialization details (e.g. blob
keys, ETag, IMAP UID) live in ``_providers``, not here.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─── Categories & enums ─────────────────────────────────────────────────────

EmailCategory = Literal[
    "urgent_customer",   # VIP / 客户严重问题(P0)
    "meeting",           # 会议邀请、改期、取消
    "internal",          # 团队内部 FYI、周报、请假
    "marketing",         # 推广、活动、促销邮件
    "notification",      # 系统/平台自动通知(GitHub、Jira 等)
    "followup",          # 来自外部的二次跟进
    "spam",              # 垃圾/钓鱼/中奖
    "billing",           # 账单、发票、付款提醒
    "other",
]

ToneStyle = Literal[
    "formal",
    "friendly_professional",
    "apologetic",
    "urgent",
    "concise",
]

ReviewAction = Literal[
    "approve",      # 接受当前草稿,写入 Drafts
    "edit",         # 用 edited_body 替换草稿后写入
    "reject",       # 不回复,标记已读 / 归档
    "regenerate",   # 让 Crew 重新生成草稿(可带 feedback)
    "skip",         # 跳过本封,继续下一封
]

ApplyOp = Literal[
    "save_draft",
    "archive",
    "mark_read",
    "label",
    "skip",
]


# ─── Email & metadata ────────────────────────────────────────────────────────


class Email(BaseModel):
    """A single inbound email parsed from RFC 5322 EML or IMAP fetch."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Stable id (UID for IMAP, filename stem for fixture)")
    sender: str = Field(..., alias="from_", description="From address (display + email)")
    to: list[str] = Field(default_factory=list)
    cc: list[str] = Field(default_factory=list)
    subject: str
    body_text: str = Field(..., description="Plain text body, decoded UTF-8")
    body_html: Optional[str] = None
    received_at: datetime
    thread_id: Optional[str] = Field(None, description="Provider-specific thread id (e.g. References hash)")
    has_ics: bool = Field(False, description="True when an ICS / iCalendar attachment is present")
    attachments: list[str] = Field(default_factory=list, description="Filenames of attachments")


# ─── Triage output (classify + prioritize nodes) ─────────────────────────────


class ClassifiedEmail(BaseModel):
    """Email + triage labels.

    Produced by the ``classify`` node and refined by ``prioritize``.
    """

    email: Email
    category: EmailCategory
    needs_reply: bool = Field(..., description="True iff the email warrants drafting a reply")
    priority: int = Field(..., ge=0, le=100, description="Higher = more urgent; 0 = ignore")
    reason: str = Field(..., description="One-sentence justification, shown in UI")


# ─── Draft generation (CrewAI sub-pipeline output) ───────────────────────────


class DraftItem(BaseModel):
    """A reply draft produced by the CrewAI ``EmailDraftCrew``."""

    email_id: str = Field(..., description="The Email.id this draft replies to")
    to: list[str] = Field(..., description="Reply recipient(s)")
    subject: str = Field(..., description="Reply subject (usually 'Re: ...')")
    body: str = Field(..., description="Reply body, plain text + markdown allowed")
    tone: ToneStyle = "friendly_professional"
    template_used: Optional[str] = Field(None, description="Skill template name if one was applied")
    confidence: float = Field(0.7, ge=0.0, le=1.0, description="Self-rated confidence")
    rationale: str = Field("", description="Why this reply (shown in approval card)")


# ─── Human-in-the-loop ───────────────────────────────────────────────────────


class ReviewDecision(BaseModel):
    """Human reviewer's decision, sent back via POST /email/review."""

    email_id: str
    action: ReviewAction
    edited_body: Optional[str] = Field(None, description="Required when action='edit'")
    feedback: Optional[str] = Field(None, description="Optional natural-language hint, used by 'regenerate'")


# ─── Final actions (apply node output) ───────────────────────────────────────


class Action(BaseModel):
    """A side-effect to perform on the mailbox after review."""

    email_id: str
    op: ApplyOp
    payload: dict = Field(default_factory=dict, description="Op-specific data, e.g. {'draft_id': '...'}")


# ─── User rules ──────────────────────────────────────────────────────────────


class UserRule(BaseModel):
    """A single personalization rule.

    Stored as part of ``fixtures/user_rules.json`` and persisted across runs
    via ``ctx.kv``. Rules drive the prioritize node and the polisher's tone.
    """

    kind: Literal["vip_domain", "auto_archive", "label", "default_tone", "signature", "language"]
    value: str
    note: Optional[str] = None


class UserRulesBundle(BaseModel):
    """Convenience aggregate of the rule set, loaded once per run."""

    vip_domains: list[str] = Field(default_factory=list)
    auto_archive: list[str] = Field(default_factory=list, description="Sender addresses or domains to auto-archive")
    default_tone: ToneStyle = "friendly_professional"
    signature: str = ""
    language: str = "zh-CN"

    def to_rules(self) -> list[UserRule]:
        """Flatten into a list of ``UserRule`` for state.user_rules."""
        out: list[UserRule] = []
        for d in self.vip_domains:
            out.append(UserRule(kind="vip_domain", value=d))
        for s in self.auto_archive:
            out.append(UserRule(kind="auto_archive", value=s))
        if self.default_tone:
            out.append(UserRule(kind="default_tone", value=self.default_tone))
        if self.signature:
            out.append(UserRule(kind="signature", value=self.signature))
        if self.language:
            out.append(UserRule(kind="language", value=self.language))
        return out
