#!/usr/bin/env python3
"""botkit: generate Grok Bot profiles and skills, and set up a bot computer.

Stdlib only. Output is deterministic: fixed section order, items in input
order, LF line endings, one trailing newline.
"""

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

__version__ = "0.1.0"

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = "/workspace"
DEFAULT_SKILLS_SUBDIR = os.path.join(".cursor", "skills")

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


def render(kind, data):
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
            data = json.load(sys.stdin)
        else:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
    except OSError as e:
        raise BotkitError(f"cannot read {path}: {e.strerror}")
    except json.JSONDecodeError as e:
        raise BotkitError(f"{path}: invalid JSON: {e}")
    if not isinstance(data, dict):
        raise BotkitError(f"{path}: top level must be a JSON object of fields")
    return data


def _write(text, out):
    data = text.encode("utf-8")
    if out:
        with open(out, "wb") as fh:
            fh.write(data)
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
    _write(render(kind, data), args.out)
    return 0


INDEX_STUB = (
    "# Reference index\n"
    "\n"
    "One line per file in this folder: `file: what it is / when to read it`.\n"
)


def _init_plan(root, skills_dir):
    skills_src = HERE / "skills"
    fleet_src = HERE / "examples" / "fleet.example.json"
    safety_src = HERE / "examples" / "safety"
    for p in (skills_src, fleet_src, safety_src):
        if not p.exists():
            raise BotkitError(f"missing {p}; run init from a full botkit checkout")
    plan = []
    for src in sorted(p for p in skills_src.rglob("*") if p.is_file()):
        plan.append((src, skills_dir / src.relative_to(skills_src)))
    plan.append((fleet_src, root / "fleet.json"))
    for src in sorted(p for p in safety_src.iterdir() if p.is_file()):
        plan.append((src, root / "safety" / src.name))
    plan.append((INDEX_STUB, root / "references" / "INDEX.md"))
    return plan


def _create(src, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = src.encode("utf-8") if isinstance(src, str) else src.read_bytes()
    with open(dest, "xb") as fh:
        fh.write(data)
    if not isinstance(src, str):
        shutil.copymode(src, dest)


def cmd_init(args):
    root = Path(args.root)
    if not root.is_dir():
        raise BotkitError(f"root {root} is not a directory; create it or pass --root DIR")
    skills_dir = Path(args.skills_dir) if args.skills_dir else root / DEFAULT_SKILLS_SUBDIR
    for src, dest in _init_plan(root, skills_dir):
        if os.path.lexists(dest):
            print(f"skip {dest} (exists)")
            continue
        try:
            _create(src, dest)
        except FileExistsError:
            print(f"skip {dest} (exists)")
            continue
        print(f"create {dest}")
    print(
        "\nNext steps:\n"
        f"[ ] {root / 'fleet.json'}: replace the sample bots with yours, one line each "
        "('<name>': '<name>: <purpose in one line>')\n"
        f"[ ] {root / 'safety'}: set allow/block lists in inbound-check.json; test allow, "
        "needs-human and ignore cases before any profile points at it\n"
        f"[ ] {root / 'references'}: add reference files and one INDEX.md line each\n"
        "[ ] design each bot with the design-a-grok-bot skill; generate its profile with "
        "'python3 botkit.py profile', never by hand\n"
        "[ ] create routines from routines/*.md; each must serve a listed responsibility\n"
        "[ ] create the bot, then read its live profile back and compare to the generated text"
    )
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="botkit",
        description="Generate Grok Bot profiles and skills; set up a bot computer.",
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
        for f in spec:
            sp.add_argument(*f.flags, dest=f.key, action="append", metavar="TEXT", help=f.help)
        sp.set_defaults(func=cmd_generate)
    ip = sub.add_parser(
        "init", help="set up a bot computer without overwriting anything",
        description="Copy skills, fleet.json, safety checks and a reference index into a bot "
                    "computer. Existing files are never overwritten.",
    )
    ip.add_argument("--root", default=DEFAULT_ROOT,
                    help=f"bot computer workspace (default: {DEFAULT_ROOT})")
    ip.add_argument("--skills-dir", metavar="DIR",
                    help=f"bot skills folder (default: ROOT/{DEFAULT_SKILLS_SUBDIR.replace(os.sep, '/')})")
    ip.set_defaults(func=cmd_init)
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
