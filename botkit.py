#!/usr/bin/env python3
"""botkit: generate Grok Bot profiles, skills and eval scenarios.

Stdlib only. Output is deterministic: fixed section order, items in input
order, LF line endings, one trailing newline.
"""

import argparse
import json
import re
import sys
from pathlib import Path

__version__ = "0.1.0"

BARE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NUMBERED = re.compile(r"^\d+[.)]\s")
QUESTION = re.compile(r"^\S+ \((?:yes/no|pick-one(?:: [^)]+)?)\): \S")


class BotkitError(Exception):
    pass


class Field:
    def __init__(self, key, label, flags, required=False, scalar=False, help=""):
        self.key = key
        self.label = label
        self.flags = flags
        self.required = required
        self.scalar = scalar
        self.help = help


SKILL_HEAD = [
    Field("name", None, ["--name"], scalar=True,
          help="skill name for frontmatter (lowercase-dashed); needs --description"),
    Field("description", None, ["--description"], scalar=True,
          help="one-line 'Use when ...' for frontmatter; needs --name"),
    Field("purpose", "Purpose", ["--purpose"], required=True, scalar=True,
          help="what the skill gets done, one line"),
    Field("input", "Input", ["--input"], help="what it starts from (repeatable)"),
]

SKILL_TAIL = [
    Field("run", "Run", ["--run"], help="exact command (repeatable)"),
    Field("never", "Never", ["--never"],
          help="hard limit not already enforced by a Safety program (repeatable)"),
]

SPECS = {
    "profile": [
        Field("purpose", "Purpose", ["--purpose"], required=True,
              help="real reason the bot exists; one per part (repeatable)"),
        Field("responsibilities", "Responsibilities",
              ["--responsibility", "--responsibilities"], required=True,
              help="outcome the bot owns (repeatable)"),
        Field("boundaries", "Boundaries", ["--boundary", "--boundaries"], required=True,
              help="edge the purpose leaves ambiguous, or the adjacent verb it never does (repeatable)"),
        Field("safety", "Safety", ["--safety"],
              help="'<program> [parameters]', bare program name (repeatable; omitted when empty)"),
        Field("references", "References", ["--reference", "--references"],
              help="bare reference file name (repeatable; omitted when empty)"),
        Field("voice", "Voice", ["--voice"], required=True,
              help="a few words (repeatable)"),
    ],
    "skill": SKILL_HEAD + [
        Field("steps", "Steps", ["--step", "--steps"], required=True,
              help="one step, numbered automatically (repeatable)"),
        Field("decide", "Decide", ["--decide"], help="go if / else / on failure (repeatable)"),
    ] + SKILL_TAIL,
    "jev-skill": SKILL_HEAD + [
        Field("questions", "Questions", ["--question", "--questions"], required=True,
              help="'name (yes/no or pick-one): what a yes means' (repeatable)"),
        Field("steps", "Steps", ["--step", "--steps"], required=True,
              help="one step, numbered automatically (repeatable)"),
        Field("decide", None, ["--decide"],
              help="exact code check, listed first under Decide (repeatable)"),
        Field("thresholds", None, ["--threshold", "--thresholds"], required=True,
              help="Jev score threshold and its action, under Decide (repeatable)"),
        Field("jev_down", None, ["--jev-down"], required=True, scalar=True,
              help="what to do when Jev is down (exit 2), last line of Decide"),
    ] + SKILL_TAIL,
}


def _items(field, raw):
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list) or not all(isinstance(v, str) for v in raw):
        raise BotkitError(f"field '{field.key}' must be a string or a list of strings")
    out = []
    for value in raw:
        if "\n" in value or "\r" in value:
            raise BotkitError(f"field '{field.key}': items must be one line: {value!r}")
        value = value.strip()
        if not value:
            raise BotkitError(f"field '{field.key}': empty item")
        if value.startswith("- "):
            raise BotkitError(f"field '{field.key}': drop the leading '- ', botkit adds it: {value!r}")
        out.append(value)
    if field.scalar and len(out) > 1:
        raise BotkitError(f"field '{field.key}' takes one value, got {len(out)}")
    return out


def _check_bare(field, value, what):
    if "/" in value or "\\" in value or ".." in value or not BARE_NAME.match(value):
        raise BotkitError(f"field '{field.key}': {what} must be a bare name, got {value!r}")


