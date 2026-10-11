---
name: cost-review
description: "Use before creating or changing a routine, or when reviewing a skill or profile for token cost."
---
# Cost review

Report findings and fixes; change nothing until the owner picks.

## Rule: cheapest tier that can decide

Cost per check: code is free, Jev costs almost nothing, a model wake is expensive. Use the cheapest tier that can decide correctly.

- Code: exact rules, same input gives same output. e.g. "any new mail since last run?", "is this sender on the allowlist?"
- Jev: needs judgment but is yes/no or pick-one. e.g. "is this message about billing?", "does this need the owner?"
- Model: open-ended reasoning or writing. e.g. writing a daily digest, planning a multi-step task

Stack them: code filters first, Jev judges what's left, the model wakes only for what survives. Flag any check running on a pricier tier than it needs.

Jev is the cheap scoring API (yes/no and pick-one, with a confidence score), called through the shared `jev` command.

## Routine (review your own, before creating or changing it)

- frequency: denser than needed? use the coarsest useful schedule
- empty wakes: can code or Jev check "anything new?" first, so the model only wakes on a hit
- quiet rule: says to stay silent when nothing changed
- serves a responsibility in the bot's profile; otherwise don't create it
- duplicate: same job already done by another routine or bot

## Skill

- summary line: trigger only; every bot pays for it every turn
- body: steps only; reference material goes to `ROOT/references/`
- overlap with another skill

## Profile

- word count; standard format, dash lists
- no routines, schedules, routing, or default model behavior
- shared rules live in skills, not repeated per bot

## Report

One line per finding: target, issue, fix, rough savings (runs per day or words cut).
