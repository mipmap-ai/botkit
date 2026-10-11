# AGENTS.md

Instructions for coding agents and bots working in this repo or using it.

A Grok Bot is a long-running AI agent with its own computer; its profile is its whole persona. Jev is a scoring API used for yes/no judgments.

## Always generate with botkit

- Profiles and skills come from `python3 botkit.py profile|skill|jev-skill`. Never write them freehand. Those three commands are all botkit does; installing is the steps below.
- Never hand-edit generated output: `examples/profiles/*.md`, `tests/golden/*.md`, or a profile on a live bot. Change the JSON input (or the flags), then regenerate.
- JSON keys are plural field names (`responsibilities`); flags are singular (`--responsibility`), repeated per item.
- After changing `botkit.py` or any `*.json` input under `examples/profiles/` or `tests/golden/`, run `python3 scripts/regen.py` and commit the results. CI fails on stale output.
- Keep `templates/*.md` in step with `botkit.py`; a test compares their section headers.
- Hand-written files: `botkit.py`, `templates/`, `skills/`, `routines/`, `examples/safety/`, docs, tests.

## Installing botkit on a bot computer

A bot doesn't read skills from any folder. It only knows a skill once it saves it through its own skill tool; in Grok Bot that's the `UpdateSkill` tool with action `write` and the full `SKILL.md` content. Copying skill files onto the computer does nothing.

`ROOT` is the bot computer's private workspace folder (on a Grok Bot computer, usually `/workspace`). Everything private lives in `ROOT`, outside the clone:

```text
ROOT/
  botkit/              clone of this repo; public, never holds private data
  fleet.json           your fleet: one line per bot
  bots/<name>.json     each bot's profile fields (input)
  bots/<name>.md       each bot's generated profile (output)
  safety/              your safety check programs (optional)
  references/          reference files plus INDEX.md (optional)
```

Follow these steps in order. Do each one yourself; ask the owner only where a step says to.

1. **Get the repo.** If `ROOT/botkit` is already a git checkout of botkit, run `git -C ROOT/botkit pull --ff-only`. Otherwise run `git clone <botkit repo URL> ROOT/botkit`. Check that `python3 --version` is 3.10 or newer.
2. **Save the shared skills.** For each `ROOT/botkit/skills/<folder>/SKILL.md`, in name order:
   1. Read the file's exact content. The skill's name is `<folder>`; it also matches the `name:` in its frontmatter.
   2. Read your existing skill of that name through your skill tool, if one exists.
   3. If it exists with identical content, skip it and note `skip <folder> (same)`.
   4. If it doesn't exist, save it through your skill tool under the name `<folder>` with the full file content (Grok Bot: `UpdateSkill`, action `write`), then note `saved <folder>`.
   5. If it exists with different content, leave it as it is and note `differs <folder>`. Tell the owner and overwrite only on their yes; updates are handled in the update steps below.
3. **Create the fleet file.** If `ROOT/fleet.json` doesn't exist, copy `ROOT/botkit/examples/fleet.example.json` to it. If it exists, leave it untouched. Then, with the owner, replace the three sample bots with the real ones.
4. **Create the bots folder.** Make `ROOT/bots/` if it's missing. Each bot's input lives at `ROOT/bots/<name>.json`, next to `fleet.json`.
5. **Safety check (optional, only for bots with risky actions).** Make `ROOT/safety/` if it's missing. Copy `ROOT/botkit/examples/safety/inbound-check` and `inbound-check.json` into it only if they're missing, and keep `inbound-check` executable. Adapt `inbound-check.json` (allow list, block list, risky words) with the owner, then test an allow, a needs-human and an ignore case before any profile points at it.
6. **References (optional).** Make `ROOT/references/` and an `INDEX.md` there if they're missing; one line per file: `file: what it is / when to read it`.
7. **Profiles.** For each bot, design it with the design-a-grok-bot skill (saved in step 2) and keep its fields in `ROOT/bots/<name>.json`. Generate its profile:

   ```text
   python3 ROOT/botkit/botkit.py profile --json ROOT/bots/<name>.json -o ROOT/bots/<name>.md
   ```

   Paste the `.md` output, exactly and in full, into the bot's profile; it's the only text that goes in. Read the live profile back and compare it with the file. Add or update the bot's line in `ROOT/fleet.json`: key is the lowercase name with no spaces, value is `"<name>: <purpose in one line>"`.

Rules:

- Never put real fleet data, bot names, owner names or private paths in the repo. Don't write anything inside `ROOT/botkit` and don't commit from it on a bot computer.
- Re-running steps 1 to 7 is safe: existing files, folders and identical skills are skipped, and regenerating a profile from unchanged input produces the same bytes.

To update botkit:

1. Note the current commit: `OLD=$(git -C ROOT/botkit rev-parse HEAD)`.
2. Run `git -C ROOT/botkit pull --ff-only`.
3. List the skills that changed: `git -C ROOT/botkit diff --name-only "$OLD" HEAD -- skills/`.
4. Re-save only those skills through your skill tool, each under its folder name with the new full content. Leave every other skill alone.
5. If `botkit.py` changed, regenerate each profile as in step 7. Paste a profile again only if its `.md` changed.

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

Print exactly one of `ALLOW`, `NEEDS_HUMAN`, `IGNORE` on stdout, reasons on stderr, exit 0; the only exception is `--help` on its own, which prints usage text. Normalize text before matching phrases (NFKC, casefold, collapse whitespace, strip zero-width characters, fold look-alike letters). Fail closed to `NEEDS_HUMAN` on bad input or any error. Decide with deterministic code first, Jev for gray areas, model judgment last. Test allow, needs-human and ignore cases before a profile points at it.
