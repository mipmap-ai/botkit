---
name: design-a-grok-bot
description: >-
  Use when designing or creating a new Grok Bot. Agree its purpose, generate
  the profile with botkit in the standard
  Purpose/Responsibilities/Boundaries/Safety/References/Voice format, write
  its safety check if it has risky actions, create it, add it to the fleet
  file, then verify against the live profile.
---
# Design a Grok Bot

Create the bot. Don't produce a shareable template unless asked for one.

`ROOT` is the private workspace folder on the bot computer, laid out as in botkit's AGENTS.md install steps: the clone at `ROOT/botkit`, private data (`bots/`, `safety/`, `references/`, `avatars/`, the fleet file) beside it, never inside the clone. The fleet file is `ROOT/fleet.json` unless `BOTKIT_FLEET` (or `botkit.py profile --fleet PATH`) names another. Every bot shares `ROOT`, so a new bot uses the same `safety/` and `references/`. On Grok Bot skills are global, one library for all the owner's bots, so it already has the shared skills; only with per-bot skill stores must they be handed over.

## Profile format

Keep the fields in `ROOT/bots/<name>.json`. Add its fleet-file line first (key: lowercase name, no spaces; value: `"<name>: <purpose in one line>"`), then generate with `python3 ROOT/botkit/botkit.py profile --json ROOT/bots/<name>.json -o ROOT/bots/<name>.md`. Never write or edit the profile by hand; the `.md` is the only text that goes into the bot.

```
Purpose:
- the real reason it exists; one line per part if it has more than one

Responsibilities:
- concrete outcomes it owns

Boundaries:
- only edges the purpose leaves ambiguous

Safety:
- <program> [parameters]

References:
- file.md

Voice:
- a few words per line
```

Every field is a dash list, even with one item, one blank line between fields. Boundaries, Safety and References are optional and left out when empty. Check its token cost with `skills/cost-review`.

- Responsibility: an outcome the bot owns, true regardless of timing ("keep shared notes current"). Routine: a scheduled way of doing part of it; schedule and steps live in the routine prompt, never the profile. Every routine serves a listed responsibility, or it's cut.
- The reader is a model: compressed, not grammatical; drop filler, articles, connectors; semicolons and commas over "and"; short names when unambiguous.
- Never name the owner or write "help the user"; every bot works for its owner.
- Purpose: the real reason it exists, as the owner states it ("why do you want it?"), not a capability brag. Precise verbs: "determine how X transfers to Y" for analysis, not "apply". Agree it with the owner before writing the other fields.
- One reason to exist. No wake list, no handoff list (bots route through the router), no tool essays, no "I can also help with...". Every token is re-read on every wake; reference material goes in a reference file.

Example:

```
Purpose:
- teach a framework's core techniques
- determine how they transfer to an existing mobile codebase
```

The create call takes a name and a description; that description is the whole persona. If there is no delete tool, only create when the job is real.

## Boundaries

