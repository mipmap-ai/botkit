# AGENTS.md

Instructions for coding agents and bots working in this repo or using it.

A Grok Bot is a long-running AI agent; its profile is its whole persona. All of an owner's Grok Bots share one bot computer; only desktops are per-bot. Jev is a scoring API used for yes/no judgments.

## Always generate with botkit

- Profiles, skills and eval scenarios come from `python3 botkit.py profile|skill|jev-skill|evals`. Never write them freehand. Those four commands are all botkit does; installing is the steps below.
- Never hand-edit generated output: `examples/profiles/*.md`, `examples/evals/*.md`, `tests/golden/*.md`, or a profile on a live bot. Change the JSON input (or the flags), then regenerate.
- JSON keys are plural field names (`responsibilities`); flags are singular (`--responsibility`), repeated per item.
- After changing `botkit.py` or any `*.json` input under `examples/profiles/`, `examples/evals/` or `tests/golden/`, run `python3 scripts/regen.py` and commit the results. CI fails on stale output.
- Keep `templates/*.md` in step with `botkit.py`; a test compares their section headers.
- Hand-written files: `botkit.py`, `templates/`, `skills/`, `routines/`, `examples/safety/` (program, config, cases), docs, tests.

## Installing botkit on a bot computer

A bot doesn't read skills from any folder. It only knows a skill once it is saved through a skill tool; in Grok Bot that's the `UpdateSkill` tool with action `write` and the full `SKILL.md` content. Copying skill files onto the computer does nothing. On Grok Bot, skills are global: one library shared by all of the owner's bots, so a skill saved once is known to every bot. Only a setup where each bot has its own skill store needs skills handed to each bot. To tell which you have: on Grok Bot, skills are shared; on anything else, ask the owner.

`ROOT` is the private workspace folder on the bot computer (usually `/workspace`). Every bot in the fleet shares that computer, so there is one `ROOT`: install once, and every bot runs the same `ROOT/safety/` programs and reads the same `ROOT/references/` files. Everything private lives in `ROOT`, outside the clone:

```text
ROOT/
  botkit/              clone of this repo; public, never holds private data
  fleet.json           your fleet: one line per bot (or set its path, see below)
  bots/<name>.json     each bot's profile fields (input)
  bots/<name>.md       each bot's generated profile (output)
  safety/              your safety check programs (optional)
  safety/tests/        unittest suite for them (optional, instead of cases files)
  references/          reference files plus INDEX.md (optional)
  avatars/<name>.png   each bot's picture (design-a-grok-bot)
```

The fleet file is `ROOT/fleet.json` unless `BOTKIT_FLEET` names another path; `botkit.py profile --fleet PATH` overrides both. Below, "the fleet file" means that path. `profile` checks it: every value a string, and a warning if the bot of `--json ROOT/bots/<name>.json` has no `<name>` line. A missing, malformed or directory path from `--fleet` or `BOTKIT_FLEET` is an error; the same problem with the default `ROOT/fleet.json` (as in a dev clone) only warns and skips the check.

Follow these steps in order. Do each one yourself; ask the owner only where a step says to.

1. **Get the repo.** If `ROOT/botkit` doesn't exist, run `git clone https://github.com/mipmap-ai/botkit ROOT/botkit`. If it exists and is a botkit checkout (`git -C ROOT/botkit remote get-url origin` ends in `botkit` or `botkit.git`, and `ROOT/botkit/botkit.py` exists), run `git -C ROOT/botkit pull --ff-only`. If it exists but isn't a botkit checkout, stop: don't move, delete or overwrite it; tell the owner what's there and ask what to do. Check that `python3 --version` is 3.10 or newer.
2. **Save the shared skills.** For each `ROOT/botkit/skills/<folder>/SKILL.md`, in name order, follow "Saving one botkit skill" below. On Grok Bot this saves them for every bot; only with per-bot skill stores do other bots get theirs through "Handing skills to other bots".
3. **Create the fleet file.** If the owner already keeps a fleet file elsewhere, set `BOTKIT_FLEET` to its path and create nothing. Otherwise, if `ROOT/fleet.json` doesn't exist, copy `ROOT/botkit/examples/fleet.example.json` to it. If it exists, leave it untouched. Then, with the owner, replace the three sample bots with the real ones.
4. **Create the bots folder.** Make `ROOT/bots/` if it's missing. Each bot's input lives at `ROOT/bots/<name>.json`.
5. **Safety check (optional, only for bots with risky actions).** Make `ROOT/safety/` if it's missing. Copy `ROOT/botkit/examples/safety/inbound-check`, `inbound-check.json` and `inbound-check.cases.json` into it only if they're missing, and keep `inbound-check` executable. Adapt `inbound-check.json` (allow list, block list, risky words) and its cases with the owner. Run its safety tests as in "Safety check programs" below; all must pass before any profile points at it.
6. **References (optional).** Make `ROOT/references/` and an `INDEX.md` there if they're missing; one line per file: `file: what it is / when to read it`.
7. **Profiles.** For each bot, design it with the design-a-grok-bot skill (saved in step 2) and keep its fields in `ROOT/bots/<name>.json`. Add or update its line in the fleet file first, so generating doesn't warn: key is the lowercase name with no spaces, value is `"<name>: <purpose in one line>"`. Generate its profile:

   ```text
   python3 ROOT/botkit/botkit.py profile --json ROOT/bots/<name>.json -o ROOT/bots/<name>.md
   ```

   Paste the `.md` output, exactly and in full, into the bot's profile; it's the only text that goes in. Read the live profile back and compare it with the file. Only with per-bot skill stores, hand the bot its skills as in "Handing skills to other bots".
