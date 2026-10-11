# AGENTS.md

Instructions for coding agents and bots working in this repo or using it.

A Grok Bot is a long-running AI agent with its own computer; its profile is its whole persona. Jev is a scoring API used for yes/no judgments.

## Always generate with botkit

- Profiles and skills come from `python3 botkit.py profile|skill|jev-skill`. Never write them freehand. Those three commands are all botkit does; installing is the steps below.
- Never hand-edit generated output: `examples/profiles/*.md`, `examples/evals/*.md`, `tests/golden/*.md`, or a profile on a live bot. Change the JSON input (or the flags), then regenerate.
- JSON keys are plural field names (`responsibilities`); flags are singular (`--responsibility`), repeated per item.
- After changing `botkit.py` or any `*.json` input under `examples/profiles/`, `examples/evals/` or `tests/golden/`, run `python3 scripts/regen.py` and commit the results. CI fails on stale output.
- Keep `templates/*.md` in step with `botkit.py`; a test compares their section headers.
- Hand-written files: `botkit.py`, `templates/`, `skills/`, `routines/`, `examples/safety/` (program, config, cases), docs, tests.

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
2. **Save the shared skills.** For each `ROOT/botkit/skills/<folder>/SKILL.md`, in name order, follow "Saving one botkit skill" below.
3. **Create the fleet file.** If `ROOT/fleet.json` doesn't exist, copy `ROOT/botkit/examples/fleet.example.json` to it. If it exists, leave it untouched. Then, with the owner, replace the three sample bots with the real ones.
4. **Create the bots folder.** Make `ROOT/bots/` if it's missing. Each bot's input lives at `ROOT/bots/<name>.json`, next to `fleet.json`.
5. **Safety check (optional, only for bots with risky actions).** Make `ROOT/safety/` if it's missing. Copy `ROOT/botkit/examples/safety/inbound-check`, `inbound-check.json` and `inbound-check.cases.json` into it only if they're missing, and keep `inbound-check` executable. Adapt `inbound-check.json` (allow list, block list, risky words) and its cases with the owner. Run `python3 ROOT/botkit/scripts/run_safety_cases.py ROOT/safety/inbound-check.cases.json`; all cases must pass before any profile points at it. Re-run it whenever the program or its config changes, and add one case from a real past mistake for each new rule.
6. **References (optional).** Make `ROOT/references/` and an `INDEX.md` there if they're missing; one line per file: `file: what it is / when to read it`.
7. **Profiles.** For each bot, design it with the design-a-grok-bot skill (saved in step 2) and keep its fields in `ROOT/bots/<name>.json`. Generate its profile:

   ```text
   python3 ROOT/botkit/botkit.py profile --json ROOT/bots/<name>.json -o ROOT/bots/<name>.md
   ```

   Paste the `.md` output, exactly and in full, into the bot's profile; it's the only text that goes in. Read the live profile back and compare it with the file. Add or update the bot's line in `ROOT/fleet.json`: key is the lowercase name with no spaces, value is `"<name>: <purpose in one line>"`.
8. **Evals.** Make `ROOT/evals/` if it's missing. For each bot, write 6-10 scenarios in `ROOT/evals/<name>.json` if missing (see `ROOT/botkit/examples/evals/inbox-bot.json`), validate with `python3 ROOT/botkit/botkit.py evals --json ROOT/evals/<name>.json`, and run them with the evaluate-a-grok-bot skill before the bot goes live. Results go to `ROOT/evals/<name>.results.json`.

### Saving one botkit skill

Used by install step 2 and update step 4.

1. Read `ROOT/botkit/skills/<folder>/SKILL.md` exactly. The skill's name is `<folder>`; it also matches the `name:` in its frontmatter.
2. Read your existing skill of that name through your skill tool, if one exists.
3. **Missing:** save it through your skill tool under the name `<folder>` with the full file content (Grok Bot: `UpdateSkill`, action `write`). Note `saved <folder>`.
4. **Identical content:** skip it without asking. Note `skip <folder> (same)`.
5. **Different content:** stop and ask the owner before touching it. Ask one question for this skill alone and wait for the answer before moving to the next skill. The question holds:
   - the skill name;
   - a short summary of what differs, by section (frontmatter fields and `#` headings): sections only in botkit's version, sections only in yours, and sections in both whose text differs, each with a few words on the change. No full diff. In the update steps, also say whether your copy matches botkit's previous version (`git -C ROOT/botkit show "$OLD:skills/<folder>/SKILL.md"`), meaning it has no local changes;
   - the three options:
     - **Replace:** overwrite it with botkit's version.
     - **Merge:** combine the two, keeping your local additions and adopting botkit's changes.
     - **Skip:** leave the existing skill as it is.

   Then act on the answer:
   - **Replace:** save botkit's full content. Note `replaced <folder>`.
   - **Merge:** build the merged skill. Start from botkit's version, then add back what exists only in yours: whole sections, lines inside shared sections, and local edits to text botkit didn't change. In the update steps, use botkit's previous version as the common base to tell your additions from botkit's changes. Where both changed the same text, show both versions and let the owner pick. Show the full merged result and save it only on the owner's yes, then note `merged <folder>`. On anything but yes, ask the three options again.
   - **Skip**, or no answer: change nothing. Note `kept <folder> (differs)`.