- Start with zero; Purpose does the scoping.
- Exception: one line for an edge the purpose makes ambiguous (a bot for one framework, next to the language it's written in), or the adjacent verb a non-coding bot never does (a scout doesn't post; a drafter doesn't send).
- Add a line only from the same drift on several days and conversations, never one slip; first try a purpose rewrite.
- A line stays only if drift on post-edit conversations beats the purpose-only baseline and evals don't drop; else roll back.
- Drift on many bots at once likely means a model change; don't edit profiles for it.
- Action rules (send, delete, buy, paths, numbers) go in the Safety program, never in prose.

## References (only if the bot needs fixed reference material)

Reference docs (specs, lookup tables, research) are files in `ROOT/references/`, never in the profile or a skill. List only file names on the References field, each with one line in `ROOT/references/INDEX.md` (`file: what it is / when to read it`). The shared bot-references skill tells bots how to use them; don't repeat it in profiles.

## Safety check (only if the bot has risky actions)

The shared bot-safety-check skill tells a bot to run its Safety program before risky actions and obey the result; don't repeat that in the profile. Write or pick a program in `ROOT/safety/` and reference it by bare name plus parameters, `{placeholders}` filled from the action:

```
Safety:
- inbound-check --from {sender} --text {message}
```

Bots may share a program; strictness fits the bot. It prints exactly one of `ALLOW`, `NEEDS_HUMAN`, `IGNORE`, reasons on stderr, and fails closed to `NEEDS_HUMAN`. Build it at the lowest level that works: deterministic code (allowlists, action types, sender rules), then Jev for gray areas (the shared `jev` command or module; never the model API directly), model judgment last.

Give it safety tests in either form: a cases file `ROOT/safety/<program>.cases.json` run by `python3 ROOT/botkit/scripts/run_safety_cases.py ROOT/safety/<program>.cases.json`, or an existing unittest suite in `ROOT/safety/tests/` run by `python3 -m unittest discover -s ROOT/safety/tests`. All must pass before a profile points at it; re-run on any program or config change. Each new rule adds one case from a real past mistake, in whichever form the program uses. Start from a copy of `ROOT/botkit/examples/safety/inbound-check` and `inbound-check.cases.json` in `ROOT/safety/`.

## Skill format

Generate skills with `python3 ROOT/botkit/botkit.py skill` (or `jev-skill`) and save them as in "Saving one botkit skill" in `ROOT/botkit/AGENTS.md`; a file on disk does nothing. Check its token cost with `skills/cost-review`. Terse dash lists, steps only; reference material goes to `ROOT/references/`. Name another skill by path (`skills/<name>`) and generate with `--root ROOT` so a missing one fails. Sections, only those that apply: Purpose (one line), Input, Steps, Decide (go if / else / on failure), Run (exact commands), Never (hard limits not in a Safety program).

Jev skills add `Questions:` (`name (yes/no or pick-one): what a yes means`, matching the questions file passed to Jev); Decide lists exact code checks first (dedupe, allowlists, dates), then score thresholds, then what to do when Jev is down (exit 2).

## Intake

Ask only preference questions no experiment can settle, skipping any already answered: the purpose; voice and name, if they care; standing routine or on-demand; who it talks to (the owner, other bots, an outside channel). Don't ask for tools, plugins or model if a working sibling bot can be copied. Don't ask "should I create it?" once the job is clear. Pick reversible details (a color, a nickname) yourself and say what you picked.

## Coding bots

The bar is pstack. Read pstack's poteto-mode when writing the profile: one purpose, unslopped prose, verified work.

- Responsibilities and Boundaries say: repo work goes to Cursor cloud agents (pstack's skills launch them); work on files that live on the bot computer stays there; replies short and unslopped; pstack and poteto-mode are situational, not standing.
- Never paste the pstack playbook into a profile.
- Sizing: a small single-file job gets one cloud agent and no pstack; a full feature uses pstack's Feature playbook; parallel work across several components uses swarm; multi-day work uses Orchestrate. Every multi-agent run has a verifier on every PR before merge.

## Non-coding bots

- Purpose names the only job; Responsibilities give the concrete how (which API, inbox, channel); Boundaries name the adjacent verb it never does; stay quiet when there's nothing to report.

## Avatar (every new bot)

Right after create, without asking, follow `skills/create-avatar/SKILL.md` for the new bot. It ends with `ROOT/avatars/<bot-name>.png` (2048 PNG), its share link in `ROOT/avatars/<bot-name>.url`, and the new bot setting the picture with `UpdateAvatar`.

- Show the owner the image in the create message; regenerate with `skills/create-avatar/SKILL.md` if they dislike it, passing any picks they name.
- Optional, only with the owner present to pick a photo: photo match in the desktop browser on https://botbuilder.mipmap.ai/ (`open_photo_match` opens a file picker, then `match_selected_photo`, poll `get_photo_match_status`, read `get_current_bot`); pass its selections as picks to `skills/create-avatar/SKILL.md`.

## After create

1. Read the live profile back and compare it with the generated `.md`; don't trust the tool's acknowledgement. Tell the owner the name and the Purpose lines.
2. Make and hand over its avatar as in "Avatar (every new bot)" (`skills/create-avatar/SKILL.md`); show it in the same message.
3. Skip this step when skills are shared across bots (Grok Bot default). Only with per-bot skill stores, hand the new bot the shared skills the "Handing skills to other bots" list in `ROOT/botkit/AGENTS.md` gives it: bot-safety-check if its profile has `Safety:`, bot-references if it has `References:`, cost-review if it will create or change its own routines. Without them it ignores those lines. Follow that section to send them and confirm the replies to the owner.
4. Write 6-30 scenarios (start near 10) in `ROOT/evals/<name>.json` and run them with the evaluate-a-grok-bot skill before the bot goes live; re-run after every profile or skill change.
5. Check its fleet-file line (added before generating): run the fleet check if there is one, and one test route with a typical ask to confirm the router picks the new bot. When its purpose changes, update the line too.
6. If the job needs a standing routine, run the cost-review skill (`skills/cost-review`) on it before creating it. Only the new bot can create its routines: message it the exact routine name, prompt, and schedule or trigger, and confirm to the owner. If sending fails, say so and give the owner the one-line instruction to paste into that bot. `ROOT/botkit/routines/` has copyable prompts.
