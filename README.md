# botkit

Versioned public templates for Grok Bot profiles and skills, plus a deterministic CLI that generates them.

`botkit.py` is one file, Python 3.10+, standard library only. It prints bot profiles and skills in a fixed format, and sets up a bot computer with shared skills, a fleet file and a sample safety check.

## Setup

On the bot computer, from a clone of this repo:

```sh
python3 botkit.py init
```

`init` writes into the bot computer's workspace (`--root`, default `/workspace`):

| What | Where |
| --- | --- |
| shared skills from `skills/` | `ROOT/.cursor/skills/` (change with `--skills-dir DIR`) |
| fleet file from `examples/fleet.example.json` | `ROOT/fleet.json` |
| sample safety check from `examples/safety/` | `ROOT/safety/` |
| empty reference index | `ROOT/references/INDEX.md` |

It never overwrites anything. Each file that already exists is reported as `skip <path> (exists)` and left alone, so running it again is safe. At the end it prints a checklist of what's left to do by hand.

To try it somewhere harmless first:

```sh
mkdir -p /tmp/botroot && python3 botkit.py init --root /tmp/botroot
```

## Generate a profile

Fields come from flags (repeat a flag for more list items) or from a JSON file.

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

The same from JSON (a string or a list of strings per field), written to a file:

```sh
python3 botkit.py profile --json examples/profiles/inbox-bot.json -o inbox-bot.txt
```

Profile fields: `purpose`, `responsibilities`, `boundaries` and `voice` are required; `safety` and `references` are optional and left out of the output when empty.

## Generate a skill

```sh
python3 botkit.py skill --name weekly-cleanup \
  --description "Use when asked to clean up old drafts: archive, never delete." \
  --purpose "archive drafts untouched for 30 days" \
  --step "list drafts older than 30 days" --step "archive each" --step "report count" \
  --decide "none found: say nothing" \
  --never "delete a draft"
```

Steps are numbered for you. Skill fields: `purpose` (one line) and `steps` are required; `name` and `description` (frontmatter, given together), `input`, `decide`, `run` and `never` are optional.

A skill that asks Jev questions uses `jev-skill`, which adds `questions` and builds Decide from your code checks (`--decide`), the score thresholds (`--threshold`) and what to do when Jev is down (`--jev-down`):

```sh
python3 botkit.py jev-skill --json tests/golden/jev-skill.json
```

Run `python3 botkit.py <command> --help` for every flag.

## Rules the generator enforces

- Output is deterministic: fixed section order, items in the order given, LF line endings, one trailing newline.
- A missing required field, an unknown field, an empty or multi-line item, or flags mixed with `--json` is an error (exit 2) with a message saying which field.
- Safety programs and reference files must be bare names, never paths.
- Jev questions must read `name (yes/no): what a yes means` or `name (pick-one: a/b/c): ...`.

## What's here

| Path | Contents |
| --- | --- |
| `botkit.py` | the CLI |
| `templates/` | the profile, skill and Jev skill layouts |
| `skills/` | shared skills: designing a bot, running safety checks, reading references |
| `examples/` | `fleet.example.json`, three sample bot profiles (JSON input and generated text), and the `inbound-check` safety check |
| `routines/` | copyable routine prompts |
| `scripts/regen.py` | regenerates every committed generated file; `--check` fails if any is stale |
| `scripts/public_safety_scan.py` | fails on emails, phone numbers, IP addresses, home paths and tokens |

## The sample safety check

`examples/safety/inbound-check --from SENDER --text MESSAGE` prints exactly one of `ALLOW`, `NEEDS_HUMAN` or `IGNORE` on stdout, the reason on stderr, and always exits 0. Blocked senders get `IGNORE`, unknown senders or risky words get `NEEDS_HUMAN`, everything else `ALLOW`. Bad arguments, a missing config or any error fail closed to `NEEDS_HUMAN`. Edit `inbound-check.json` next to it for your allow list, block list and risky words. The `ops-check` program named in the infra-bot example isn't included; write your own.

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
