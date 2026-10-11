# AGENTS.md

Instructions for coding agents and bots working in this repo or using it.

A Grok Bot is a long-running AI agent with its own computer; its profile is its whole persona. Jev is a scoring API used for yes/no judgments.

## Always generate with botkit

- Profiles and skills come from `python3 botkit.py profile|skill|jev-skill`. Never write them freehand.
- Never hand-edit generated output: `examples/profiles/*.md`, `tests/golden/*.md`, or a profile on a live bot. Change the JSON input (or the flags), then regenerate.
- JSON keys are plural field names (`responsibilities`); flags are singular (`--responsibility`), repeated per item.

## Adding a bot on a bot computer

- Follow the design-a-grok-bot skill (`skills/design-a-grok-bot/SKILL.md`; installed to `ROOT/.cursor/skills/`) for intake, Purpose, Boundaries and the safety check.
- Keep the bot's input in `ROOT/bots/<name>.json`, next to `ROOT/fleet.json`. Generate with `python3 botkit.py profile --json ROOT/bots/<name>.json -o ROOT/bots/<name>.md`; the `.md` is the only text that goes into the bot.
- Add the bot to `ROOT/fleet.json`: key is the lowercase name with no spaces, value is `"<name>: <purpose in one line>"`. Update the line whenever Purpose changes.
- After changing `botkit.py` or any `*.json` input under `examples/profiles/` or `tests/golden/`, run `python3 scripts/regen.py` and commit the results. CI fails on stale output.
- Keep `templates/` in step with `botkit.py`; a test compares their section headers.
- Hand-written files: `botkit.py`, `skills/`, `routines/`, `examples/safety/`, docs, tests.

## Before you commit

```sh
python3 -m unittest discover -s tests
python3 scripts/regen.py --check
python3 scripts/public_safety_scan.py
```

This repo is public. No real names, emails, phone numbers, account IDs, org or repo names other than botkit, hostnames, avatar sites or personal paths. Use neutral placeholders (`owner`, `inbox-bot`, `ROOT`).

## Writing profile fields

The reader is a model, not a person. Every field is a dash list, even with one item.

- Compressed, not grammatical. Drop filler, articles and connectors when meaning survives; semicolons and commas over "and".
- Never name the owner or write "help the user"; every bot works for its owner.
- Short names over full ones when unambiguous.
- **Purpose**: the real reason the bot exists, as the owner states it; not a capability list. One line per part if there's more than one. Agree it with the owner before writing anything else. Use precise verbs: "determine how X transfers to Y" for analysis, not "apply".
- **Responsibilities**: outcomes the bot owns, true regardless of timing. Schedules and steps belong in routines, never here. Every routine serves one of these lines.
- **Boundaries**: start from zero. Write one only for an edge the purpose leaves ambiguous, or to name the adjacent verb the bot never does (a drafter doesn't send). Add more only from repeated drift across days and conversations; prefer rewriting Purpose. Drift on many bots at once means a model change, so don't edit profiles for it.
- **Safety**: only if the bot has risky actions. `<program> [parameters]`, program is a bare name in `ROOT/safety/`, `{placeholders}` for values from the action. Action rules (send, delete, buy, paths, numbers) live in that program, never in prose.
- **References**: only if the bot needs fixed reference material. Bare file names in `ROOT/references/`, each with one line in `INDEX.md`.
- **Voice**: a few words per line.
- One purpose per bot. No wake lists, handoff lists, tool essays or "I can also help with...". Every token is re-read on every wake.

## Writing skill fields

- Terse dash lists; steps only. Reference material goes in `ROOT/references/`, not in the skill.
- **Purpose**: what the skill gets done, one line.
- **Input**: what it starts from.
- **Steps**: one action each; botkit numbers them.
- **Decide**: go if / else / on failure.
- **Run**: exact commands.
- **Never**: hard limits not already enforced by a Safety program.
- Jev skills add **Questions** as `name (yes/no): what a yes means` or `name (pick-one: a/b/c): ...`, matching the questions file passed to Jev. Decide lists exact code checks first (dedupe against a state file, sender allowlists, dates are code, not Jev questions), then score thresholds, then what to do when Jev is down (exit 2).

## Safety check programs

Print exactly one of `ALLOW`, `NEEDS_HUMAN`, `IGNORE` on stdout, reasons on stderr, exit 0; the only exception is `--help` on its own, which prints usage text. Normalize text before matching phrases (NFKC, casefold, collapse whitespace). Fail closed to `NEEDS_HUMAN` on bad input or any error. Decide with deterministic code first, Jev for gray areas, model judgment last. Test allow, needs-human and ignore cases before a profile points at it.
