#!/usr/bin/env python3
"""Run safety-check cases files and compare each result with the expected one.

Usage: run_safety_cases.py [CASES_FILE ...]
       (default: examples/safety/*.cases.json in this repo)

A cases file sits next to its program as <program>.cases.json:
  {"program": "<program>", "cases": [{"args": [...], "expect": "ALLOW", "why": "..."}]}

Each case runs <program> with its args from the program's folder. A case
passes when the program exits 0 and prints exactly the expected token.
Exit 0 when every case passes, 1 on any failure, 2 on a bad cases file.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS = ("ALLOW", "NEEDS_HUMAN", "IGNORE")
SUFFIX = ".cases.json"


class BadCases(Exception):
    pass


def load(path):
    if not path.name.endswith(SUFFIX):
        raise BadCases(f"{path}: name must be <program>{SUFFIX}")
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise BadCases(f"{path}: {e}")
    program = path.name[: -len(SUFFIX)]
    if not isinstance(data, dict) or set(data) != {"program", "cases"}:
        raise BadCases(f"{path}: expected {{\"program\": ..., \"cases\": [...]}}")
    if data["program"] != program:
        raise BadCases(f"{path}: program must be {program!r}, got {data['program']!r}")
    cases = data["cases"]
    if not isinstance(cases, list) or not cases:
        raise BadCases(f"{path}: 'cases' must be a non-empty list")
    for n, case in enumerate(cases, 1):
        if not isinstance(case, dict) or set(case) - {"args", "expect", "why"}:
            raise BadCases(f"{path}: case {n}: keys are args, expect, why")
        args = case.get("args")
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            raise BadCases(f"{path}: case {n}: 'args' must be a list of strings")
        if case.get("expect") not in TOKENS:
            raise BadCases(f"{path}: case {n}: 'expect' must be one of {', '.join(TOKENS)}")
    return path.parent / program, cases


def run(path):
    program, cases = load(path)
    if not program.is_file():
        raise BadCases(f"{path}: program {program} not found")
    failed = 0
    for n, case in enumerate(cases, 1):
        try:
            r = subprocess.run([str(program), *case["args"]], capture_output=True,
                               cwd=program.parent, timeout=30)
            got = r.stdout.decode("utf-8", "replace").splitlines()
            ok = r.returncode == 0 and got == [case["expect"]]
            detail = f"exit {r.returncode}, stdout {got!r}"
        except (OSError, subprocess.TimeoutExpired) as e:
            ok, detail = False, f"{type(e).__name__}: {e}"
        why = f" ({case['why']})" if case.get("why") else ""
        if ok:
            print(f"ok   {program.name} #{n} {case['expect']}{why}")
        else:
            failed += 1
            print(f"FAIL {program.name} #{n} expected {case['expect']}, got {detail}{why}")
    return failed, len(cases)


def main(argv):
    paths = [Path(a) for a in argv] or sorted((ROOT / "examples" / "safety").glob("*" + SUFFIX))
    if not paths:
        print("no cases files found", file=sys.stderr)
        return 2
    failed = total = 0
    try:
        for path in paths:
            f, t = run(path)
            failed += f
            total += t
    except BadCases as e:
        print(f"run_safety_cases: error: {e}", file=sys.stderr)
        return 2
    print(f"{total - failed}/{total} cases passed", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