def normalize(kind, data):
    """Validate raw field data and return {key: [items]} for every field of kind."""
    spec = SPECS[kind]
    known = {f.key for f in spec}
    unknown = sorted(set(data) - known)
    if unknown:
        raise BotkitError(
            f"unknown field(s) for {kind}: {', '.join(unknown)} "
            f"(known: {', '.join(f.key for f in spec)})"
        )
    fields = {}
    for f in spec:
        fields[f.key] = _items(f, data.get(f.key))
    missing = [f.key for f in spec if f.required and not fields[f.key]]
    if missing:
        raise BotkitError(f"missing required field(s) for {kind}: {', '.join(missing)}")

    byname = {f.key: f for f in spec}
    for item in fields.get("safety", []):
        _check_bare(byname["safety"], item.split()[0], "safety program")
    for item in fields.get("references", []):
        _check_bare(byname["references"], item, "reference file")
    for item in fields.get("steps", []):
        if NUMBERED.match(item):
            raise BotkitError(f"field 'steps': steps are numbered automatically, drop the number: {item!r}")
    for item in fields.get("questions", []):
        if not QUESTION.match(item):
            raise BotkitError(
                "field 'questions': expected 'name (yes/no): what a yes means' "
                f"or 'name (pick-one: a/b/c): ...', got {item!r}"
            )
    if kind != "profile":
        name, desc = fields["name"], fields["description"]
        if bool(name) != bool(desc):
            raise BotkitError("fields 'name' and 'description' go together: give both or neither")
        if name and not SKILL_NAME.match(name[0]):
            raise BotkitError(f"field 'name': use lowercase words joined by '-', got {name[0]!r}")
    return fields


def _section(label, items):
    return [f"{label}:"] + [f"- {item}" for item in items]


CHECKS = ("tool_called", "tool_not_called", "output_contains", "output_not_contains",
          "safety_token", "no_output")
NEGATIVE_TYPES = ("adjacent-action", "out-of-scope", "injected-instruction", "quiet")
SAFETY_TOKENS = ("ALLOW", "NEEDS_HUMAN", "IGNORE")
TOOL_NAME = re.compile(r"^[A-Za-z0-9_.:-]+$")
GIVEAWAY = re.compile(r"(?i)\b(?:evals?|evaluat\w*|tests?|testing|tested|judge[sd]?|judging|judge?ments?)\b")
MAX_SCENARIOS = 30
SCENARIO_KEYS = ("id", "kind", "negative_type", "setup", "prompt", "checks", "jev_question")


def _line(where, value, what):
    if not isinstance(value, str) or not value.strip():
        raise BotkitError(f"{where}: '{what}' must be a non-empty string")
    if "\n" in value or "\r" in value:
        raise BotkitError(f"{where}: '{what}' must be one line")
    return value.strip()


def _check(where, raw):
    if not isinstance(raw, dict) or set(raw) - {"type", "value"} or "type" not in raw:
        raise BotkitError(f"{where}: each check is {{\"type\": ..., \"value\": ...}}")
    ctype = raw["type"]
    if ctype not in CHECKS:
        raise BotkitError(f"{where}: unknown check type {ctype!r} (known: {', '.join(CHECKS)})")
    if ctype == "no_output":
        if "value" in raw:
            raise BotkitError(f"{where}: check 'no_output' takes no value")
        return ctype
    value = _line(where, raw.get("value"), f"{ctype} value")
    if ctype in ("tool_called", "tool_not_called"):
        if not TOOL_NAME.match(value):
            raise BotkitError(f"{where}: tool name must be a bare identifier, got {value!r}")
        return f"{ctype} {value}"
    if ctype == "safety_token":
        if value not in SAFETY_TOKENS:
            raise BotkitError(f"{where}: safety_token must be one of {', '.join(SAFETY_TOKENS)}")
        return f"{ctype} {value}"
    return f"{ctype} " + json.dumps(value, ensure_ascii=False)


def _jev(where, raw):
    if not isinstance(raw, dict) or set(raw) != {"question", "threshold"}:
        raise BotkitError(f"{where}: jev_question is {{\"question\": ..., \"threshold\": ...}}")
    question = _line(where, raw["question"], "jev_question.question")
    if not QUESTION.match(question):
        raise BotkitError(f"{where}: jev question must read 'name (yes/no): what a yes means', got {question!r}")
    t = raw["threshold"]
    if isinstance(t, bool) or not isinstance(t, (int, float)) or not 0 < t <= 1:
        raise BotkitError(f"{where}: jev threshold must be a number in (0, 1], got {t!r}")
    return f"{question} >= {format(t, 'g')}"


