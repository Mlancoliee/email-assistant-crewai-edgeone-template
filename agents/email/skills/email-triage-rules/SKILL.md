---
name: email-triage-rules
description: User-specific overrides for how to classify and prioritize incoming emails. Loaded by the classify node when triaging an inbox so VIP relationships, recurring sender patterns, and ambiguous-case rules surface in addition to the LLM's general heuristics.
license: Apache-2.0
metadata:
  version: "1.0"
  scope: classification
---

# Email Triage Rules

Customizable rules that supplement the classifier's general priority
heuristics. Read this whenever classifying a batch — these are the user's
explicit preferences and override conventional defaults.

## Sender heuristics

- Anyone from `vipcustomer.com` or `bigclient.com` defaults to
  `urgent_customer` even if the surface text looks routine. They are paid
  enterprise customers; their "minor question" is our P1.
- Senders matching `noreply@*` are almost always `notification` —
  prioritize ≤ 30 unless the subject contains "security" or "incident".
- `billing@*` / `accounting@*` / `finance@*` from third parties: usually
  `billing`. Don't flag for reply unless an action is required (rare —
  most are autopay confirmations).

## Subject heuristics

- Square-bracket prefixes like `[URGENT]`, `[ACTION REQUIRED]`, `[P0]`
  generally warrant priority bumps to ≥ 80.
- Subjects starting with `Re: Re: ` (multi-reply chain) are typically
  `followup` — boost priority by ~10 from the LLM's first guess if the
  user is in the To field (they explicitly need to weigh in).
- Subjects with `[Repo]`, `[CI]`, `[Build]` are GitHub / CI notifications
  — `notification`, low priority.

## Body heuristics

- Body containing "down" + "production" / "outage" / "500 errors" →
  `urgent_customer`, priority ≥ 90.
- Body with calendar invite metadata (`BEGIN:VCALENDAR`) → `meeting`,
  needs_reply=true.
- Body containing words like "unsubscribe" / "promo" / "30% off" near
  the top → `marketing`, priority ≤ 10.

## Edge cases

- A meeting invite from a VIP domain → `urgent_customer` (NOT `meeting`).
  The fact that they're scheduling time means a topic is already on
  their mind — read it like a regular ask, not just a calendar event.
- Auto-replies (Subject contains "Auto-reply" / "Out of office") → `other`,
  priority 0, needs_reply=false. They're informational only.
- Forwarded threads (subject starts with `Fwd: `) — read the original
  sender's intent, not the forwarder's. The forwarder is rarely who
  needs a reply.

## Output reminder

This skill ONLY influences the classifier's input. The output schema is
unchanged — still emit JSON with `id`, `category`, `needs_reply`,
`priority`, `reason`. Don't add fields.
