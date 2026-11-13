"""Tests for link_skills.py and check.py's link checks. They really create temporary junctions with mklink /J.

Run:  py -m unittest discover -s <HUB>/tools/tests
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check  # noqa: E402
import link_skills  # noqa: E402

SKILL_MD = "---\nname: {name}\ndescription: demo\n---\n\nBody\n"


def make_junction(link: Path, target: Path) -> None:
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"failed to create junction: {link} -> {target}")


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.hub = self.root / "hub"
        self.links = self.root / "links"
        self.hub.mkdir()
        self.links.mkdir()

    def tearDown(self):
        if self.links.is_dir():
            for entry in list(self.links.iterdir()):
                if os.path.isjunction(entry):
                    os.rmdir(entry)
        self.tmp.cleanup()

    def make_skill(self, name: str, domain: str = "agent-ops") -> Path:
        d = self.hub / "global" / domain / "skills" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(SKILL_MD.format(name=name), encoding="utf-8")
        return d

    def write_config(self, ignore=None) -> None:
        cfg = {"skill_links": str(self.links)}
        if ignore is not None:
            cfg["skill_links_ignore"] = ignore
        (self.hub / "hub.json").write_text(
            json.dumps(cfg, ensure_ascii=False), encoding="utf-8"
        )

    def run_link(self, **kwargs):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = link_skills.run(self.hub, **kwargs)
        return code, buf.getvalue()

    def test_missing_link_is_created(self):
        target = self.make_skill("demo-skill")
        self.write_config()
        code, out = self.run_link()
        link = self.links / "demo-skill"
        self.assertEqual(code, 0)
        self.assertTrue(os.path.isjunction(link))
        self.assertEqual(
            link_skills.junction_target(link), link_skills.norm(target.resolve())
        )
        self.assertIn("created 1", out)

    def test_existing_correct_link_not_rebuilt(self):
        target = self.make_skill("demo-skill")
        self.write_config()
        make_junction(self.links / "demo-skill", target)
        plan = link_skills.plan_links(self.hub, self.links, [])
        self.assertEqual([i.name for i in plan.ok], ["demo-skill"])
        self.assertEqual(plan.missing, [])
        with mock.patch.object(link_skills.subprocess, "run") as run:
            code, out = self.run_link()
        run.assert_not_called()
        self.assertEqual(code, 0)
        self.assertIn("created 0", out)
        self.assertIn("existing 1", out)

    def test_real_folder_conflict(self):
        self.make_skill("demo-skill")
        self.write_config()
        (self.links / "demo-skill").mkdir()
        code, out = self.run_link()
        self.assertEqual(code, 1)
        self.assertIn("conflict", out)
        self.assertFalse(os.path.isjunction(self.links / "demo-skill"))
        self.assertTrue((self.links / "demo-skill").is_dir())

    def test_junction_to_elsewhere_conflict(self):
        self.make_skill("demo-skill")
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        self.write_config()
        make_junction(self.links / "demo-skill", elsewhere)
        code, out = self.run_link()
        self.assertEqual(code, 1)
        self.assertIn("conflict", out)
        self.assertEqual(
            link_skills.junction_target(self.links / "demo-skill"),
            link_skills.norm(elsewhere),
        )

    def test_dangling_junction_removed(self):
        target = self.make_skill("gone-skill")
        self.write_config()
        link = self.links / "gone-skill"
        make_junction(link, target)
        shutil.rmtree(target)
        keep = self.hub / "keep.txt"
        keep.write_text("intact", encoding="utf-8")
        code, out = self.run_link()
        self.assertEqual(code, 0)
        self.assertIn("removed 1", out)
        self.assertFalse(os.path.isjunction(link))
        self.assertFalse(link.exists())
        self.assertTrue(keep.exists())

    def test_outside_junction_untouched(self):
        outside = self.root / "outside"
        outside.mkdir()
        link = self.links / "external-link"
        make_junction(link, outside)
        self.write_config()
        code, out = self.run_link()
        self.assertEqual(code, 0)
        self.assertNotIn("external-link", out)
        self.assertTrue(os.path.isjunction(link))
        self.assertEqual(link_skills.junction_target(link), link_skills.norm(outside))

    def test_ignore_and_unmanaged(self):
        self.make_skill("demo-skill")
        (self.links / "synced").mkdir()
        (self.links / ".trash").mkdir()
        (self.links / "notes").mkdir()
        self.write_config()
        code, out = self.run_link()
        self.assertEqual(code, 0)
        self.assertIn("unmanaged 1", out)
        self.assertIn("notes", out)
        self.assertNotIn("synced", out)
        self.assertNotIn(".trash", out)

    def test_dry_run_changes_nothing(self):
        self.make_skill("demo-skill")
        self.write_config()
        code, out = self.run_link(dry_run=True)
        self.assertEqual(code, 0)
        self.assertIn("would create", out)
        self.assertFalse((self.links / "demo-skill").exists())

    def test_dry_run_keeps_dangling_junction(self):
        target = self.make_skill("gone-skill")
        self.write_config()
        link = self.links / "gone-skill"
        make_junction(link, target)
        shutil.rmtree(target)
        code, out = self.run_link(dry_run=True)
        self.assertEqual(code, 0)
        self.assertIn("would remove dangling junction", out)
        self.assertTrue(os.path.isjunction(link))

    def test_check_reports_e8_and_w4(self):
        self.make_skill("demo-skill")
        self.write_config()
        errors, warnings = check.check(self.hub)
        self.assertTrue(any(e.startswith("E8") and "demo-skill" in e for e in errors))
        self.assertTrue(any("link_skills.py" in e for e in errors))

        (self.links / "stray").mkdir()
        errors, warnings = check.check(self.hub)
        self.assertTrue(any(w.startswith("W4") and "stray" in w for w in warnings))

    def test_check_without_skill_links_key_ignores_links(self):
        self.make_skill("demo-skill")
        (self.links / "stray").mkdir()
        (self.hub / "hub.json").write_text("{}", encoding="utf-8")
        errors, warnings = check.check(self.hub)
        self.assertFalse(any(e.startswith("E8") for e in errors))
        self.assertFalse(any(w.startswith("W4") for w in warnings))


if __name__ == "__main__":
    unittest.main()