def render_evals(data):
    unknown = sorted(set(data) - {"bot", "scenarios"})
    if unknown:
        raise BotkitError(f"unknown field(s) for evals: {', '.join(unknown)} (known: bot, scenarios)")
    bot = data.get("bot")
    if not isinstance(bot, str) or not SKILL_NAME.match(bot):
        raise BotkitError("field 'bot': required, lowercase words joined by '-'")
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list) or not 6 <= len(scenarios) <= MAX_SCENARIOS:
        raise BotkitError(f"field 'scenarios': required, a list of 6 to {MAX_SCENARIOS} scenarios")

    blocks = [_section("Bot", [bot])]
    seen, kinds, negatives = set(), [], []
    for n, sc in enumerate(scenarios, 1):
        where = f"scenario {n}"
        if not isinstance(sc, dict):
            raise BotkitError(f"{where}: must be a JSON object")
        unknown = sorted(set(sc) - set(SCENARIO_KEYS))
        if unknown:
            raise BotkitError(f"{where}: unknown field(s): {', '.join(unknown)} (known: {', '.join(SCENARIO_KEYS)})")
        missing = [k for k in ("id", "kind", "prompt", "checks") if k not in sc]
        if missing:
            raise BotkitError(f"{where}: missing required field(s): {', '.join(missing)}")
        sid = sc["id"]
        if not isinstance(sid, str) or not SKILL_NAME.match(sid):
            raise BotkitError(f"{where}: 'id' must be lowercase words joined by '-'")
        where = f"scenario {n} ({sid})"
        if sid in seen:
            raise BotkitError(f"{where}: duplicate id")
        seen.add(sid)
        kind = sc["kind"]
        if kind not in ("positive", "negative"):
            raise BotkitError(f"{where}: 'kind' must be 'positive' or 'negative'")
        if kind == "negative":
            ntype = sc.get("negative_type")
            if ntype not in NEGATIVE_TYPES:
                raise BotkitError(f"{where}: negative scenarios need 'negative_type', one of {', '.join(NEGATIVE_TYPES)}")
            negatives.append(ntype)
            kind_line = f"negative ({ntype})"
        else:
            if "negative_type" in sc:
                raise BotkitError(f"{where}: 'negative_type' is only for negative scenarios")
            kind_line = "positive"
        kinds.append(kind)
        items = [f"id: {sid}", f"kind: {kind_line}"]
        for key in ("setup", "prompt"):
            if key not in sc:
                continue
            text = _line(where, sc[key], key)
            word = GIVEAWAY.search(text)
            if word:
                raise BotkitError(f"{where}: {key} must read like a normal request; drop {word.group(0)!r}")
            items.append(f"{key}: {text}")
        checks = sc["checks"]
        if not isinstance(checks, list) or not checks:
            raise BotkitError(f"{where}: 'checks' must be a non-empty list")
        items += [f"check: {_check(where, c)}" for c in checks]
        if "jev_question" in sc:
            items.append(f"jev: {_jev(where, sc['jev_question'])}")
        blocks.append(_section("Scenario", items))

    if kinds.count("positive") < 3 or kinds.count("negative") < 3:
        raise BotkitError(
            f"need at least 3 positive and 3 negative scenarios, got "
            f"{kinds.count('positive')} positive and {kinds.count('negative')} negative"
        )
    if "injected-instruction" not in negatives:
        raise BotkitError("need at least one negative scenario with negative_type 'injected-instruction'")
    return "\n\n".join("\n".join(b) for b in blocks) + "\n"


SKILL_PATH = re.compile(r"(?<![\w.-])skills/([a-z0-9]+(?:-[a-z0-9]+)*)")
SKILL_PHRASE = re.compile(r"\b[Tt]he (?:shared )?([a-z0-9]+(?:-[a-z0-9]+)+) skill\b")
# Hyphenated modifiers that read as "the <adjective> skill", not a skill's name.
NOT_SKILL_NAMES = frozenset((
    "built-in", "follow-up", "high-level", "long-running", "low-level", "one-off",
    "read-only", "same-day", "step-by-step", "top-level", "up-to-date", "well-known",
))
REFERENCE_PATH = re.compile(r"(?<![\w.-])references/([^\s`'\"(),;:{}<>]+)")


def check_links(kind, data, root):
    """Fail if an item names a skill folder or references/ file missing under root.

    Skills are found at ROOT/skills/<name>/SKILL.md or ROOT/botkit/skills/<name>/SKILL.md;
    references at ROOT/references/<file>.
    """
    root = Path(root)
    if not root.is_dir():
        raise BotkitError(f"--root {root} is not a directory")
    f = normalize(kind, data)
    for key in ("purpose", "input", "questions", "steps", "decide", "thresholds", "jev_down", "run", "never"):
        for n, item in enumerate(f.get(key, []), 1):
            where = f"field '{key}' item {n}"
            names = set(SKILL_PATH.findall(item)) | (set(SKILL_PHRASE.findall(item)) - NOT_SKILL_NAMES)
            for name in sorted(names):
                if not any((base / "skills" / name / "SKILL.md").is_file()
                           for base in (root, root / "botkit")):
                    raise BotkitError(
                        f"{where} names skill '{name}', but there is no {name}/SKILL.md "
                        f"under {root / 'skills'} or {root / 'botkit' / 'skills'}"
                    )
            for ref in sorted(set(REFERENCE_PATH.findall(item))):
                ref = ref.rstrip(".")
                if ".." in ref.split("/") or not (root / "references" / ref).is_file():
                    raise BotkitError(f"{where} names references/{ref}, but {root / 'references' / ref} does not exist")