8. **Evals.** Make `ROOT/evals/` if it's missing. For each bot, write 6-30 scenarios in `ROOT/evals/<name>.json` if missing (see `ROOT/botkit/examples/evals/inbox-bot.json`), validate with `python3 ROOT/botkit/botkit.py evals --json ROOT/evals/<name>.json`, and run them with the evaluate-a-grok-bot skill before the bot goes live. Results go to `ROOT/evals/<name>.results.json`.

### Saving one botkit skill

Used by install step 2, update step 4, and by any bot that is handed a skill (see "Handing skills to other bots").

1. Read `ROOT/botkit/skills/<folder>/SKILL.md` exactly (or, when handed a skill, the full content in the message). The skill's name is `<folder>`; it also matches the `name:` in its frontmatter.
2. Read your existing skill of that name through your skill tool, if one exists.
3. **Missing:** save it through your skill tool under the name `<folder>` with the full file content (Grok Bot: `UpdateSkill`, action `write`). Note `saved <folder>`.
4. **Identical:** byte-for-byte equal after turning every CRLF or CR line ending into LF in both. Skip it without asking. Note `skip <folder> (same)`.
5. **Unchanged old version (update steps only):** your copy is identical, in the same sense, to botkit's previous version (`git -C ROOT/botkit show "$OLD:skills/<folder>/SKILL.md"`), so it has no local changes. Save botkit's new version without asking; the owner already chose to update. Note `updated <folder>`.
6. **Different content** (local changes, or any difference at install): stop and ask the owner before touching it. Ask one question for this skill alone and wait for the answer before moving to the next skill. The question holds:
   - the skill name;
   - a short summary of what differs, by section (frontmatter fields and `#` headings): sections only in botkit's version, sections only in yours, and sections in both whose text differs, each with a few words on the change. No full diff. In the update steps, also summarize your local changes against botkit's previous version;
   - the three options:
     - **Replace:** overwrite it with botkit's version.
     - **Merge:** combine the two, keeping your local additions and adopting botkit's changes.
     - **Skip:** leave the existing skill as it is.

   Then act on the answer:
   - **Replace:** save botkit's full content. Note `replaced <folder>`.
   - **Merge:** build the merged skill. Start from botkit's version, then add back what exists only in yours: whole sections, lines inside shared sections, and local edits to text botkit didn't change.
     - With a common base (the update steps: botkit's previous version, the `$OLD` commit), use it to tell your additions from botkit's changes. Where both changed the same text, show both versions and let the owner pick.
     - With no common base (install, or a handed skill), you can't tell additions from changes: for every section whose text differs, show both versions and let the owner pick or edit; sections only in one version are kept.
     - Show the full merged result and save it only on the owner's yes, then note `merged <folder>`. On anything but yes, ask the three options again.
   - **Skip:** change nothing. Note `kept <folder> (differs)`.
   - **No answer:** if the conversation ends or moves on without one, treat it as Skip and say so in your next message (`kept <folder> (no answer)`). Don't set timers or reminders to wait for it; re-running the steps asks again.

### Handing skills to other bots

Skip this section when skills are shared across bots, the Grok Bot default: install step 2 already gave every bot every shared skill. Only where each bot has its own skill store: you can't save a skill on another bot; only that bot can, with its own skill tool. Who needs which shared skill:

- bot-safety-check: every bot whose profile has `Safety:`.
- bot-references: every bot whose profile has `References:`.
- design-a-grok-bot, evaluate-a-grok-bot: only the bot that designs and evaluates bots (you).

To hand a skill over, message the bot with the skill name, the full `SKILL.md` content in a code block, and the instruction: save it through your skill tool under that name, following botkit's "Saving one botkit skill" (save if missing, skip if identical, ask your owner Replace, Merge or Skip if different), then reply with the note. In the update steps, also give the `$OLD` commit, so a bot whose copy matches botkit's previous version (readable from the shared `ROOT/botkit`) updates without asking. Confirm to the owner what you sent and each bot's reply. If sending fails, say so and give the owner the one-line instruction to paste into that bot.

Rules:

- Never put real fleet data, bot names, owner names or private paths in the repo. Don't write anything inside `ROOT/botkit` and don't commit from it on a bot computer.
- Nothing that already exists changes without the owner's answer, except a skill with no local changes during an update the owner asked for. Re-running steps 1 to 8 is safe: existing files and folders are left alone, identical skills are skipped silently, a skill that differs changes only after the owner picks Replace or approves a Merge, and regenerating a profile from unchanged input produces the same bytes.

To update botkit:

1. Note the current commit: `OLD=$(git -C ROOT/botkit rev-parse HEAD)`.
2. Run `git -C ROOT/botkit pull --ff-only`.
3. List the skills that changed: `git -C ROOT/botkit diff --name-status "$OLD" HEAD -- skills/`. `D` means botkit deleted the skill; anything else means it was added or changed.
4. For each added or changed skill only, follow "Saving one botkit skill" above: a copy with no local changes is updated without asking; a copy with local changes gets the Replace, Merge or Skip question. Skip the re-save on other bots when skills are shared across bots (Grok Bot default). Only with per-bot skill stores, hand it to every other bot that uses it (see "Handing skills to other bots"; check `Safety:` and `References:` in each `ROOT/bots/<name>.md`) so each re-saves it. Leave every other skill alone.
5. For each skill botkit deleted that you or another bot still has: ask the owner, one question per skill, Keep (leave it as a local skill) or Delete (remove it through your skill tool; only with per-bot skill stores, also message each other bot that has it to remove its own). No answer means Keep. Never delete without a yes.
6. Whenever a skill changes (updated without asking, Replace, or an approved Merge), keep the old content, save the new version, then run the evals of every bot that uses the skill (evaluate-a-grok-bot skill). Keep the new version only if no bot's pass count drops; otherwise save the old content back (and, with per-bot skill stores, hand it back to the other bots) and report which scenarios failed.
7. If `botkit.py` changed, regenerate each profile as in install step 7. Paste a profile again only if its `.md` changed.

## Before you commit

```sh
python3 -m unittest discover -s tests
python3 scripts/regen.py --check
python3 scripts/run_safety_cases.py
python3 scripts/public_safety_scan.py
```

This repo is public. No real names, emails, phone numbers, account IDs, org or repo names other than botkit, hostnames, avatar sites or personal paths. Use neutral placeholders (`owner`, `inbox-bot`, `ROOT`). Exceptions: botkit's own repo URL (`https://github.com/mipmap-ai/botkit`, including its org name); the public avatar site `https://botbuilder.mipmap.ai/` used by design-a-grok-bot; and third-party projects botkit adapts or builds on (pstack and its skills), named in shared skills and credited with their license in the README's Credits section.

## Writing profile fields

The reader is a model, not a person. Every field is a dash list, even with one item.

- Compressed, not grammatical. Drop filler, articles and connectors when meaning survives; semicolons and commas over "and".
- Never name the owner or write "help the user"; every bot works for its owner.
- Short names over full ones when unambiguous.
- **Purpose**: the real reason the bot exists, as the owner states it; not a capability list. One line per part if there's more than one. Agree it with the owner before writing anything else. Use precise verbs: "determine how X transfers to Y" for analysis, not "apply".
- **Responsibilities**: outcomes the bot owns, true regardless of timing. Schedules and steps belong in routines, never here. Every routine serves one of these lines.
- **Boundaries**: optional; start from zero (botkit omits the section when empty). Write one only for an edge the purpose leaves ambiguous, or to name the adjacent verb the bot never does (a drafter doesn't send). Add more only from repeated drift across days and conversations; prefer rewriting Purpose. Drift on many bots at once means a model change, so don't edit profiles for it.
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
- Name another skill by its path, `skills/<name>` (for example `follow skills/bot-references/SKILL.md`), so `--root` can check it.
- Jev skills add **Questions** as `name (yes/no): what a yes means` or `name (pick-one: a/b/c): ...`, matching the questions file passed to Jev. Decide lists exact code checks first (dedupe against a state file, sender allowlists, dates are code, not Jev questions), then score thresholds, then what to do when Jev is down (exit 2).

## Safety check programs

Print exactly one of `ALLOW`, `NEEDS_HUMAN`, `IGNORE` on stdout, reasons on stderr, exit 0; the only exception is `--help` on its own, which prints usage text. Normalize text before matching phrases (NFKC, casefold, collapse whitespace, strip zero-width characters, fold look-alike letters). Fail closed to `NEEDS_HUMAN` on bad input or any error. Decide with deterministic code first, Jev for gray areas, model judgment last. Safety tests, in either form:

- A cases file, `ROOT/safety/<program>.cases.json` (args mapped to the expected `ALLOW`, `NEEDS_HUMAN` or `IGNORE`), run by `python3 ROOT/botkit/scripts/run_safety_cases.py ROOT/safety/<program>.cases.json`.
- An existing unittest suite in `ROOT/safety/tests/`, run by `python3 -m unittest discover -s ROOT/safety/tests`. Keep it; don't convert it to a cases file.
- All must pass before a profile points at the program. Re-run whenever the program or its config changes.
- Each new rule adds one case from a real past mistake, in whichever form the program's tests use: a cases-file entry whose `why` names the mistake, or a test method whose name or docstring does.

## Writing eval scenarios

- 6-30 per bot in `ROOT/evals/<name>.json` (`botkit.py evals` rejects fewer or more); start near 10 and add one from each real failure. Render and validate with `python3 botkit.py evals --json FILE`.
- 3+ positive: typical in-purpose requests.
- 3+ negative: `adjacent-action`, `out-of-scope`, `injected-instruction` (required), `quiet`.
- Prompts and setup read like normal requests; never eval, test, judge, judgment. The bot never sees checks or Jev questions.
- The word rule is deliberately conservative: it rejects whole words anywhere in `setup`, even in realistic staged content ("a blood-test reminder"). Reword the staged content ("a blood-work reminder"); a false rejection costs a rewrite, a giveaway costs the eval.
- Checks are code first (`tool_called`, `tool_not_called`, `output_contains`, `output_not_contains`, `safety_token`, `no_output`); `jev_question` only for judgment calls.
- Judge from the transcript (tool calls, outputs), never the bot's own claims.
- Keep a profile or skill change only if the pass count doesn't drop; else roll back.

## Rules and their enforcers

| Rule | Enforced by |
| --- | --- |
| Generated `.md` files match their JSON input | `scripts/regen.py --check` (CI) and the golden and example tests |
| Output is deterministic: order, LF, one trailing newline | golden tests, byte-identical across runs |
| Exactly one blank line between sections | `scripts/regen.py` layout check; `LayoutTest` |
| Required fields present, no unknown fields, one-line items | `botkit.py` field validation (exit 2); error tests |
| Boundaries, Safety and References omitted when empty | `OmitTest` |
| Fleet file: `--fleet`, else `BOTKIT_FLEET`, else `ROOT/fleet.json` | `botkit.py profile`; `FleetTest` |
| Safety programs and reference files are bare names | `botkit.py` validation; error tests |
| Jev questions read `name (yes/no): ...` | `botkit.py` validation (skills and evals) |
| Templates match the generator's sections | template header test |
| Generated skills name only skills and references that exist | `botkit.py skill --root DIR` / `jev-skill --root DIR`, run on the bot computer (not in CI: the files live in the private `ROOT`); checks only skills generated with `--root`. Fails on a missing `skills/<name>` or `references/<file>`; an unknown "the <name> skill" is only a warning, so generated skills name skills by `skills/<name>` path |
| Shipped docs (`skills/`, `routines/`, AGENTS.md, README) name only skills and `ROOT/botkit/` files that exist in the repo | `SkillsTest` (CI); `ROOT/references/` files are private and not checked |
| Each shared skill is named after its folder | `SkillsTest` |
| Eval scenarios: 6-30, 3+ positive, 3+ negative, an injected instruction, no giveaway words in prompt or setup, known check types | `botkit.py evals` (exit 2); evals tests |
| Every bot with `Safety:` or `References:` has the matching shared skill | Grok Bot's shared skill library; with per-bot skill stores, no enforcer: "Handing skills to other bots" above |
| Safety programs give the expected token per case | `ROOT/safety/<program>.cases.json` run by `scripts/run_safety_cases.py` (CI for the example), or a unittest suite in `ROOT/safety/tests/` run by `python3 -m unittest discover -s ROOT/safety/tests` |
| Each new safety rule adds a case from a real past mistake | no enforcer: whichever test form the program uses |
| Safety programs: one token, exit 0, fail closed | safety contract tests and the cases file |
| No personal data, secrets or private paths in the repo | `scripts/public_safety_scan.py` (CI) |
| Runs on Python 3.10-3.13, stdlib only | CI matrix |
| A change is kept only if evals don't drop | no enforcer: the evaluate-a-grok-bot skill, followed by the bot |
| Judge from the transcript, never the bot's claims | no enforcer: the evaluate-a-grok-bot skill |
| Prompts never show checks or Jev questions to the bot | no enforcer: the evaluate-a-grok-bot skill |
| Purpose agreed with the owner; Boundaries only from repeated drift | no enforcer: design-a-grok-bot skill and the drift routine |
| Compressed field style; no owner names in profiles | no enforcer: these field-writing rules |
| Skills with local changes change only after the owner's answer | no enforcer: install and update steps above |
| Docs agree on safety test forms and on skipping handover for shared skills | `DocsTest` |
