"""Tests for check.py: a compliant tree has zero errors; every violation reports its own code.

Run:  py -m unittest discover -s <HUB>/tools/tests
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from check import check  # noqa: E402

NOTE = "---\nname: {name}\ndescription: demo\nstatus: active\nupdated: 2026-11-12\n---\n\n# Title\n"


def build(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def good_tree() -> dict[str, str]:
    return {
        "INDEX.md": "# Root\n\n| Content | When to read |\n|---|---|\n| [Area](area/INDEX.md) | always |\n",
        "area/INDEX.md": "# area\n\n- [Note](my-note.md)\n- [Another page](other-note.md)\n- [Sub](sub/INDEX.md)\n- `skill:some-skill`\n\n```markdown\n[Example](not-real.md)\n```\n",
        "area/my-note.md": NOTE.format(name="my-note") + "\nSee [another page](other-note.md)\n",
        "area/other-note.md": NOTE.format(name="other-note"),
        "area/sub/INDEX.md": "# sub\n\n- [Deep](deep-note.md)\n",
        "area/sub/deep-note.md": NOTE.format(name="deep-note"),
    }


class CheckTests(unittest.TestCase):
    def run_check(self, files: dict[str, str]):
        with tempfile.TemporaryDirectory() as tmp:
            build(Path(tmp), files)
            return check(Path(tmp))

    def codes(self, files: dict[str, str]) -> set[str]:
        errors, warnings = self.run_check(files)
        return {line.split()[0] for line in errors + warnings}

    def test_good_tree_is_clean(self):
        errors, warnings = self.run_check(good_tree())
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_orphan(self):
        files = good_tree()
        files["area/lonely.md"] = NOTE.format(name="lonely")
        self.assertIn("E1", self.codes(files))

    def test_note_cannot_lead_downward(self):
        # A file that only a note links to, not any index, is still an orphan.
        files = good_tree()
        files["area/my-note.md"] += "[x](hidden.md)\n"
        files["area/hidden.md"] = NOTE.format(name="hidden")
        self.assertIn("E1", self.codes(files))

    def test_broken_link(self):
        files = good_tree()
        files["area/INDEX.md"] += "- [Missing](missing.md)\n"
        self.assertIn("E2", self.codes(files))

    def test_index_too_long(self):
        files = good_tree()
        files["area/INDEX.md"] += "\n" * 80
        self.assertIn("E3", self.codes(files))

    def test_frontmatter_missing(self):
        files = good_tree()
        files["area/other-note.md"] = "# No frontmatter\n"
        self.assertIn("E4", self.codes(files))

    def test_frontmatter_name_mismatch(self):
        files = good_tree()
        files["area/other-note.md"] = NOTE.format(name="wrong")
        self.assertIn("E4", self.codes(files))

    def test_bad_filename(self):
        files = good_tree()
        files["area/INDEX.md"] += "- [Bad](Bad_Name.md)\n"
        files["area/Bad_Name.md"] = NOTE.format(name="Bad_Name")
        self.assertIn("E5", self.codes(files))

    def test_folder_without_index(self):
        files = good_tree()
        files["area/INDEX.md"] += "- [x](loose/some-note.md)\n"
        files["area/loose/some-note.md"] = NOTE.format(name="some-note")
        self.assertIn("E6", self.codes(files))

    def test_external_link_must_be_registered(self):
        with tempfile.TemporaryDirectory() as outside, tempfile.TemporaryDirectory() as tmp:
            target = Path(outside) / "SKILL.md"
            target.write_text("# skill\n", encoding="utf-8")
            files = good_tree()
            files["area/INDEX.md"] += f"- [External]({target.as_posix()})\n"
            files["INDEX.md"] += "| [Exceptions](EXCEPTIONS.md) | when needed |\n"
            files["EXCEPTIONS.md"] = "# Exceptions\n\nNo paths are registered.\n"
            build(Path(tmp), files)
            errors, _ = check(Path(tmp))
            self.assertTrue(any(e.startswith("E7") for e in errors))
            (Path(tmp) / "EXCEPTIONS.md").write_text(
                f"# Exceptions\n\n- `{outside}` used by a test\n", encoding="utf-8"
            )
            errors, _ = check(Path(tmp))
            self.assertEqual(errors, [])

    def test_cross_domain_link_warns(self):
        files = good_tree()
        files["INDEX.md"] += "| [Elsewhere](else/INDEX.md) | always |\n"
        files["else/INDEX.md"] = "# else\n\n- [a](a-note.md)\n"
        files["else/a-note.md"] = NOTE.format(name="a-note") + "[Cross](../area/my-note.md)\n"
        self.assertIn("W1", self.codes(files))

    def test_legacy_only_needs_indexing(self):
        files = good_tree()
        files["hub.json"] = '{"legacy": ["old/*"]}'
        files["INDEX.md"] += "| [Old](old/Old_Doc.md) | when needed |\n"
        files["old/Old_Doc.md"] = "# Old document\n"
        errors, _ = self.run_check(files)
        self.assertEqual(errors, [])

    def test_skill_folder(self):
        files = good_tree()
        files["area/INDEX.md"] += "- [s](skills/my-skill/SKILL.md)\n"
        files["area/skills/my-skill/SKILL.md"] = "---\nname: my-skill\ndescription: demo\n---\n\nBody\n"
        files["area/skills/my-skill/Helper_Notes.md"] = "companion file without frontmatter\n"
        errors, warnings = self.run_check(files)
        self.assertEqual(errors, [])

    def test_skill_name_mismatch(self):
        files = good_tree()
        files["area/INDEX.md"] += "- [s](skills/my-skill/SKILL.md)\n"
        files["area/skills/my-skill/SKILL.md"] = "---\nname: other\ndescription: demo\n---\n"
        self.assertIn("E4", self.codes(files))

    def test_skill_orphan(self):
        files = good_tree()
        files["area/skills/my-skill/SKILL.md"] = "---\nname: my-skill\ndescription: demo\n---\n"
        self.assertIn("E1", self.codes(files))


if __name__ == "__main__":
    unittest.main()
