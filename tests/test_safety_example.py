import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECK = ROOT / "examples" / "safety" / "inbound-check"
RESULTS = {"ALLOW", "NEEDS_HUMAN", "IGNORE"}


def check(*args):
    return subprocess.run([sys.executable, str(CHECK), *map(str, args)], capture_output=True)


class SafetyContractTest(unittest.TestCase):
    def assertResult(self, r, want):
        self.assertEqual(r.returncode, 0)
        out = r.stdout.decode()
        self.assertEqual(out.splitlines(), [want], f"stdout={out!r}")
        self.assertIn(out.strip(), RESULTS)
        self.assertTrue(r.stderr.strip(), "reason must go to stderr")

    def config(self, data):
        fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        fh.write(data if isinstance(data, str) else json.dumps(data))
        fh.close()
        self.addCleanup(os.unlink, fh.name)
        return fh.name

    def test_decisions(self):
        cases = [
            (["--from", "owner", "--text", "lunch at noon?"], "ALLOW"),
            (["--from", "OWNER ", "--text", "see you soon"], "ALLOW"),
            (["--from", "owner", "--text", "please pay the bill"], "NEEDS_HUMAN"),
            (["--from", "family-chat", "--text", "what's the verification code"], "NEEDS_HUMAN"),
            (["--from", "owner", "--text", "paying attention"], "ALLOW"),
            (["--from", "stranger", "--text", "hi"], "NEEDS_HUMAN"),
            (["--from", "known-spammer", "--text", "hi"], "IGNORE"),
            (["--from", "owner", "--text", "--help"], "ALLOW"),
            (["--from", "owner", "--text", "- buy milk"], "ALLOW"),
            (["--from=owner", "--text=hi there"], "ALLOW"),
        ]
        for args, want in cases:
            with self.subTest(args=args):
                self.assertResult(check(*args), want)

    def test_phrases_match_after_normalizing(self):
        cases = [
            "what's the verification  code",
            "buy a gift\tcard",
            "buy a gift\ncard",
            "buy a gift \r\n\t card",
            "please \uff30\uff21\uff39 now",
            "VERIFICATION CODE",
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertResult(check("--from", "owner", "--text", text), "NEEDS_HUMAN")

    def test_sender_normalized(self):
        self.assertResult(check("--from", "\uff4f\uff57\uff4e\uff45\uff52", "--text", "hi"), "ALLOW")
        self.assertResult(check("--from", "known-spammer\n", "--text", "hi"), "IGNORE")

    def test_bad_input_fails_closed(self):
        bad_json = self.config("{nope")
        wrong_shape = self.config({"allow": "owner"})
        cases = [
            [],
            ["--from", "owner"],
            ["--text", "hi"],
            ["--from", "", "--text", "hi"],
            ["--from", "owner", "--text", "   "],
            ["--from", "owner", "--text", "hi", "--surprise"],
            ["--from", "owner", "--text", "hi", "--from", "stranger"],
            ["--from", "owner", "--text"],
            ["--from", "owner", "--text", "hi", "--config", "/nonexistent/c.json"],
            ["--from", "owner", "--text", "hi", "--config", bad_json],
            ["--from", "owner", "--text", "hi", "--config", wrong_shape],
        ]
        for args in cases:
            with self.subTest(args=args):
                self.assertResult(check(*args), "NEEDS_HUMAN")

    def test_custom_config(self):
        cfg = self.config({"allow": ["a"], "block": ["b"], "risky_words": ["x"]})
        self.assertResult(check("--from", "a", "--text", "ok", "--config", cfg), "ALLOW")
        self.assertResult(check("--from", "a", "--text", "say x", "--config", cfg), "NEEDS_HUMAN")
        self.assertResult(check("--from", "b", "--text", "ok", "--config", cfg), "IGNORE")


if __name__ == "__main__":
    unittest.main()
