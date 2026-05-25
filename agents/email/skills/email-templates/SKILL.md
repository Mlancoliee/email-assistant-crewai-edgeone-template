---
name: email-templates
description: Use proven reply templates for common scenarios. Use when an email matches one of - meeting accept/decline, polite followup, customer apology - to skip writing from scratch and ground the reply in a battle-tested structure.
license: Apache-2.0
metadata:
  version: "1.0"
  author: edgeone-templates
---

# Email Templates

A small library of reply templates for the highest-frequency email scenarios.
The Reply Writer agent calls `lookup_reply_template` when the analyst flags
a scenario; the template comes back as markdown that the writer adapts to
the specific email — fill in placeholders, drop sections that don't apply,
keep the structure.

## When to use

| Scenario                                | Template            |
|-----------------------------------------|---------------------|
| Calendar invite I can attend            | `meeting-accept`    |
| Calendar invite I can't attend          | `meeting-decline`   |
| External party went silent on a thread  | `polite-followup`   |
| Customer-facing outage / dropped ball   | `customer-apology`  |

## When NOT to use a template

- **VIP customer urgent issues** — write fully bespoke, the recipient
  deserves attention to their specific situation
- **Internal reports** — most don't need a reply at all; if they do, a
  one-line acknowledgment is fine
- **First contact with a new external party** — templates feel
  impersonal; introduce yourself properly first
- **Anything where the analyst flagged tone:urgent** — urgency requires
  custom framing (specific deadlines, specific stakes)

## Adaptation rules

1. **Always replace ALL placeholders** before sending. A draft with
   `{sender_first_name}` still in it is worse than no template.
2. **Drop irrelevant sections.** If a template has an "agenda" subsection
   but the meeting is informal, cut it.
3. **Add specifics.** Templates give structure; the writer adds the email's
   actual content (the customer's actual issue, the actual proposed time).
4. **Match the recipient's language.** If the inbound email is in 中文,
   translate the template body to 中文 before adapting.
5. **Never include the template's section headers** in the final reply
   (e.g. `# meeting-accept` is metadata, not output).

## Template variables (across all templates)

- `{sender_first_name}` — first name from the sender's display name
- `{topic}` — short noun phrase summarizing the original ask
- `{previous_date}` — when the user previously responded (for follow-ups)

Template-specific variables are documented inside each template file.

## Available templates

See `templates/`:

- `meeting-accept.md` — confirm attendance, ask for agenda
- `meeting-decline.md` — politely decline, propose alternatives
- `polite-followup.md` — nudge after silence, no guilt-tripping
- `customer-apology.md` — outage / issue acknowledgment + remediation
