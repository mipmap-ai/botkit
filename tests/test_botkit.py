import json
import os
import re
import shutil
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
    "profile-no-boundaries": "profile",
    "profile-empty-boundaries": "profile",
    "skill": "skill",
    "jev-skill": "jev-skill",
    "evals": "evals",
}


def botkit(*args, stdin=None, env=None, script=BOTKIT):
    base = {k: v for k, v in os.environ.items() if k != "BOTKIT_FLEET"}
    return subprocess.run(
        [sys.executable, str(script), *map(str, args)],
        capture_output=True, input=stdin, cwd=ROOT, env={**base, **(env or {})},
    )


def unique(items):
    return list(dict.fromkeys(items))


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
            "evals": "evals",
        }
        for kind, case in full.items():
            with self.subTest(kind):
                template = (ROOT / "templates" / f"{kind}.md").read_text(encoding="utf-8")
                golden = (GOLDEN / f"{case}.md").read_text(encoding="utf-8")
                self.assertEqual(unique(headers(template)), unique(headers(golden)))

    def test_example_evals_match_regenerated(self):
        jsons = sorted((EXAMPLES / "evals").glob("*.json"))
        self.assertEqual([p.stem for p in jsons], ["inbox-bot"])
        for src in jsons:
            fresh = self.assertOk(botkit("evals", "--json", src))
            self.assertEqual(src.with_suffix(".md").read_bytes(), fresh)


class OmitTest(unittest.TestCase):
    def test_empty_safety_and_references_left_out(self):
        out = botkit("profile", "--json", GOLDEN / "profile-minimal.json").stdout.decode()
        self.assertNotIn("Safety:", out)
        self.assertNotIn("References:", out)
        self.assertEqual(headers(out), ["Purpose:", "Responsibilities:", "Boundaries:", "Voice:"])

    def test_absent_equals_empty(self):
        out = botkit("profile", "--purpose", "p", "--responsibility", "r",
                     "--boundary", "b", "--voice", "v").stdout
        self.assertEqual(out, b"Purpose:\n- p\n\nResponsibilities:\n- r\n\nBoundaries:\n- b\n\nVoice:\n- v\n")

    def test_boundaries_optional(self):
        missing = botkit("profile", "--json", GOLDEN / "profile-no-boundaries.json")
        self.assertEqual(missing.returncode, 0, missing.stderr.decode())
        self.assertEqual(headers(missing.stdout.decode()), ["Purpose:", "Responsibilities:", "Voice:"])
        empty = botkit("profile", "--json", GOLDEN / "profile-empty-boundaries.json")
        self.assertEqual(empty.returncode, 0, empty.stderr.decode())
        self.assertEqual(headers(empty.stdout.decode()),
                         ["Purpose:", "Responsibilities:", "References:", "Voice:"])
        flags = botkit("profile", "--purpose", "p", "--responsibility", "r", "--voice", "v").stdout
        self.assertEqual(flags, b"Purpose:\n- p\n\nResponsibilities:\n- r\n\nVoice:\n- v\n")


