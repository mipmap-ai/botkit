import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import public_safety_scan as scan  # noqa: E402

# Samples are assembled at runtime so this file itself stays clean.
AT, DOT = "@", "."
SAMPLES = {
    "email": "mail " + "someone" + AT + "example" + DOT + "org",
    "phone": "call " + "+1 " + "415 555 " + "0100",
    "ipv4": "host " + DOT.join(["10", "0", "0", "12"]),
    "home path": "see " + "/" + "home" + "/" + "someone/notes",
    "github token": "ghp" + "_" + "a1B2" * 9,
    "aws key": "AK" + "IA" + "ABCDEFGHIJKLMNOP",
    "private key": "-----BEGIN " + "RSA PRIVATE KEY-----",
    "api key": "sk" + "-" + "abcdEFGH1234" * 2,
    "secret assignment": "api_key" + " = " + '"' + "zz9Yq2Lm8Kp3Xw" + '"',
}
EXTRA_SAMPLES = [
    ("phone", "text me at " + "415" + "555" + "0123"),
    ("phone", "call " + "1" + "212" + "555" + "0199" + " today"),
    ("bearer token", "Authorization" + ": Bearer " + "abc123DEF456ghi789"),
    ("bearer token", "curl -H 'authorization: bearer " + "x9" * 12 + "'"),
    ("secret assignment", "TOKEN" + "=" + "deadbeef" * 4),
    ("secret assignment", "export API_SECRET" + "=" + "U2VjcmV0" * 4 + "=="),
    ("secret assignment", "db_pass" + " = " + "a1b2c3d4e5f6a7b8c9d0e1f2"),
]
EXTRA_CLEAN = [
    "id 1234567890123",
    "run 38145337037",
    "sha e3b5c0e48a5318a6efeeec7c105ec150610711b9",
    "MODE=production_deployment_settings",
    "the bearer of bad news",
    "python -m unittest discover -s tests -v",
]
CLEAN = [
    "uses: actions/checkout" + AT + "v4",
    "python-version: ['3.10', '3.11', '3.12', '3.13']",
    "Schedule: `44 8 * * 1-5`",
    "- inbound-check --from {sender} --text {message}",
    "version 0.1.0",
]


class ScanTest(unittest.TestCase):
    def test_detects_samples(self):
        for kind, text in SAMPLES.items():
            with self.subTest(kind):
                kinds = [k for _, k, _ in scan.scan_text(text)]
                self.assertIn(kind, kinds)

    def test_detects_extra_samples(self):
        for kind, text in EXTRA_SAMPLES:
            with self.subTest(text):
                self.assertIn(kind, [k for _, k, _ in scan.scan_text(text)])

    def test_ignores_clean_lines(self):
        for text in CLEAN + EXTRA_CLEAN:
            with self.subTest(text):
                self.assertEqual(scan.scan_text(text), [])

    @unittest.skipUnless(shutil.which("git") and (ROOT / ".git").exists(), "needs a git checkout")
    def test_repo_is_clean(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "public_safety_scan.py")],
                           capture_output=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stdout.decode())


if __name__ == "__main__":
    unittest.main()
