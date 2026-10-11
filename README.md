# botkit

Versioned public templates for Grok Bot profiles, skills and evals, plus a deterministic CLI that generates them.

- A **Grok Bot** is a long-running AI agent with its own chats, scheduled routines and desktop. All of an owner's Grok Bots share one bot computer, so its files (including the safety checks and reference files botkit sets up) are shared by every bot. Its profile (the description it's created with) is its whole persona, re-read on every wake.
- **Jev** is a scoring API used for yes/no judgments: a skill sends it fixed questions plus an input and gets a score per question back.

`botkit.py` is one file, Python 3.10+, standard library only. It prints bot profiles, skills and eval scenarios in a fixed format: `profile`, `skill`, `jev-skill` and `evals` are its only commands.

## Use it with your bots

A bot only knows a skill once it's saved through a skill tool, so there's nothing to install by copying files. Instead, tell your bot:

> Follow the "Installing botkit on a bot computer" steps in botkit's AGENTS.md.

The bot clones the repo, saves the shared skills through its skill tool, and sets up its private fleet file, `bots/` folder and optional safety check outside the clone. On Grok Bot, skills are global (one library shared by all of the owner's bots), so saving once covers every bot. Only where each bot has its own skill store does it also hand bot-safety-check and bot-references to each bot whose profile has `Safety:` or `References:`. Re-running the steps changes nothing that already exists without the owner's answer: identical skills are skipped, and for a skill whose content differs the bot shows a short summary of the differences and asks you to Replace, Merge or Skip. AGENTS.md also has the update steps; there, a copy with no local changes is updated without asking.

To use botkit on your own machine, clone the repo and run `python3 botkit.py` from the clone.

## Inputs and outputs

Every bot has two files. Keep both; only the second goes into the bot.

| File | What it is |
| --- | --- |
| `<bot>.json` | the **input**: the profile's fields as JSON. Edit this. |
| `<bot>.md` | the **generated profile**, printed by `botkit.py profile --json <bot>.json`. This is the only thing you paste into a bot as its description. Never edit it by hand. |

`examples/profiles/` has this pair for each of the three sample bots (inbox-bot, feed-bot and infra-bot). On a bot computer, your own inputs live in a private `bots/` folder next to your fleet file, outside the clone (see AGENTS.md), and each profile is generated beside its input:

```text
python3 botkit/botkit.py profile --json bots/<name>.json -o bots/<name>.md
```

Field names: JSON keys are the plural field names (`responsibilities`, `boundaries`, `references`, `steps`, `questions`, `thresholds`), and the flags are singular (`--responsibility`, `--boundary`, `--reference`, `--step`, `--question`, `--threshold`); repeat a flag for each list item. The plural flag spellings also work. In JSON a list field takes a string or a list of strings.

## Generate a profile

From flags:

```sh
python3 botkit.py profile \
  --purpose "keep inbox triaged so nothing important waits" \
  --responsibility "sort new mail: act, reply, read later, archive" \
  --responsibility "draft replies for mail needing an answer" \
  --boundary "drafts only; never sends" \
  --safety "inbound-check --from {sender} --text {message}" \
  --voice terse --voice "plain words"
```

```text
Purpose:
- keep inbox triaged so nothing important waits

Responsibilities:
- sort new mail: act, reply, read later, archive
- draft replies for mail needing an answer

Boundaries:
- drafts only; never sends

Safety:
- inbound-check --from {sender} --text {message}

Voice:
- terse
- plain words
```

From JSON, written to a file with `-o` (any path you choose):

```sh
python3 botkit.py profile --json examples/profiles/inbox-bot.json -o /tmp/inbox-bot.md
```

Profile fields: `purpose`, `responsibilities` and `voice` are required; `boundaries`, `safety` and `references` are optional and left out of the output when empty (most bots need no Boundaries). Sections are separated by exactly one blank line.

### Fleet file

`profile` also checks your fleet file, a JSON object of `"<key>": "<name>: <purpose in one line>"` lines. Its path is `--fleet PATH`, else the `BOTKIT_FLEET` environment variable, else `ROOT/fleet.json` (the folder holding the botkit clone). A `--fleet` or `BOTKIT_FLEET` path that is missing, a directory, not a JSON object or has a non-string line is an error; the same problem with the default file (as in a dev clone) prints a warning and skips the check. With `--json bots/<name>.json`, a fleet file with no `<name>` line prints a warning and still exits 0:

```sh
BOTKIT_FLEET=shared/fleet.json python3 botkit/botkit.py profile --json bots/<name>.json -o bots/<name>.md
```

## Generate a skill

From JSON:

```sh
python3 botkit.py skill --json tests/golden/skill.json -o /tmp/weekly-cleanup.md
```

From flags:

```sh
python3 botkit.py skill --name weekly-cleanup \
  --description "Use when asked to clean up old drafts: archive, never delete." \
  --purpose "archive drafts untouched for 30 days" \
  --step "list drafts older than 30 days" --step "archive each" --step "report count" \
  --decide "none found: say nothing" \
  --never "delete a draft"
```

Steps are numbered for you. Skill fields: `purpose` (one line) and `steps` are required; `name` and `description` (frontmatter, given together), `input`, `decide`, `run` and `never` are optional.

## Generate a Jev skill

A skill that asks Jev questions uses `jev-skill`. It adds `questions` and builds Decide from your exact code checks (`--decide`), then the score thresholds (`--threshold`), then what to do when Jev is down (`--jev-down`):

```sh
python3 botkit.py jev-skill --name mention-scout \
  --description "Use when scanning new mentions for ones worth a reply." \
  --purpose "pick mentions worth a reply" \
  --input "mentions since last run" --input "state file of seen ids" \
  --question "needs_reply (yes/no): a reply would help the asker" \
  --question "tone (pick-one: friendly/neutral/hostile): tone of the mention" \
  --step "drop ids already in state file" --step "ask Jev questions per mention" \
  --step "list picks, one line each" \
  --decide "id in state file: skip, no Jev call" \
  --threshold "needs_reply >= 0.8: list it" \
  --threshold "needs_reply 0.5-0.8: list under maybe" \
  --threshold "tone hostile: never list" \
  --jev-down "list nothing; report Jev down once" \
  --run "jev ask --questions mention-scout.questions --input {mention}" \
  --never "reply or post"
```

That prints the same bytes as `python3 botkit.py jev-skill --json tests/golden/jev-skill.json` (in JSON the Jev-down field is `jev_down`).

`skill` and `jev-skill` also take `--root DIR`: the command fails if an item names a `skills/<name>` or `references/<file>` that doesn't exist under `DIR` (skills are also looked up in `DIR/botkit/skills`). Only the skill you're generating is checked. Name other skills by path; a phrase like `the <name> skill` with an unknown name only prints a warning (the "name" may really be an adjective such as follow-up) and still exits 0. The shared skills in `skills/` are hand-written; a test checks in CI that they, the routines and the docs name only skills and `ROOT/botkit/` files that exist in the repo.

```sh
python3 botkit.py skill --root . --purpose "check a new bot" --step "follow skills/evaluate-a-grok-bot/SKILL.md"
```

## Eval scenarios

Each bot gets 6 to 30 scenarios (start near 10 and add one from each real failure) that prove it does its job and refuses the rest. The evaluate-a-grok-bot skill runs them before a bot goes live and after every profile or skill change; a change is kept only if the pass count doesn't drop. `evals` validates and prints a scenario file:

```sh
python3 botkit.py evals --json examples/evals/inbox-bot.json -o /tmp/inbox-bot-evals.md
```

- At least 3 `positive` scenarios (typical requests) and 3 `negative` ones, each with a `negative_type`: `adjacent-action`, `out-of-scope`, `injected-instruction` (at least one is required) or `quiet`.
- Each scenario has an `id`, a `prompt` that reads like a normal request, an optional `setup` (in both, the words eval, test, judge and judgment are rejected; this is deliberately conservative, so reword staged content like "a blood-test reminder"), and one or more `checks`: `tool_called`, `tool_not_called`, `output_contains`, `output_not_contains`, `safety_token` or `no_output`.
- An optional `jev_question` with a `threshold` covers judgment calls code can't decide.

See `templates/evals.md` and `examples/evals/inbox-bot.md`.

Run `python3 botkit.py <command> --help` for every flag.

## Rules the generator enforces

- Output is deterministic: fixed section order, items in the order given, LF line endings, one trailing newline.
- A missing required field, an unknown field, an empty or multi-line item, flags mixed with `--json`, an unreadable or non-UTF-8 input, or an unwritable `-o` path is an error (exit 2) with a message saying what's wrong.
- Safety programs and reference files must be bare names, never paths.
- Jev questions must read `name (yes/no): what a yes means` or `name (pick-one: a/b/c): ...`.

## What's here

| Path | Contents |
| --- | --- |
| `botkit.py` | the CLI |
| `templates/` | the profile, skill, Jev skill and evals layouts (`profile.md`, `skill.md`, `jev-skill.md`, `evals.md`) |
| `skills/` | shared skills: designing a bot, evaluating a bot, reviewing token cost, running safety checks, reading references |
| `examples/` | `fleet.example.json`, three sample bots (JSON input and generated `.md` profile), inbox-bot's eval scenarios, and the `inbound-check` safety check with its cases |
| `routines/` | copyable routine prompts |
| `scripts/run_safety_cases.py` | runs safety-check cases files |
| `scripts/regen.py` | regenerates every committed generated file; `--check` fails if any is stale |
| `scripts/public_safety_scan.py` | fails on emails, phone numbers, IP addresses, home paths, bearer tokens, keys and secrets (`NAME=value` and YAML `token: value` forms) |

## The sample safety check

`examples/safety/inbound-check --from SENDER --text MESSAGE` prints exactly one of `ALLOW`, `NEEDS_HUMAN` or `IGNORE` on stdout, the reason on stderr, and always exits 0.

- Blocked senders get `IGNORE`; unknown senders or text with a risky word get `NEEDS_HUMAN`; everything else gets `ALLOW`.
- Sender, text and risky words are normalized first (NFKC, casefold, every whitespace run to one space), so `gift<TAB>card`, a double space or fullwidth letters still match.
- Text, risky words and the block list are also folded: zero-width characters and soft hyphens are removed, and Cyrillic and Greek look-alike letters become Latin, so `pa<soft hyphen>y` or a Cyrillic `а` in `pаy` still match. A space inside a risky phrase may be missing (`giftcard` matches `gift card`). The allow list is matched without folding, so a look-alike sender name is never allowed.
- Bad arguments, a missing config or any error fail closed to `NEEDS_HUMAN`.
- The one exception to the single-token output: `inbound-check --help` (or `-h`) on its own prints the usage text.

Edit `inbound-check.json` next to it for your allow list, block list and risky words. `inbound-check.cases.json` maps argument lists to the expected token; `python3 scripts/run_safety_cases.py` runs every `examples/safety/*.cases.json` (or the files you name) and fails on any mismatch. A program that already has a unittest suite in `ROOT/safety/tests/` can keep it instead, run with `python3 -m unittest discover -s ROOT/safety/tests`. Re-run the tests whenever the program or its config changes, and add one case from a real past mistake for each new rule, in whichever form the program uses. The `ops-check` program named in the infra-bot example isn't included; write your own.

## Development

```sh
python3 -m unittest discover -s tests -v
python3 scripts/regen.py --check
python3 scripts/run_safety_cases.py
python3 scripts/public_safety_scan.py
```

After changing `botkit.py` or any example or golden JSON input, run `python3 scripts/regen.py` and commit the regenerated files. CI runs the tests, the regen check and the safety cases on Python 3.10 to 3.13, plus the public-safety scan.

This repo is public. Don't commit names, contact details, account IDs, hostnames or personal paths; the scan catches the common cases, not all of them. The only other names and links allowed are botkit's own repo, the public avatar site `https://botbuilder.mipmap.ai/`, and the third-party projects credited below with their license (pstack, which the shared skills also name).

## Credits

The evals, safety cases and drift loop adapt Cursor's public [pstack plugin](https://github.com/cursor/plugins/tree/main/pstack) (MIT): its eval playbook, the principles "test behavior, not implementation", "prove it works" and "encode lessons in structure", and its `correct` skill (the rule-to-enforcer table and cases from real past mistakes).

## License

MIT, see [LICENSE](LICENSE).
