import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts" / "run_safety_cases.py"
SAFETY = ROOT / "examples" / "safety"


def runner(*args):
    return subprocess.run([sys.executable, str(RUNNER), *map(str, args)], capture_output=True)


class SafetyCasesTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        for name in ("inbound-check", "inbound-check.json"):
            shutil.copy2(SAFETY / name, self.dir / name)

    def write_cases(self, data, name="inbound-check.cases.json"):
        path = self.dir / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_shipped_cases_pass(self):
        r = runner()
        self.assertEqual(r.returncode, 0, r.stdout.decode())
        out = r.stdout.decode().splitlines()
        cases = json.loads((SAFETY / "inbound-check.cases.json").read_text(encoding="utf-8"))["cases"]
        self.assertEqual(len(out), len(cases))
        self.assertTrue(all(line.startswith("ok   inbound-check #") for line in out))
        self.assertEqual({c["expect"] for c in cases}, {"ALLOW", "NEEDS_HUMAN", "IGNORE"})

    def test_wrong_expectation_fails(self):
        path = self.write_cases({"program": "inbound-check", "cases": [
            {"args": ["--from", "owner", "--text", "hi"], "expect": "ALLOW"},
            {"args": ["--from", "stranger", "--text", "hi"], "expect": "ALLOW", "why": "wrong on purpose"},
        ]})
        r = runner(path)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL inbound-check #2 expected ALLOW", r.stdout.decode())
        self.assertIn("1/2 cases passed", r.stderr.decode())

    def test_config_change_is_caught(self):
        path = self.write_cases({"program": "inbound-check", "cases": [
            {"args": ["--from", "owner", "--text", "hi"], "expect": "ALLOW"}]})
        self.assertEqual(runner(path).returncode, 0)
        (self.dir / "inbound-check.json").write_text('{"allow": []}', encoding="utf-8")
        self.assertEqual(runner(path).returncode, 1)

    def test_bad_cases_files(self):
        cases = [
            ({"program": "other", "cases": [{"args": [], "expect": "ALLOW"}]}, "program must be"),
            ({"program": "inbound-check", "cases": []}, "non-empty"),
            ({"program": "inbound-check", "cases": [{"args": "x", "expect": "ALLOW"}]}, "'args'"),
            ({"program": "inbound-check", "cases": [{"args": [], "expect": "OK"}]}, "'expect'"),
            ({"program": "inbound-check", "cases": [{"args": [], "expect": "ALLOW", "x": 1}]}, "keys are"),
        ]
        for data, needle in cases:
            with self.subTest(needle=needle):
                r = runner(self.write_cases(data))
                self.assertEqual(r.returncode, 2)
                self.assertIn(needle, r.stderr.decode())
        r = runner(self.write_cases({"program": "x", "cases": []}, name="x.json"))
        self.assertEqual(r.returncode, 2)
        self.assertIn(".cases.json", r.stderr.decode())

    def test_missing_program(self):
        os.unlink(self.dir / "inbound-check")
        r = runner(self.write_cases({"program": "inbound-check", "cases": [
            {"args": [], "expect": "NEEDS_HUMAN"}]}))
        self.assertEqual(r.returncode, 2)
        self.assertIn("not found", r.stderr.decode())


if __name__ == "__main__":
    unittest.main()
