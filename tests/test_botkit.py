import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOTKIT = ROOT / "botkit.py"
GOLDEN = ROOT / "tests" / "golden"
EXAMPLES = ROOT / "examples"

GOLDEN_CASES = {
    "profile-full": "profile",
    "profile-minimal": "profile",
    "skill": "skill",
    "jev-skill": "jev-skill",
}


def botkit(*args, stdin=None):
    return subprocess.run(
        [sys.executable, str(BOTKIT), *map(str, args)],
        capture_output=True, input=stdin, cwd=ROOT,
    )


def headers(text):
    return [line for line in text.splitlines() if re.match(r"^[A-Z][A-Za-z]*:$", line)]


class GenerateTest(unittest.TestCase):
    def assertOk(self, r):
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        return r.stdout

    def test_golden_files_byte_identical_across_runs(self):
        for name, kind in GOLDEN_CASES.items():
            with self.subTest(name):
                first = self.assertOk(botkit(kind, "--json", GOLDEN / f"{name}.json"))
                second = self.assertOk(botkit(kind, "--json", GOLDEN / f"{name}.json"))
                self.assertEqual(first, second)
                self.assertEqual(first, (GOLDEN / f"{name}.md").read_bytes())
                self.assertNotIn(b"\r", first)
                self.assertTrue(first.endswith(b"\n") and not first.endswith(b"\n\n"))

    def test_flags_match_json(self):
        data = json.loads((GOLDEN / "profile-full.json").read_text(encoding="utf-8"))
        args = ["profile"]
        flag = {"responsibilities": "--responsibility", "boundaries": "--boundary",
                "references": "--reference"}
        for key, values in data.items():
            for v in values:
                args += [flag.get(key, f"--{key}"), v]
        self.assertEqual(self.assertOk(botkit(*args)), (GOLDEN / "profile-full.md").read_bytes())

    def test_jev_skill_flags_match_json(self):
        data = json.loads((GOLDEN / "jev-skill.json").read_text(encoding="utf-8"))
        flag = {"questions": "--question", "steps": "--step", "thresholds": "--threshold",
                "jev_down": "--jev-down"}
        args = ["jev-skill"]
        for key, values in data.items():
            for v in [values] if isinstance(values, str) else values:
                args += [flag.get(key, f"--{key}"), v]
        self.assertEqual(self.assertOk(botkit(*args)), (GOLDEN / "jev-skill.md").read_bytes())

    def test_json_from_stdin(self):
        src = (GOLDEN / "skill.json").read_bytes()
        self.assertEqual(self.assertOk(botkit("skill", "--json", "-", stdin=src)),
                         (GOLDEN / "skill.md").read_bytes())

    def test_out_file(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "p.md"
            self.assertOk(botkit("profile", "--json", GOLDEN / "profile-full.json", "-o", out))
            self.assertEqual(out.read_bytes(), (GOLDEN / "profile-full.md").read_bytes())

    def test_example_profiles_match_regenerated(self):
        jsons = sorted((EXAMPLES / "profiles").glob("*.json"))
        self.assertEqual([p.stem for p in jsons], ["feed-bot", "inbox-bot", "infra-bot"])
        for src in jsons:
            with self.subTest(src.stem):
                fresh = self.assertOk(botkit("profile", "--json", src))
                self.assertEqual(src.with_suffix(".md").read_bytes(), fresh)

    def test_regen_check_clean(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "regen.py"), "--check"],
                           capture_output=True)
        self.assertEqual(r.returncode, 0, r.stdout.decode())

    def test_fleet_example_lists_example_bots(self):
        fleet = json.loads((EXAMPLES / "fleet.example.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(fleet), ["feed-bot", "inbox-bot", "infra-bot"])
        for key, line in fleet.items():
            self.assertTrue(line.startswith(f"{key}: "), line)

    def test_templates_match_generator_sections(self):
        full = {
            "profile": "profile-full",
            "skill": "skill",
            "jev-skill": "jev-skill",
        }
        for kind, case in full.items():
            with self.subTest(kind):
                template = (ROOT / "templates" / f"{kind}.txt").read_text(encoding="utf-8")
                golden = (GOLDEN / f"{case}.md").read_text(encoding="utf-8")
                self.assertEqual(headers(template), headers(golden))


class OmitTest(unittest.TestCase):
    def test_empty_safety_and_references_left_out(self):
        out = botkit("profile", "--json", GOLDEN / "profile-minimal.json").stdout.decode()
        self.assertNotIn("Safety:", out)
        self.assertNotIn("References:", out)
        self.assertEqual(headers(out), ["Purpose:", "Responsibilities:", "Boundaries:", "Voice:"])

    def test_absent_equals_empty(self):
        out = botkit("profile", "--purpose", "p", "--responsibility", "r",
                     "--boundary", "b", "--voice", "v").stdout
        self.assertEqual(out, b"Purpose:\n- p\nResponsibilities:\n- r\nBoundaries:\n- b\nVoice:\n- v\n")

    def test_skill_optional_sections_left_out(self):
        out = botkit("skill", "--purpose", "p", "--step", "s").stdout
        self.assertEqual(out, b"Purpose:\n- p\n\nSteps:\n- 1. s\n")


class ErrorTest(unittest.TestCase):
    def assertFails(self, r, *needles):
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(r.stdout, b"")
        err = r.stderr.decode()
        for n in needles:
            self.assertIn(n, err)

    def json_file(self, data):
        fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(data, fh)
        fh.close()
        self.addCleanup(os.unlink, fh.name)
        return fh.name

    def test_missing_required_flags(self):
        self.assertFails(botkit("profile", "--purpose", "p"),
                         "missing required field", "responsibilities", "boundaries", "voice")

    def test_missing_required_json(self):
        path = self.json_file({"responsibilities": ["r"], "boundaries": ["b"], "voice": ["v"]})
        self.assertFails(botkit("profile", "--json", path), "missing required field", "purpose")

    def test_jev_skill_requires_questions_thresholds_and_jev_down(self):
        self.assertFails(botkit("jev-skill", "--purpose", "p", "--step", "s"),
                         "questions", "thresholds", "jev_down")

    def test_unknown_json_field(self):
        path = self.json_file({"purpose": "p", "responsibilities": "r", "boundaries": "b",
                               "voice": "v", "tools": ["x"]})
        self.assertFails(botkit("profile", "--json", path), "unknown field", "tools")

    def test_unknown_flag(self):
        self.assertFails(botkit("profile", "--purpose", "p", "--tools", "x"), "--tools")

    def test_profile_field_unknown_to_skill(self):
        path = self.json_file({"purpose": "p", "steps": ["s"], "voice": ["v"]})
        self.assertFails(botkit("skill", "--json", path), "unknown field", "voice")

    def test_bad_inputs(self):
        cases = [
            (["profile", "--json", GOLDEN / "skill.json", "--voice", "x"], "not both"),
            (["skill", "--purpose", "a", "--purpose", "b", "--step", "s"], "takes one value"),
            (["skill", "--purpose", "p", "--step", "1. s"], "numbered automatically"),
            (["skill", "--purpose", "p", "--step", "- s"], "leading '- '"),
            (["skill", "--purpose", "p", "--step", "  "], "empty item"),
            (["skill", "--purpose", "p", "--step", "a\nb"], "one line"),
            (["skill", "--purpose", "p", "--step", "s", "--name", "x"], "go together"),
            (["skill", "--purpose", "p", "--step", "s", "--name", "Bad Name",
              "--description", "d"], "lowercase"),
            (["profile", "--purpose", "p", "--responsibility", "r", "--boundary", "b",
              "--voice", "v", "--safety", "../evil --x"], "bare name"),
            (["profile", "--purpose", "p", "--responsibility", "r", "--boundary", "b",
              "--voice", "v", "--reference", "dir/file.md"], "bare name"),
            (["jev-skill", "--purpose", "p", "--step", "s", "--question", "is it good?",
              "--threshold", "t", "--jev-down", "d"], "questions"),
            (["profile", "--json", "/nonexistent/x.json"], "cannot read"),
        ]
        for args, needle in cases:
            with self.subTest(args=args):
                self.assertFails(botkit(*args), needle)

    def test_bad_json(self):
        fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        fh.write("{not json")
        fh.close()
        self.addCleanup(os.unlink, fh.name)
        self.assertFails(botkit("profile", "--json", fh.name), "invalid JSON")
        self.assertFails(botkit("profile", "--json", self.json_file(["purpose"])), "JSON object")
        self.assertFails(botkit("profile", "--json", self.json_file({"purpose": 3})), "string")

    def assertCleanError(self, r, needle):
        self.assertEqual(r.returncode, 2)
        err = r.stderr.decode()
        self.assertTrue(err.startswith("botkit: error: "), err)
        self.assertIn(needle, err)
        self.assertNotIn("Traceback", err)

    def test_non_utf8_json(self):
        fh = tempfile.NamedTemporaryFile("wb", suffix=".json", delete=False)
        fh.write(b'{"purpose": "caf\xe9"}')
        fh.close()
        self.addCleanup(os.unlink, fh.name)
        self.assertCleanError(botkit("profile", "--json", fh.name), "not UTF-8")
        self.assertCleanError(botkit("profile", "--json", "-", stdin=b"\xff\xfe{}"), "not UTF-8")

    def test_out_into_missing_directory(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "missing" / "p.md"
            r = botkit("profile", "--json", GOLDEN / "profile-full.json", "-o", out)
            self.assertCleanError(r, "cannot write")
            self.assertEqual(r.stdout, b"")


def snapshot(root):
    out = {}
    for p in sorted(Path(root).rglob("*")):
        st = p.lstat()
        out[str(p.relative_to(root))] = (
            stat.S_IFMT(st.st_mode), stat.S_IMODE(st.st_mode),
            p.read_bytes() if p.is_file() else None,
        )
    return out


class InitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def init(self, *extra):
        r = botkit("init", "--root", self.root, *extra)
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        return r.stdout.decode()

    def test_fresh_install_layout(self):
        out = self.init()
        skills = self.root / ".cursor" / "skills"
        for name in ("design-a-grok-bot", "bot-safety-check", "bot-references"):
            self.assertEqual((skills / name / "SKILL.md").read_bytes(),
                             (ROOT / "skills" / name / "SKILL.md").read_bytes())
        self.assertEqual((self.root / "fleet.json").read_bytes(),
                         (EXAMPLES / "fleet.example.json").read_bytes())
        check = self.root / "safety" / "inbound-check"
        self.assertEqual(check.read_bytes(), (EXAMPLES / "safety" / "inbound-check").read_bytes())
        if os.name == "posix":
            self.assertTrue(os.access(check, os.X_OK))
        self.assertTrue((self.root / "safety" / "inbound-check.json").is_file())
        self.assertTrue((self.root / "references" / "INDEX.md").is_file())
        self.assertNotIn("skip ", out)
        self.assertIn("Next steps:", out)

    def test_custom_skills_dir(self):
        skills = self.root / "elsewhere"
        self.init("--skills-dir", skills)
        self.assertTrue((skills / "bot-references" / "SKILL.md").is_file())
        self.assertFalse((self.root / ".cursor").exists())

    def test_never_overwrites(self):
        seeded = {
            self.root / "fleet.json": b'{"mine": "mine: keep me"}\n',
            self.root / "safety" / "inbound-check.json": b'{"allow": ["me"]}\n',
            self.root / ".cursor" / "skills" / "bot-references" / "SKILL.md": b"my edits\n",
            self.root / "references" / "INDEX.md": b"my index\n",
        }
        for path, data in seeded.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        out = self.init()
        for path, data in seeded.items():
            self.assertEqual(path.read_bytes(), data)
            self.assertIn(f"skip {path} (exists)\n", out)
        self.assertTrue((self.root / "safety" / "inbound-check").is_file())

        before = snapshot(self.root)
        again = self.init()
        self.assertEqual(snapshot(self.root), before)
        actions = [l for l in again.splitlines() if l.startswith(("create ", "skip "))]
        self.assertTrue(actions)
        self.assertTrue(all(l.startswith("skip ") and l.endswith(" (exists)") for l in actions))

    def test_existing_symlink_is_not_followed(self):
        if not hasattr(os, "symlink"):
            self.skipTest("no symlinks")
        target = self.root / "outside.txt"
        target.write_bytes(b"untouched\n")
        try:
            os.symlink(target, self.root / "fleet.json")
        except OSError:
            self.skipTest("cannot create symlinks")
        out = self.init()
        self.assertIn(f"skip {self.root / 'fleet.json'} (exists)", out)
        self.assertEqual(target.read_bytes(), b"untouched\n")

    @unittest.skipIf(os.name != "posix" or os.geteuid() == 0, "needs a non-root POSIX user")
    def test_read_only_root_errors_cleanly(self):
        self.root.chmod(0o555)
        self.addCleanup(self.root.chmod, 0o755)
        r = botkit("init", "--root", self.root)
        self.assertEqual(r.returncode, 2)
        err = r.stderr.decode()
        self.assertIn("botkit: error: cannot write", err)
        self.assertNotIn("Traceback", err)

    def test_missing_root_errors(self):
        r = botkit("init", "--root", self.root / "nope")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not a directory", r.stderr.decode())


if __name__ == "__main__":
    unittest.main()