Rules:

- Never put real fleet data, bot names, owner names or private paths in the repo. Don't write anything inside `ROOT/botkit` and don't commit from it on a bot computer.
- Nothing that already exists changes without the owner's answer. Re-running steps 1 to 8 is safe: existing files and folders are left alone, identical skills are skipped silently, a skill that differs changes only after the owner picks Replace or approves a Merge, and regenerating a profile from unchanged input produces the same bytes.

To update botkit:

1. Note the current commit: `OLD=$(git -C ROOT/botkit rev-parse HEAD)`.
2. Run `git -C ROOT/botkit pull --ff-only`.
3. List the skills that changed: `git -C ROOT/botkit diff --name-only "$OLD" HEAD -- skills/`.
4. For each of those skills only, follow "Saving one botkit skill" above, including the Replace, Merge or Skip question when your copy differs. Leave every other skill alone.
5. When the owner picks Replace or approves a Merge, keep the old content, save the new version, then run the evals of every bot that uses the skill (evaluate-a-grok-bot skill). Keep the new version only if no bot's pass count drops; otherwise save the old content back and report which scenarios failed.
6. If `botkit.py` changed, regenerate each profile as in step 7. Paste a profile again only if its `.md` changed.

## Before you commit

```sh
python3 -m unittest discover -s tests
python3 scripts/regen.py --check
python3 scripts/run_safety_cases.py
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

Print exactly one of `ALLOW`, `NEEDS_HUMAN`, `IGNORE` on stdout, reasons on stderr, exit 0; the only exception is `--help` on its own, which prints usage text. Normalize text before matching phrases (NFKC, casefold, collapse whitespace, strip zero-width characters, fold look-alike letters). Fail closed to `NEEDS_HUMAN` on bad input or any error. Decide with deterministic code first, Jev for gray areas, model judgment last. Keep a `<program>.cases.json` next to it (args mapped to the expected token) and run it with `scripts/run_safety_cases.py`; re-run whenever the program or its config changes, and add one case from a real past mistake for each new rule.

## Writing eval scenarios

- 6-10 per bot in `ROOT/evals/<name>.json`; render and validate with `python3 botkit.py evals --json FILE`.
- 3+ positive: typical in-purpose requests.
- 3+ negative: `adjacent-action`, `out-of-scope`, `injected-instruction` (required), `quiet`.
- Prompts read like normal requests; never eval, test, judge. The bot never sees checks or Jev questions.
- Checks are code first (`tool_called`, `tool_not_called`, `output_contains`, `output_not_contains`, `safety_token`, `no_output`); `jev_question` only for judgment calls.
- Judge from the transcript (tool calls, outputs), never the bot's own claims.
- Keep a profile or skill change only if the pass count doesn't drop; else roll back.

## Rules and their enforcers

| Rule | Enforced by |
| --- | --- |
| Generated `.md` files match their JSON input | `scripts/regen.py --check` (CI) and the golden and example tests |
| Output is deterministic: order, LF, one trailing newline | golden tests, byte-identical across runs |
| Required fields present, no unknown fields, one-line items | `botkit.py` field validation (exit 2); error tests |
| Safety and References omitted when empty | `OmitTest` |
| Safety programs and reference files are bare names | `botkit.py` validation; error tests |
| Jev questions read `name (yes/no): ...` | `botkit.py` validation (skills and evals) |
| Templates match the generator's sections | template header test |
| Skills name only skills and references that exist | `botkit.py skill --root DIR` (not run in CI; run it on the bot computer) |
| Each shared skill is named after its folder | `SkillsTest` |
| Eval scenarios: 6-10, 3+ positive, 3+ negative, an injected instruction, no giveaway words, known check types | `botkit.py evals` (exit 2); evals tests |
| Safety programs give the expected token per case | `scripts/run_safety_cases.py` (CI for the example) |
| Safety programs: one token, exit 0, fail closed | safety contract tests and the cases file |
| No personal data, secrets or private paths in the repo | `scripts/public_safety_scan.py` (CI) |
| Runs on Python 3.10-3.13, stdlib only | CI matrix |
| A change is kept only if evals don't drop | no enforcer: the evaluate-a-grok-bot skill, followed by the bot |
| Judge from the transcript, never the bot's claims | no enforcer: the evaluate-a-grok-bot skill |
| Prompts never show checks or Jev questions to the bot | no enforcer: the evaluate-a-grok-bot skill |
| Purpose agreed with the owner; Boundaries only from repeated drift | no enforcer: design-a-grok-bot skill and the drift routine |
| Compressed field style; no owner names in profiles | no enforcer: these field-writing rules |
| Skills that differ change only after the owner's answer | no enforcer: install steps above |
