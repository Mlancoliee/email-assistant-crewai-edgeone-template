# Priority Booster — rule-based design doc

> Documentation for the ``prioritize`` LangGraph node. **No LLM call** — pure
> rules over the classifier output. Rules live in ``_nodes.prioritize``.

## Inputs

- `state.classified`: `list[ClassifiedEmail]` (already has LLM priority 0-100)
- `state.user_rules`: `list[UserRule]` derived from `fixtures/user_rules.json`

## Pipeline (cumulative)

1. **VIP domain boost** — if `email.sender` contains any `vip_domains`
   entry → `priority += 20` (capped at 100).
2. **Calendar invite boost** — if `email.has_ics && needs_reply` →
   `priority += 10` (capped at 100). Skipped when `needs_reply=false`
   to avoid bumping accidentally-shared invites.
3. **Urgent customer multiplier** — if `category == "urgent_customer"` →
   `priority := int(priority * 1.2)` (capped at 100).
4. **Spam clamp** — if `category == "spam"` → `priority := 0`. Always last,
   so a misclassified VIP-spam still ends up at 0.

## Filter

Drop emails where `needs_reply == false AND priority < min_priority`
(default `min_priority = 30`).

## Sort

`priority desc`, then `received_at asc` within the same priority bucket
(older emails surface first when priorities tie — they've been waiting longer).

## Cursor reset

`prioritize` resets `state.cursor = 0`. The `apply` node bumps cursor
before routing to `draft` (next email) or `summarize` (done).

## Why no LLM here?

The classifier already used LLM judgement to assign priority. This stage is
deterministic personalization — VIP lists, archive rules, signature — that
the user owns and audits in `user_rules.json`. Determinism here also keeps
the unit tests fast and offline.
