#!/usr/bin/env python3
"""Fail if any tracked file looks like it leaks personal or secret data.

Flags email addresses, phone numbers, IP addresses, home-directory paths and
token or key patterns. Scans `git ls-files` output, or every file under the
given paths. Exits 1 with one line per hit, 0 when clean.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PATTERNS = [
    ("email", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"),
    ("phone", r"(?<![\w.])\+\d[\d ().-]{8,}\d(?![\w.])"),
    ("phone", r"(?<![\w.])\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?![\w.])"),
    ("phone", r"(?<![\w.+/-])1?[2-9]\d{2}[2-9]\d{6}(?![\w./-])"),
    ("ipv4", r"(?<![\w.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\w.])"),
    ("ipv6", r"(?<![\w:])(?:[0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4}(?![\w:])"),
    ("ipv6", r"(?<![\w:])(?:[0-9A-Fa-f]{1,4}:){1,6}:[0-9A-Fa-f]{1,4}(?![\w:])"),
    ("home path", r"/(?:home|Users)/[A-Za-z0-9._-]+"),
    ("home path", r"(?i)[A-Z]:\\+Users\\+[A-Za-z0-9._-]+"),
    ("home path", r"(?<![\w/])~[A-Za-z0-9._-]*/"),
    ("home path", r"(?<![\w.])/root(?=/)"),
    ("private key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("github token", r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    ("slack token", r"\bxox[abposr]-[A-Za-z0-9-]{10,}"),
    ("aws key", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ("google key", r"\bAIza[0-9A-Za-z_-]{35}\b"),
    ("api key", r"\bsk-(?:[A-Za-z0-9_-]+-)?[A-Za-z0-9]{20,}"),
    ("jwt", r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ("secret assignment",
     r"(?i)\b(?:api[_-]?key|secret|token|passwd|password|auth)\b[\"']?\s*[:=]\s*[\"'][^\"'\s{}<>]{12,}[\"']"),
    ("bearer token", r"(?i)\bauthorization\s*[:=]\s*[\"']?bearer\s+[A-Za-z0-9._~+/-]{8,}=*"),
    ("bearer token", r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{20,}=*"),
    # Unquoted NAME=value: the value must look like hex, padded base64, or a
    # mixed-case token with a digit, so plain snake_case identifiers don't match.
    ("secret assignment",
     r"\b[A-Za-z_][A-Za-z0-9_]*\s*=\s*(?:[0-9a-fA-F]{24,}"
     r"|[A-Za-z0-9+/]{20,}={1,2}"
     r"|(?=[\w+/-]*\d)(?=[\w+/-]*[a-z])(?=[\w+/-]*[A-Z])[A-Za-z0-9+/_-]{24,})(?![\w+/=(.-])"),
    ("secret assignment",
     r"(?i)\b(?:[a-z0-9_-]*[_-])?(?:token|secret|password|passwd|api[_-]?key|key)\s*:\s*"
     r"(?=[A-Za-z0-9+/_.=-]*\d)(?=[A-Za-z0-9+/_.=-]*[A-Za-z])[A-Za-z0-9+/_.=-]{16,}(?![^\s#])"),
    ("url credentials", r"[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]+@"),
]
COMPILED = [(name, re.compile(rx)) for name, rx in PATTERNS]


def scan_text(text):
    """Return [(line_no, kind, match)] for every hit in text."""
    hits = []
    for no, line in enumerate(text.splitlines(), 1):
        for name, rx in COMPILED:
            for m in rx.finditer(line):
                hits.append((no, name, m.group(0)))
    return hits


def tracked_files():
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    ).stdout.decode("utf-8")
    return [ROOT / p for p in out.split("\0") if p]


def walk(paths):
    for p in map(Path, paths):
        if p.is_dir():
            yield from sorted(f for f in p.rglob("*") if f.is_file() and ".git" not in f.parts)
        else:
            yield p


def main(argv):
    files = list(walk(argv)) if argv else tracked_files()
    found = 0
    for path in files:
        try:
            text = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            print(f"{path}: not UTF-8 text; binary files are not allowed")
            found += 1
            continue
        for no, kind, match in scan_text(text):
            print(f"{path}:{no}: {kind}: {match}")
            found += 1
    if found:
        print(f"public-safety scan: {found} hit(s)", file=sys.stderr)
        return 1
    print(f"public-safety scan: {len(files)} file(s) clean", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