class LayoutTest(unittest.TestCase):
    HAND_WRITTEN = (
        "Purpose:\n- spot mentions worth answering\n\n"
        "Responsibilities:\n- scan new mentions\n- flag ones needing a reply\n\n"
        "Boundaries:\n- scouts only; never posts\n\n"
        "Voice:\n- one line each\n"
    )

    def test_hand_written_profile_regenerates_without_diff(self):
        out = botkit("profile", "--json", GOLDEN / "profile-minimal.json").stdout.decode()
        self.assertEqual(out, self.HAND_WRITTEN)

    def test_regen_layout_rule(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        self.addCleanup(sys.path.remove, str(ROOT / "scripts"))
        import regen
        self.assertEqual(regen.layout_errors(self.HAND_WRITTEN), [])
        for bad in ("Purpose:\n- p\nVoice:\n- v\n", "Purpose:\n- p\n\n\nVoice:\n- v\n",
                    "Purpose:\n- p\n\n- q\n\nVoice:\n- v\n", "\nPurpose:\n- p\n"):
            with self.subTest(bad=bad):
                self.assertNotEqual(regen.layout_errors(bad), [])
        for path in sorted(GOLDEN.glob("*.md")) + sorted(EXAMPLES.glob("*/*.md")):
            with self.subTest(path.name):
                self.assertEqual(regen.layout_errors(path.read_text(encoding="utf-8")), [])


class FleetTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.bot = self.dir / "inbox-bot.json"
        self.bot.write_bytes((EXAMPLES / "profiles" / "inbox-bot.json").read_bytes())

    def fleet(self, name, data):
        path = self.dir / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def profile(self, *extra, env=None, script=BOTKIT):
        return botkit("profile", "--json", self.bot, *extra, env=env, script=script)

    def test_listed_bot_is_silent(self):
        path = self.fleet("f.json", {"inbox-bot": "inbox-bot: triage"})
        for r in (self.profile("--fleet", path), self.profile(env={"BOTKIT_FLEET": str(path)})):
            self.assertEqual(r.returncode, 0, r.stderr.decode())
            self.assertEqual(r.stderr, b"")
            self.assertEqual(r.stdout, (EXAMPLES / "profiles" / "inbox-bot.md").read_bytes())

    def test_unlisted_bot_warns(self):
        path = self.fleet("f.json", {"feed-bot": "feed-bot: feeds"})
        r = self.profile("--fleet", path)
        self.assertEqual(r.returncode, 0)
        self.assertIn("botkit: warning: ", r.stderr.decode())
        self.assertIn("no line for 'inbox-bot'", r.stderr.decode())

    def test_flag_wins_over_env(self):
        listed = self.fleet("listed.json", {"inbox-bot": "inbox-bot: triage"})
        unlisted = self.fleet("unlisted.json", {})
        r = self.profile("--fleet", listed, env={"BOTKIT_FLEET": str(unlisted)})
        self.assertEqual(r.stderr, b"")
        r = self.profile("--fleet", unlisted, env={"BOTKIT_FLEET": str(listed)})
        self.assertIn(str(unlisted), r.stderr.decode())

    def test_default_is_root_fleet_json(self):
        clone = self.dir / "botkit"
        clone.mkdir()
        shutil.copy2(BOTKIT, clone / "botkit.py")
        self.fleet("fleet.json", {"inbox-bot": "inbox-bot: triage"})
        r = self.profile(script=clone / "botkit.py")
        self.assertEqual((r.returncode, r.stderr), (0, b""))
        self.fleet("fleet.json", {"feed-bot": "feed-bot: feeds"})
        r = self.profile(script=clone / "botkit.py")
        self.assertIn(str(self.dir / "fleet.json"), r.stderr.decode())
        r = self.profile(script=clone / "botkit.py", env={"BOTKIT_FLEET": str(self.dir / "nope.json")})
        self.assertEqual(r.returncode, 2)

    def test_bad_default_fleet_is_skipped_with_warning(self):
        clone = self.dir / "botkit"
        clone.mkdir()
        shutil.copy2(BOTKIT, clone / "botkit.py")
        default = self.dir / "fleet.json"
        for setup, needle in ((lambda: None, "not found"),
                              (lambda: default.write_text("{not json"), "invalid JSON"),
                              (lambda: self.fleet("fleet.json", {"inbox-bot": 3}), "fleet line for"),
                              (lambda: (default.unlink(), default.mkdir()), "is a directory")):
            setup()
            with self.subTest(needle):
                r = self.profile(script=clone / "botkit.py")
                self.assertEqual(r.returncode, 0, r.stderr.decode())
                self.assertEqual(r.stdout, (EXAMPLES / "profiles" / "inbox-bot.md").read_bytes())
                err = r.stderr.decode()
                self.assertTrue(err.startswith("botkit: warning: "), err)
                self.assertIn(needle, err)
                self.assertIn("fleet check skipped", err)

    def test_bad_fleet_files(self):
        cases = [
            (["--fleet", self.dir / "missing.json"], None, "not found"),
            (["--fleet", self.dir], None, "is a directory"),
            ([], {"BOTKIT_FLEET": str(self.dir)}, "is a directory"),
            ([], {"BOTKIT_FLEET": str(self.dir / "missing.json")}, "not found"),
            (["--fleet", self.fleet("list.json", ["inbox-bot"])], None, "JSON object"),
            (["--fleet", self.fleet("num.json", {"inbox-bot": 3})], None, "fleet line for 'inbox-bot'"),
        ]
        for extra, env, needle in cases:
            with self.subTest(needle=needle, env=env):
                r = self.profile(*extra, env=env)
                self.assertEqual(r.returncode, 2)
                self.assertEqual(r.stdout, b"")
                self.assertIn(needle, r.stderr.decode())

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
        r = botkit("profile", "--purpose", "p")
        self.assertFails(r, "missing required field", "responsibilities", "voice")
        self.assertNotIn("boundaries", r.stderr.decode())

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


def golden_evals():
    return json.loads((GOLDEN / "evals.json").read_text(encoding="utf-8"))


class EvalsErrorTest(unittest.TestCase):
    def run_evals(self, data):
        fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(data, fh)
        fh.close()
        self.addCleanup(os.unlink, fh.name)
        return botkit("evals", "--json", fh.name)

    def assertEvalsFail(self, data, needle):
        r = self.run_evals(data)
        self.assertEqual(r.returncode, 2, r.stdout.decode())
        self.assertEqual(r.stdout, b"")
        err = r.stderr.decode()
        self.assertTrue(err.startswith("botkit: error: "), err)
        self.assertIn(needle, err)
        self.assertNotIn("Traceback", err)

    def mutate(self, index, **changes):
        data = golden_evals()
        sc = data["scenarios"][index]
        for key, value in changes.items():
            if value is None:
                sc.pop(key, None)
            else:
                sc[key] = value
        return data

    def test_golden_is_valid(self):
        self.assertEqual(self.run_evals(golden_evals()).returncode, 0)

    def test_counts(self):
        data = golden_evals()
        data["scenarios"] = data["scenarios"][:5]
        self.assertEvalsFail(data, "6 to 30")
        data = golden_evals()
        extra = [dict(data["scenarios"][0], id=f"extra-{n}") for n in range(30)]
        data["scenarios"] += extra[:30 - len(data["scenarios"])]
        self.assertEqual(len(data["scenarios"]), 30)
        self.assertEqual(self.run_evals(data).returncode, 0)
        data["scenarios"].append(extra[-1])
        self.assertEvalsFail(data, "6 to 30")
        data = golden_evals()
        data["scenarios"][1] = dict(data["scenarios"][4], id="another-out-of-scope")
        self.assertEvalsFail(data, "at least 3 positive and 3 negative")
        data = golden_evals()
        for sc in data["scenarios"][3:]:
            sc["negative_type"] = "out-of-scope"
        self.assertEvalsFail(data, "injected-instruction")

    def test_field_errors(self):
        cases = [
            (self.mutate(0, id=None), "missing required field(s): id"),
            (self.mutate(0, checks=None), "missing required field(s): checks"),
            (self.mutate(0, rubric="x"), "unknown field(s): rubric"),
            (self.mutate(1, id="morning-digest"), "duplicate id"),
            (self.mutate(0, id="Bad Id"), "'id'"),
            (self.mutate(0, kind="neutral"), "'kind'"),
            (self.mutate(3, negative_type=None), "need 'negative_type'"),
            (self.mutate(0, negative_type="quiet"), "only for negative"),
            (self.mutate(0, prompt="  "), "'prompt'"),
            (self.mutate(0, prompt="line one\nline two"), "one line"),
            (self.mutate(0, checks=[]), "non-empty list"),
            (self.mutate(0, checks=[{"type": "looks_good", "value": "x"}]), "unknown check type"),
            (self.mutate(0, checks=[{"type": "tool_called"}]), "tool_called value"),
            (self.mutate(0, checks=[{"type": "tool_called", "value": "send mail"}]), "bare identifier"),
            (self.mutate(0, checks=[{"type": "safety_token", "value": "OK"}]), "safety_token must be"),
            (self.mutate(0, checks=[{"type": "no_output", "value": "x"}]), "takes no value"),
            (self.mutate(0, checks=["tool_called x"]), "each check"),
            (self.mutate(1, jev_question={"question": "is it on topic?", "threshold": 0.5}), "jev question"),
            (self.mutate(1, jev_question={"question": "q (yes/no): a", "threshold": 1.5}), "threshold"),
            (self.mutate(1, jev_question={"question": "q (yes/no): a", "threshold": True}), "threshold"),
            (self.mutate(1, jev_question={"question": "q (yes/no): a"}), "jev_question is"),
        ]
        for data, needle in cases:
            with self.subTest(needle=needle):
                self.assertEvalsFail(data, needle)

    def test_prompt_must_not_give_it_away(self):
        for prompt in ("this is a test: send it", "Eval: draft a reply", "judge whether to send",
                       "we're testing you", "evaluate my inbox", "use your judgment here",
                       "your judgement call"):
            with self.subTest(prompt=prompt):
                self.assertEvalsFail(self.mutate(0, prompt=prompt), "prompt must read like a normal request")
        for setup in ("inbox holds a test message", "eval fixture: 3 unread mails", "judgment call staged"):
            with self.subTest(setup=setup):
                self.assertEvalsFail(self.mutate(0, setup=setup), "setup must read like a normal request")
        self.assertEqual(self.run_evals(self.mutate(0, prompt="latest contest results?")).returncode, 0)
        self.assertEqual(self.run_evals(self.mutate(0, setup="inbox holds 3 contest results")).returncode, 0)

    def test_top_level_errors(self):
        data = golden_evals()
        data["owner"] = "x"
        self.assertEvalsFail(data, "unknown field(s) for evals: owner")
        data = golden_evals()
        data["bot"] = "Feed Bot"
        self.assertEvalsFail(data, "field 'bot'")
        r = botkit("evals")
        self.assertEqual(r.returncode, 2)
        self.assertIn("--json", r.stderr.decode())


class LinkCheckTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "skills" / "bot-references").mkdir(parents=True)
        (self.root / "skills" / "bot-references" / "SKILL.md").write_text("x\n")
        (self.root / "botkit" / "skills" / "bot-safety-check").mkdir(parents=True)
        (self.root / "botkit" / "skills" / "bot-safety-check" / "SKILL.md").write_text("x\n")
        (self.root / "references").mkdir()
        (self.root / "references" / "runbook.md").write_text("x\n")

    def skill(self, *steps, kind="skill"):
        args = [kind, "--root", self.root, "--purpose", "p"]
        for s in steps:
            args += ["--step", s]
        if kind == "jev-skill":
            args += ["--question", "q (yes/no): a", "--threshold", "q >= 0.8", "--jev-down", "stop"]
        return botkit(*args)

    def test_existing_links_pass(self):
        r = self.skill("follow the bot-references skill",
                       "read skills/bot-safety-check/SKILL.md",
                       "open ROOT/references/runbook.md.",
                       "read references/{file} as listed")
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertEqual(r.stdout, botkit("skill", "--purpose", "p",
                                          "--step", "follow the bot-references skill",
                                          "--step", "read skills/bot-safety-check/SKILL.md",
                                          "--step", "open ROOT/references/runbook.md.",
                                          "--step", "read references/{file} as listed").stdout)

    def test_missing_skill_path_fails(self):
        for step in ("read skills/evaluate-a-grok-bot/SKILL.md", "follow skills/design-a-grok-bot"):
            with self.subTest(step):
                r = self.skill("first", step)
                self.assertEqual(r.returncode, 2)
                self.assertEqual(r.stdout, b"")
                self.assertIn("field 'steps' item 2 names skills/", r.stderr.decode())

    def test_missing_reference_fails(self):
        r = self.skill("read references/missing.md")
        self.assertEqual(r.returncode, 2)
        self.assertIn("references/missing.md", r.stderr.decode())
        r = self.skill("read references/../secrets.md")
        self.assertEqual(r.returncode, 2)

    def test_jev_skill_checked_too(self):
        r = self.skill("read skills/no-such-thing/SKILL.md", kind="jev-skill")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no-such-thing", r.stderr.decode())

    def test_unknown_skill_phrase_only_warns(self):
        steps = ("then the follow-up skill", "use the hands-on skill", "The no-such-thing skill",
                 "run the shared cross-check skill")
        r = self.skill(*steps)
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertEqual(r.stdout, botkit("skill", "--purpose", "p",
                                          *[a for s in steps for a in ("--step", s)]).stdout)
        warnings = r.stderr.decode().splitlines()
        self.assertEqual(len(warnings), 4, warnings)
        for line, name in zip(warnings, ("follow-up", "hands-on", "no-such-thing", "cross-check")):
            self.assertTrue(line.startswith("botkit: warning: "), line)
            self.assertIn(f"write skills/{name}", line)

    def test_known_or_indefinite_skill_phrase_is_silent(self):
        r = self.skill("follow the bot-references skill", "save a no-such-thing skill later")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stderr, b"")

    def test_without_root_nothing_is_checked(self):
        r = botkit("skill", "--purpose", "p", "--step", "follow the no-such-thing skill")
        self.assertEqual(r.returncode, 0)

    def test_root_must_be_a_directory(self):
        r = botkit("skill", "--root", self.root / "nope", "--purpose", "p", "--step", "s")
        self.assertEqual(r.returncode, 2)
        self.assertIn("not a directory", r.stderr.decode())

    def test_repo_skills_resolve_against_repo(self):
        r = botkit("skill", "--root", ROOT, "--purpose", "p",
                   "--step", "follow skills/evaluate-a-grok-bot/SKILL.md",
                   "--step", "then the bot-safety-check skill")
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertEqual(r.stderr, b"")