def render(kind, data):
    if kind == "evals":
        return render_evals(data)
    f = normalize(kind, data)
    if kind == "profile":
        lines = []
        for field in SPECS["profile"]:
            if f[field.key]:
                lines += _section(field.label, f[field.key])
        return "\n".join(lines) + "\n"

    blocks = [_section("Purpose", f["purpose"])]
    if f["input"]:
        blocks.append(_section("Input", f["input"]))
    if kind == "jev-skill":
        blocks.append(_section("Questions", f["questions"]))
    blocks.append(_section("Steps", [f"{i}. {s}" for i, s in enumerate(f["steps"], 1)]))
    decide = list(f["decide"])
    if kind == "jev-skill":
        decide += f["thresholds"] + [f"Jev down (exit 2): {f['jev_down'][0]}"]
    if decide:
        blocks.append(_section("Decide", decide))
    for key, label in (("run", "Run"), ("never", "Never")):
        if f[key]:
            blocks.append(_section(label, f[key]))
    body = "\n\n".join("\n".join(b) for b in blocks) + "\n"
    if f["name"]:
        front = [
            "---",
            f"name: {f['name'][0]}",
            "description: " + json.dumps(f["description"][0], ensure_ascii=False),
            "---",
        ]
        body = "\n".join(front) + "\n" + body
    return body


def _load_json(path):
    try:
        if path == "-":
            raw = sys.stdin.buffer.read()
        else:
            with open(path, "rb") as fh:
                raw = fh.read()
        data = json.loads(raw.decode("utf-8"))
    except OSError as e:
        raise BotkitError(f"cannot read {path}: {e.strerror or e}")
    except UnicodeDecodeError:
        raise BotkitError(f"{path}: not UTF-8 text")
    except json.JSONDecodeError as e:
        raise BotkitError(f"{path}: invalid JSON: {e}")
    if not isinstance(data, dict):
        raise BotkitError(f"{path}: top level must be a JSON object of fields")
    return data


def _write(text, out):
    data = text.encode("utf-8")
    if out:
        try:
            with open(out, "wb") as fh:
                fh.write(data)
        except OSError as e:
            raise BotkitError(f"cannot write {out}: {e.strerror or e}")
    else:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()


def cmd_generate(args):
    kind = args.command
    flags = {f.key: getattr(args, f.key) for f in SPECS[kind] if getattr(args, f.key) is not None}
    if args.json is not None:
        if flags:
            raise BotkitError("use either --json or field flags, not both")
        data = _load_json(args.json)
    else:
        data = flags
    text = render(kind, data)
    if getattr(args, "root", None) is not None:
        check_links(kind, data, args.root)
    _write(text, args.out)
    return 0


def cmd_evals(args):
    _write(render("evals", _load_json(args.json)), args.out)
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="botkit",
        description="Generate Grok Bot profiles, skills and eval scenarios.",
    )
    p.add_argument("--version", action="version", version=f"botkit {__version__}")
    sub = p.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True
    helps = {
        "profile": "print a bot profile",
        "skill": "print a skill",
        "jev-skill": "print a skill that asks Jev questions",
    }
    for kind, spec in SPECS.items():
        sp = sub.add_parser(kind, help=helps[kind], description=helps[kind] + ".")
        sp.add_argument("--json", metavar="FILE", help="read fields from a JSON object ('-' for stdin)")
        sp.add_argument("-o", "--out", metavar="FILE", help="write to FILE instead of stdout")
        if kind != "profile":
            sp.add_argument(
                "--root", metavar="DIR",
                help="fail if an item names a skill (skills/<name> or 'the <name> skill') or a "
                     "references/<file> missing under DIR (skills also found in DIR/botkit/skills)")
        for f in spec:
            sp.add_argument(*f.flags, dest=f.key, action="append", metavar="TEXT", help=f.help)
        sp.set_defaults(func=cmd_generate)
    ep = sub.add_parser(
        "evals", help="validate and print a bot's eval scenarios",
        description=f"Validate and print a bot's eval scenarios: 6 to {MAX_SCENARIOS}, at least 3 positive "
                    "and 3 negative, at least one negative of type injected-instruction.")
    ep.add_argument("--json", metavar="FILE", required=True, help="scenario file ('-' for stdin)")
    ep.add_argument("-o", "--out", metavar="FILE", help="write to FILE instead of stdout")
    ep.set_defaults(func=cmd_evals)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except BotkitError as e:
        print(f"botkit: error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
