# Summarizer — design doc

> Documentation for the ``summarize`` LangGraph node (lands W1 D5). The
> actual prompt lives in ``_nodes.SUMMARIZE_SYSTEM`` once implemented.

## Purpose

Produce the final markdown digest the UI shows when the run completes.
Goes into `state.summary` and is also surfaced via SSE `event="done"`.

## Sections (in order)

1. **概览** — total emails fetched, # auto-archived, # classified, # drafted
2. **需要你关注的** — top 5 prioritized emails, each one line:
   `[priority] subject — sender — reason`
3. **草稿待审批 / 已处理** — count + per-email status:
   `email_id | subject | decision (approve/edit/regenerate/skip)`
4. **本次归档 / 已读** — list of email_ids the apply node side-effected
5. **下一步建议** — natural language: "明天可以开始 Q3 路演准备 / 三封发票
   已自动归档,需要时可以在控制台找回"

## Tone

Concise, business-friendly, in `user_rules.language` (default `zh-CN`).
Don't repeat the per-email reasoning verbatim — that's already in `state.classified`.

## Output

Plain markdown string assigned to `state.summary` (and forwarded by `run.py`
in the final SSE `event="done"` frame). Length budget: ≤ 800 字符.

## Failure mode

If the LLM call errors, `summarize` writes a fallback summary built from
`state.drafts` / `state.review_decisions` / `state.final_actions` (no LLM)
and appends the error to `state.errors`. The UI still shows something useful.
