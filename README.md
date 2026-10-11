# botkit

Versioned public templates for Grok Bot profiles and skills, plus a deterministic CLI that generates them.

- A **Grok Bot** is a long-running AI agent with its own computer, chats and scheduled routines; its profile (the description it's created with) is its whole persona, re-read on every wake.
- **Jev** is a scoring API used for yes/no judgments: a skill sends it fixed questions plus an input and gets a score per question back.

`botkit.py` is one file, Python 3.10+, standard library only. It prints bot profiles and skills in a fixed format: `profile`, `skill` and `jev-skill` are its only commands.

## Use it with your bots

A bot only knows a skill once it saves it through its own skill tool, so there's nothing to install by copying files. Instead, tell your bot:

> Follow the "Installing botkit on a bot computer" steps in botkit's AGENTS.md.

The bot clones the repo, saves the shared skills through its skill tool, and sets up its private fleet file, `bots/` folder and optional safety check outside the clone. Re-running the steps changes nothing that already exists without the owner's answer: identical skills are skipped, and for a skill whose content differs the bot shows a short summary of the differences and asks you to Replace, Merge or Skip. AGENTS.md also has the update steps.

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

Profile fields: `purpose`, `responsibilities`, `boundaries` and `voice` are required; `safety` and `references` are optional and left out of the output when empty.

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
| `templates/` | the profile, skill and Jev skill layouts (`profile.md`, `skill.md`, `jev-skill.md`) |
| `skills/` | shared skills: designing a bot, running safety checks, reading references |
| `examples/` | `fleet.example.json`, three sample bots (JSON input and generated `.md` profile), and the `inbound-check` safety check |
| `routines/` | copyable routine prompts |
| `scripts/regen.py` | regenerates every committed generated file; `--check` fails if any is stale |
| `scripts/public_safety_scan.py` | fails on emails, phone numbers, IP addresses, home paths, bearer tokens, keys and secrets (`NAME=value` and YAML `token: value` forms) |

## The sample safety check

`examples/safety/inbound-check --from SENDER --text MESSAGE` prints exactly one of `ALLOW`, `NEEDS_HUMAN` or `IGNORE` on stdout, the reason on stderr, and always exits 0.

- Blocked senders get `IGNORE`; unknown senders or text with a risky word get `NEEDS_HUMAN`; everything else gets `ALLOW`.
- Sender, text and risky words are normalized first (NFKC, casefold, every whitespace run to one space), so `gift<TAB>card`, a double space or fullwidth letters still match.
- Text, risky words and the block list are also folded: zero-width characters and soft hyphens are removed, and Cyrillic and Greek look-alike letters become Latin, so `pa<soft hyphen>y` or a Cyrillic `а` in `pаy` still match. A space inside a risky phrase may be missing (`giftcard` matches `gift card`). The allow list is matched without folding, so a look-alike sender name is never allowed.
- Bad arguments, a missing config or any error fail closed to `NEEDS_HUMAN`.
- The one exception to the single-token output: `inbound-check --help` (or `-h`) on its own prints the usage text.

Edit `inbound-check.json` next to it for your allow list, block list and risky words. The `ops-check` program named in the infra-bot example isn't included; write your own.

## Development

```sh
python3 -m unittest discover -s tests -v
python3 scripts/regen.py --check
python3 scripts/public_safety_scan.py
```

After changing `botkit.py` or any example or golden JSON input, run `python3 scripts/regen.py` and commit the regenerated files. CI runs the tests on Python 3.10 to 3.13, plus the public-safety scan.

This repo is public. Don't commit names, contact details, account IDs, hostnames or personal paths; the scan catches the common cases, not all of them.

## License

MIT, see [LICENSE](LICENSE).