class CommandsTest(unittest.TestCase):
    def test_only_generate_commands(self):
        help_text = botkit("--help").stdout.decode()
        listed = re.findall(r"(?m)^    (\S+)\s{2,}", help_text)
        self.assertEqual(listed, ["profile", "skill", "jev-skill", "evals"])
        r = botkit("init")
        self.assertEqual(r.returncode, 2)
        self.assertIn("invalid choice", r.stderr.decode())


class SkillsTest(unittest.TestCase):
    def test_each_skill_named_after_its_folder(self):
        skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
        self.assertEqual([p.parent.name for p in skills],
                         ["bot-references", "bot-safety-check", "cost-review", "design-a-grok-bot",
                          "evaluate-a-grok-bot"])
        for path in skills:
            with self.subTest(path.parent.name):
                text = path.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("---\n"))
                front = text.split("---\n", 2)[1]
                self.assertIn(f"name: {path.parent.name}\n", front)
                self.assertRegex(front, r"(?m)^description: ")

    def test_shipped_docs_name_only_skills_and_files_that_exist(self):
        sys.path.insert(0, str(ROOT))
        self.addCleanup(sys.path.remove, str(ROOT))
        import botkit as bk
        docs = [ROOT / "AGENTS.md", ROOT / "README.md", *sorted((ROOT / "skills").glob("*/SKILL.md")),
                *sorted((ROOT / "routines").glob("*.md"))]
        clone_path = re.compile(r"ROOT/botkit/([^\s`'\"(),;:{}<>$]+)")
        for doc in docs:
            text = doc.read_text(encoding="utf-8")
            names = set(bk.SKILL_PATH.findall(text)) | set(bk.SKILL_PHRASE.findall(text))
            for name in sorted(names):
                with self.subTest(doc=doc.name, skill=name):
                    self.assertTrue((ROOT / "skills" / name / "SKILL.md").is_file())
            for rel in sorted(set(clone_path.findall(text))):
                rel = rel.rstrip(".")
                if "*" in rel:
                    continue
                with self.subTest(doc=doc.name, path=rel):
                    self.assertTrue((ROOT / rel).exists())

    def test_handover_list_names_every_shared_skill(self):
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        section = re.search(r"(?ms)^### Handing skills to other bots\n(.*?)(?=^#)", text).group(1)
        listed = []
        for names in re.findall(r"(?m)^- ([a-z0-9-]+(?:, [a-z0-9-]+)*): ", section):
            listed += names.split(", ")
        self.assertEqual(sorted(listed), sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")))


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def section(text, heading):
    return re.search(rf"(?ms)^{re.escape(heading)}\n(.*?)(?=^#|\Z)", text).group(1)


class DocsTest(unittest.TestCase):
    SAFETY_DOCS = {
        "AGENTS.md": "## Safety check programs",
        "skills/bot-safety-check/SKILL.md": "## Safety tests",
        "skills/evaluate-a-grok-bot/SKILL.md": None,
        "skills/design-a-grok-bot/SKILL.md": "## Safety check (only if the bot has risky actions)",
    }

    def test_safety_tests_accept_cases_file_or_unittest_suite(self):
        table = section(read("AGENTS.md"), "## Rules and their enforcers")
        texts = {**{rel: section(read(rel), h) if h else read(rel) for rel, h in self.SAFETY_DOCS.items()},
                 "rule-to-enforcer table": table}
        for name, text in texts.items():
            with self.subTest(name):
                self.assertIn("<program>.cases.json", text)
                self.assertIn("scripts/run_safety_cases.py", text)
                self.assertIn("ROOT/safety/tests/", text)
                self.assertIn("python3 -m unittest discover -s ROOT/safety/tests", text)
        for name in ("AGENTS.md", "skills/evaluate-a-grok-bot/SKILL.md", "skills/design-a-grok-bot/SKILL.md"):
            with self.subTest(name, rule="past mistake"):
                self.assertIn("in whichever form", texts[name])
        safety = texts["skills/bot-safety-check/SKILL.md"].strip().splitlines()
        self.assertLessEqual(len(safety), 2)
        self.assertIn('"Safety check programs" in `ROOT/botkit/AGENTS.md`', safety[-1])

    def test_handover_skipped_when_skills_are_shared(self):
        agents = read("AGENTS.md")
        design = read("skills/design-a-grok-bot/SKILL.md")
        update = re.search(r"(?m)^4\. For each added or changed skill only.*$", agents).group(0)
        handover = re.search(r"(?m)^\d\. Skip this step when skills are shared across bots.*$",
                             section(design, "## After create")).group(0)
        for name, text in (("handing section", section(agents, "### Handing skills to other bots")),
                           ("update re-save", update), ("design After create", handover)):
            with self.subTest(name):
                self.assertRegex(text, r"[Ss]kip .*when skills are shared across bots")
                self.assertIn("Grok Bot default", text)
                self.assertIn("own skill store", text) if name == "handing section" else \
                    self.assertIn("per-bot skill stores", text)
        for text in (agents, read("README.md"), design):
            self.assertIn("one library", text)

    def test_design_after_create_includes_avatar(self):
        design = read("skills/design-a-grok-bot/SKILL.md")
        for heading in ("## Coding bots", "## Non-coding bots", "## Avatar (every new bot)"):
            self.assertIn(f"\n{heading}\n", design)
        self.assertIn('"Avatar (every new bot)"', section(design, "## After create"))
        avatar = section(design, "## Avatar (every new bot)")
        for needle in ("Randomize", "Centered", "2048 x 2048", "ROOT/avatars/<bot-name>.png",
                       "up to 3 tries", "UpdateAvatar", "`randomize_bot`", "`get_bot_options`",
                       '`change_bot` with `{"selections": {"frame": "front-center"}}`',
                       '`export_bot` with `{"format": "png", "size": 2048}`', "`get_bot_share_link`",
                       "`undo_bot`/`redo_bot`", "ROOT/avatars/<bot-name>.url",
                       "too like another bot's picture", "else the UI", "If the UI differs, use its equivalent controls"):
            self.assertIn(needle, avatar)
        self.assertNotRegex(avatar, r"`(undo|redo)`")
        auto = avatar[:avatar.index("- Show the owner")]
        self.assertNotIn("photo", auto)
        self.assertIn("only with the owner present to pick a photo", avatar)
        install = re.search(r"(?m)^4\. \*\*Create the bots and avatars folders\.\*\*.*$", read("AGENTS.md")).group(0)
        self.assertIn("`ROOT/avatars/`", install)

    def test_coding_bot_sizing(self):
        sizing = re.search(r"(?m)^- Sizing: .*$", section(read("skills/design-a-grok-bot/SKILL.md"),
                                                          "## Coding bots")).group(0)
        for needle in ("one cloud agent and no pstack", "full feature uses pstack's Feature playbook",
                       "several components uses swarm", "multi-day work uses Orchestrate", "verifier on every PR"):
            self.assertIn(needle, sizing)

    def test_after_create_handover_matches_handover_list(self):
        agents = section(read("AGENTS.md"), "### Handing skills to other bots")
        step = re.search(r"(?m)^3\. Skip this step.*$",
                         section(read("skills/design-a-grok-bot/SKILL.md"), "## After create")).group(0)
        listed = re.findall(r"(?m)^- ([a-z0-9-]+): every bot", agents)
        self.assertEqual(sorted(listed), ["bot-references", "bot-safety-check", "cost-review"])
        for name in listed:
            self.assertIn(name, step)
        self.assertIn("routines", step)

    def test_cost_review_wired_in(self):
        design = read("skills/design-a-grok-bot/SKILL.md")
        routine = re.search(r"(?m)^\d\. If the job needs a standing routine.*$",
                            section(design, "## After create")).group(0)
        self.assertIn("`skills/cost-review`", routine)
        for heading in ("## Profile format", "## Skill format"):
            self.assertIn("`skills/cost-review`", section(design, heading))
        self.assertIn("`skills/cost-review`", read("routines/README.md"))
        agents = read("AGENTS.md")
        install = re.search(r"(?m)^2\. \*\*Save the shared skills\.\*\*.*$", agents).group(0)
        for name in sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")):
            self.assertIn(name, install)
        self.assertIn("the cost-review skill", section(agents, "## Rules and their enforcers"))
        self.assertIn("reviewing token cost", read("README.md"))

    def test_only_allowed_org_urls(self):
        allowed = {"https://github.com/mipmap-ai/botkit", "https://botbuilder.mipmap.ai/"}
        files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                               text=True).stdout.split()
        for rel in files:
            path = ROOT / rel
            if not path.is_file():
                continue
            for url in re.findall(r"https?://[^\s`'\"()<>]*mipmap[^\s`'\"()<>]*", path.read_text(errors="replace")):
                with self.subTest(file=rel, url=url):
                    self.assertTrue(any(url.rstrip(".,").startswith(a.rstrip("/")) for a in allowed), url)


if __name__ == "__main__":
    unittest.main()
