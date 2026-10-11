---
name: design-a-grok-bot
description: >-
  Use when designing or creating a new Grok Bot. Agree its purpose, generate
  the profile with botkit in the standard
  Purpose/Responsibilities/Boundaries/Safety/References/Voice format, write
  its safety check if it has risky actions, create it, add it to fleet.json,
  then verify against the live profile.
---
# Design a Grok Bot

Create the bot. Don't produce a shareable template unless asked for one.

`ROOT` is the bot computer's private workspace folder, laid out as in botkit's AGENTS.md install steps: the botkit clone at `ROOT/botkit`, private data (`fleet.json`, `bots/`, `safety/`, `references/`) beside it, never inside the clone.

## Profile format

Every bot's description is these labeled fields, in this order, as plain text (not JSON). Keep the fields in `ROOT/bots/<name>.json` and generate the profile with `python3 ROOT/botkit/botkit.py profile --json ROOT/bots/<name>.json -o ROOT/bots/<name>.md`; never write or edit the profile by hand. The `.md` is the only text that goes into the bot.

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

Every field is a dash list, even with one item: consistent for the model, easy for scripts (drift monitors, fleet checks) to parse. Safety and References are left out entirely when empty.

### Responsibilities vs routines

- Responsibility: an outcome the bot owns, true regardless of timing ("keep shared notes current").
- Routine: a scheduled way of doing part of that work. Schedule and steps live in the routine prompt, never in the profile.
- Every routine serves a listed responsibility. A routine that doesn't is cut, or the responsibility is missing.

### Writing the lines (the reader is a model, not a person)

- Compressed, not grammatical. Drop filler words, articles and connectors when meaning survives. Prefer semicolons and commas to "and".
- Never name the owner or write "help the user": every bot works for its owner; that's implied.
- Short names over full ones when unambiguous.
- Purpose is the real reason the bot exists, as the owner states it. Ask "why do you want it?" before writing. Not a capability brag.
- Precise verbs that match intent: "determine how X transfers to Y" when the job is analysis, not "apply" (which implies editing).
- Draft Purpose first and agree it with the owner before writing the other fields.

Example:

```
Purpose:
- teach a framework's core techniques
- determine how they transfer to an existing mobile codebase
```

Single responsibility: one reason to exist. No wake list, no handoff list (bots route through the router), no tool essays, no "I can also help with...". The profile is re-read on every wake and every token costs; reference material goes in a skill or a reference file read only when needed.

The create call takes a name and a description; that description is the whole persona. After create, read the live profile back from the platform and compare it with the generated text. Don't trust the tool's acknowledgement alone.

If there is no delete tool, only create when the job is real.

## Boundaries

- Start with zero. Purpose does the scoping.
- Exception: one line for an edge the purpose itself makes ambiguous (a bot for one framework, next to the general language it's written in).
- Non-coding bots name the adjacent verb they never do (a mentions scout does not post; a drafter does not send).
- Add a line only from evidence: the same drift on several days and conversations, never one slip.
- First ask whether a purpose rewrite fixes it; prefer that to a new line.
- A line stays only if drift on post-edit conversations beats the purpose-only baseline; otherwise roll back.
- No fixed cap; every line earns its place on new data.
- Drift on many bots at once likely means a model change; don't edit profiles for it.
- Action rules (send, delete, buy, paths, numbers) never live in prose. They go in the Safety program.

## References (only if the bot needs fixed reference material)

Reference docs (specs, lookup tables, research) are files in `ROOT/references/`, never in the profile and never a skill. List only file names on the References field. Add or update the file's one-line entry in `ROOT/references/INDEX.md` (`file: what it is / when to read it`). The shared bot-references skill tells bots how to use them; don't repeat it in profiles. Several bots can list the same file; its description lives only in the index.

## Safety check (only if the bot has risky actions)

The shared bot-safety-check skill tells every bot to run its Safety program before risky actions and obey the result. Don't repeat that rule in the profile.

Write or pick a check program in `ROOT/safety/` and reference it by bare name plus parameters, with `{placeholders}` for values filled from the action:

```
Safety:
- inbound-check --from {sender} --text {message}
```

Bots may share a program; strictness fits the bot. It prints exactly one of `ALLOW`, `NEEDS_HUMAN`, `IGNORE`, writes reasons to stderr, and fails closed to `NEEDS_HUMAN`. Build it at the lowest level that works:

1. Deterministic code: allowlists, action types, sender rules.
2. Jev for gray areas code can't decide: shell out to the shared `jev` command or import the shared `jev` module. Never call the model API directly.
3. Model judgment only as a last resort.

Test it with a few allow, needs-human and ignore cases before pointing a profile at it. `ROOT/botkit/examples/safety/inbound-check` is a starting point; copy it into `ROOT/safety/` rather than running it from the clone.

## Skill format

Generate skills with `python3 ROOT/botkit/botkit.py skill` (or `jev-skill`). A bot knows a skill only once it saves it through its own skill tool (Grok Bot: `UpdateSkill`, action `write`, with the full content); a file on disk does nothing. Dash lists, terse, model-oriented, steps only; reference material goes to `ROOT/references/`. Only the sections that apply:

```
Purpose:
- what the skill gets done, in one line

Input:
- what it starts from

Steps:
- 1. ...

Decide:
- go if / else / on failure

Run:
- exact commands

Never:
- hard limits not already enforced by a Safety program
```

Skills that call Jev also list `Questions:` (`name (yes/no or pick-one): what a yes means`), and Decide holds the score thresholds plus what to do when Jev is down (exit 2). Anything code can decide exactly (dedupe against a state file, sender allowlist, dates) is a code check in Decide, not a Jev question. The questions file the skill passes to Jev must match the Questions list.

## Intake

Ask only preference questions no experiment can settle. Skip any already answered:

- the purpose
- voice and name, if they care
- standing routine or on-demand
- who it talks to (the owner, other bots, an outside channel)

Don't ask for tools, plugins or model if a working sibling bot can be copied. Don't ask "should I create it?" once the job is clear. Create it. Pick reversible details (a color, a nickname) yourself and say what you picked.

## Coding bots

Hold them to the team's coding playbook: one purpose, plain prose, verified work. Responsibilities and Boundaries say: repo work goes to cloud coding agents; work on files that live on the bot computer stays there; short plain replies. Don't paste the playbook into the profile.

Sizing: a job too big for one agent (parallel work, several components, a full feature) runs as several agents with a verifier on every PR before merge. A small single-file job gets one agent. This rule lives in shared memory and here, not in each profile.

## Non-coding bots

Same tightness. Purpose names the only job. Responsibilities give the concrete how (which API, inbox, channel). Boundaries name the adjacent verb it never does. Stay quiet when there is nothing to report.

## After create

1. Read the live profile back. Tell the owner the name and the Purpose lines.
2. Add the bot to `ROOT/fleet.json`: key is the lowercase name with no spaces, value is `"<name>: <purpose in one line>"`. Run the fleet check if there is one, and one test route with a typical ask to confirm the router picks the new bot. When a bot's purpose changes, update its line too.
3. If the job needs a standing routine, review its cost first. You can't write another bot's routines: message the new bot with the exact routine name, prompt, and schedule or trigger, and tell it to create the routine. Confirm to the owner that you sent it. If sending fails, say so and give the owner the one-line instruction to paste into that bot. `ROOT/botkit/routines/` has copyable prompts.
