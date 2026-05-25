# Email Classifier — design doc

> This is documentation for the ``classify`` LangGraph node. The actual
> system prompt lives in ``_nodes.CLASSIFY_SYSTEM`` (Python string) so
> we can iterate without re-reading a file at runtime.

## Categories

| key                | meaning                                            | example                               |
|--------------------|----------------------------------------------------|---------------------------------------|
| `urgent_customer`  | Customer-facing issues affecting biz operation     | Production 500 errors from a paid customer |
| `meeting`          | Calendar invites, reschedules, RSVP requests       | An ICS or "Can we meet Friday at 3pm?" |
| `internal`         | Internal team comms (FYI / report / leave)         | Weekly engineering update, "I'm out Thursday" |
| `marketing`        | Newsletters, promos, vendor pitches                | "🚀 30% off Pro!"                     |
| `notification`     | Automated system messages                          | GitHub PR review request, CI failure  |
| `followup`         | External party pinging again on a prior thread     | "Re: Re: Re: about the quote"         |
| `spam`             | Unsolicited bulk / phishing / scams                | "You won 1M USDT!!!"                  |
| `billing`          | Invoices, receipts, payment notifications          | "Your May invoice ¥2340"              |
| `other`            | Doesn't fit any of the above                       | —                                     |

## Priority guidance (LLM heuristics, 0-100)

- **80-100**: customer outage, security incident, VIP urgent question
- **60-79**: meeting needing prompt RSVP, important external follow-up
- **40-59**: typical internal asks, FYI worth reading
- **20-39**: automated notifications, low-priority FYI
- **0-19**: marketing, billing reminders on autopay, spam

The downstream `prioritize` node applies post-LLM rule-based boosts (VIP
domain +20, ICS attendance +10, urgent_customer ×1.2, spam clamp). **Don't
double-count those here** — the LLM's score is the baseline, the rules nudge.

## Output contract

Strictly a JSON object `{"results": [...]}` where the array is in input
order, one item per email:

```json
{
  "id": "<email-id>",
  "category": "urgent_customer | meeting | ...",
  "needs_reply": true,
  "priority": 87,
  "reason": "Production outage from paying customer."
}
```

No markdown fences. No prose. The `_nodes.classify` parser is forgiving
(falls back from `results`→`emails`→first list) but reliability matters
for token economy.

## Token economy

`_compact_inbox_for_llm` trims each email to `{id, from, subject, snippet[:600], has_ics}`
to keep the batch prompt ≤ ~6k tokens for a 10-email run on Sonnet/DeepSeek.
For larger inboxes (100+) we'll chunk in 20-email batches in W3.
