---
name: email-tone
description: Apply the user's preferred writing tone to an email draft. Use when composing a reply that should match a tone preset — formal, friendly_professional, apologetic, urgent, or concise. Always consult this skill before finalizing the polished draft.
license: Apache-2.0
metadata:
  version: "1.0"
  author: edgeone-templates
---

# Email Tone

Apply the right voice to a reply draft. Read this whenever you're about to
finalize wording. Tone is HOW the message is delivered — never change WHAT
is being said; that's the writer's job.

## When to use

- Polishing a draft just before final output
- After the writer agent has produced a body and you need to match the
  user's voice
- When the analyst's tone recommendation needs to be operationalized

## Tone presets

### `formal`

> Default for: external regulatory correspondence, legal-adjacent topics,
> communicating up the chain at a customer (CEO / GC / CFO).

- Full sentences. No contractions. No emojis.
- Open with "Dear {name}," and a one-line acknowledgment of context.
- Close with "Sincerely," or "Kind regards," followed by signature.
- Avoid hedges ("just", "maybe", "kinda"). Use direct verbs.
- Numbered lists for procedural items; never bulleted.

**Anti-patterns**: "Hi there!", "Just wanted to flag...", "Cheers!", emojis.

### `friendly_professional`

> Default tone — use when the analyst doesn't recommend something more specific.

- Warm but business-appropriate. Light contractions are fine ("I'll", "we're").
- Open with "Hi {name}," — first-name only when you've corresponded before;
  full name otherwise.
- Close with "Best," or "Thanks," followed by signature.
- One emoji per message MAX, only when celebratory or conveying empathy.
- Bullet points fine for action items.

**Anti-patterns**: filler openers ("I hope this email finds you well"),
forced enthusiasm, multiple emojis, excessive exclamation points.

### `apologetic`

> Use for: outage acknowledgments, missed deadlines, dropped balls, customer
> escalations where we are at fault.

- Open with the acknowledgment, NOT pleasantries:
  - 中文: "致歉" / "抱歉" / "对此造成的影响,我们深感歉意"
  - English: "I'm sorry that...", "Apologies for the disruption..."
- Take responsibility without excuses ("we missed this" not "this fell
  through the cracks").
- State remediation: what's being done, who's doing it, by when.
- End with the offer to discuss live ("happy to jump on a call").
- NEVER include emojis. NEVER blame the customer.

**Anti-patterns**: "we apologize for the inconvenience" (template-ese),
"this is unfortunate" (passive distance), pivoting to blame ("if you had
done X").

### `urgent`

> Use for: production incidents, time-bounded asks, escalations needing
> next-business-hour response.

- Lead with the action item or deadline. Don't bury the ask.
- Short paragraphs (≤ 3 sentences each). Visual breaks matter.
- Explicit timestamps: "by 18:00 CST today", "before EOD Tuesday".
- Bold or capitalize the deadline if it's hard.
- Provide a fallback contact: "if you can't reach me, ping {alternate}".

**Anti-patterns**: long preambles, ambiguous timing ("ASAP", "soon"),
buried CTAs.

### `concise`

> Use for: known-recipient internal comms, quick status updates, where
> brevity is a courtesy.

- 3–5 sentences total. No more.
- Skip the open / close pleasantries — go directly to the point.
- One bullet point list MAX, capped at 3 items.
- No emojis. No filler. The user's signature is the only sign-off.

**Anti-patterns**: explanatory paragraphs, "circling back", anything that
could be a bullet but is a paragraph.

## Sign-off

Always end with the user's signature on its own line, separated by a blank
line from the body. Pull the signature from `user_rules.json#signature`.

```
{body content}

{signature}
```

If the user's preferred language is `zh-CN`, the signature stays in its
original language (don't translate it).

## Few-shot examples

See `examples/`:

- `reply-to-vendor.eml` — friendly_professional, declining a sales pitch
- `decline-meeting.eml` — friendly_professional, alternative time offered
- `customer-apology.eml` — apologetic, outage acknowledgment with ETA

These are the user's actual past replies; mimic their cadence and word
choice when matching tone.

## Output contract

When invoked via `lookup_tone_guidance(tone)`, this skill returns the body
above + the few-shot examples concatenated. The polisher agent uses that
in its system context to rewrite the draft. Output format from the
polisher MUST be a JSON DraftItem (no markdown fences); the polished body
goes in the `body` field.
