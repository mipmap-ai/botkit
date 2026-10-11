#!/usr/bin/env python3
"""Regenerate every committed generated file from its JSON input via botkit.

  examples/profiles/<bot>.json -> examples/profiles/<bot>.md  (profile)
  tests/golden/<kind>*.json    -> tests/golden/<kind>*.md     (kind from file name)

With --check, write nothing and exit 1 if any file differs.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import botkit  # noqa: E402


def kind_for(path):
    if path.parent.name == "profiles":
        return "profile"
    for kind in ("jev-skill", "skill", "profile"):
        if path.name.startswith(kind):
            return kind
    raise SystemExit(f"cannot tell template kind for {path}")


def targets():
    inputs = sorted((ROOT / "examples" / "profiles").glob("*.json"))
    inputs += sorted((ROOT / "tests" / "golden").glob("*.json"))
    for src in inputs:
        yield src, src.with_suffix(".md"), kind_for(src)


def expected(src, kind):
    return botkit.render(kind, botkit._load_json(str(src))).encode("utf-8")


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
