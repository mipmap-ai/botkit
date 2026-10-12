#!/usr/bin/env python3
"""Regenerate every committed generated file from its JSON input via botkit.

  examples/profiles/<bot>.json -> examples/profiles/<bot>.md  (profile)
  examples/evals/<bot>.json    -> examples/evals/<bot>.md     (evals)
  tests/golden/<kind>*.json    -> tests/golden/<kind>*.md     (kind from file name)
  skills/<name>/skill.json     -> skills/<name>/SKILL.md      (skill; shared skills without one are hand-written)

With --check, write nothing and exit 1 if any file differs.
Every file must put exactly one blank line between sections, so a profile
hand-written in that style regenerates with no whitespace-only diff.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import botkit  # noqa: E402


def kind_for(path):
    if path.parent.name in ("profiles", "evals"):
        return {"profiles": "profile", "evals": "evals"}[path.parent.name]
    for kind in ("evals", "jev-skill", "skill", "profile"):
        if path.name.startswith(kind):
            return kind
    raise SystemExit(f"cannot tell template kind for {path}")


def targets():
    inputs = sorted((ROOT / "examples" / "profiles").glob("*.json"))
    inputs += sorted((ROOT / "examples" / "evals").glob("*.json"))
    inputs += sorted((ROOT / "tests" / "golden").glob("*.json"))
    for src in inputs:
        yield src, src.with_suffix(".md"), kind_for(src)
    for src in sorted((ROOT / "skills").glob("*/skill.json")):
        yield src, src.with_name("SKILL.md"), "skill"


HEADER = re.compile(r"^[A-Z][A-Za-z]*:$")


def layout_errors(text):
    lines = text.split("\n")[:-1]
    errors = []
    if "" in lines[:1] or "" in lines[-1:]:
        errors.append("leading or trailing blank line")
    headers = [n for n, line in enumerate(lines) if HEADER.match(line)]
    for n in headers[1:]:
        if lines[n - 1] != "" or lines[n - 2] == "":
            errors.append(f"line {n + 1} {lines[n]!r}: need exactly one blank line before it")
    for n, line in enumerate(lines):
        if line == "" and n + 1 not in headers:
            errors.append(f"line {n + 1}: blank line not before a section")
    return errors


def expected(src, kind):
    text = botkit.render(kind, botkit._load_json(str(src)))
    errors = layout_errors(text)
    if errors:
        raise SystemExit(f"{src.relative_to(ROOT)}: bad layout: {'; '.join(errors)}")
    return text.encode("utf-8")


def main(argv):
    check = "--check" in argv
    stale = []
    for src, dest, kind in targets():
        want = expected(src, kind)
        if dest.exists() and dest.read_bytes() == want:
            continue
        stale.append(dest)
        if not check:
            dest.write_bytes(want)
            print(f"wrote {dest.relative_to(ROOT)}")
    if check and stale:
        for dest in stale:
            print(f"stale {dest.relative_to(ROOT)}; run python3 scripts/regen.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
