"""Hub structure checker. Standard library only.

Usage:  py check.py --root <hub or project path>
The root needs a hub.json:
  include             files or folders to check (relative to the root)
  skip_dirs           folder names to skip
  legacy              glob patterns for old files: they only need to be indexed,
                      their frontmatter, naming and sub-indexes are not checked
  root_entries        entry files; the walk starts here and follows links downward
  skill_links         optional, the link directory for global skills (e.g. "~/.claude/skills");
                      omit it to skip link checks
  skill_links_ignore  names in the link directory that the hub does not manage,
                      default ["synced", ".trash"]
A folder containing SKILL.md is one skill unit: SKILL.md only needs name (equal to
the folder name) and description, and is linked from the parent index; the folder
does not need an INDEX.md; its other files are companion files and are not checked.
With skill_links configured, a missing, conflicting or dangling junction is reported
as E8, and a folder in the link directory that the hub does not manage is W4.
Exit code is 1 when there are errors.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

SPECIAL = {"INDEX", "AGENTS", "CLAUDE", "PROTOCOL", "EXCEPTIONS", "HANDOFF", "README"}
STATUSES = {"active", "draft", "stale", "有效", "草稿", "过时"}
MAX_INDEX_LINES = 60
MAX_SPECIAL_LINES = 150
MAX_NOTE_LINES = 400
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
FENCE_RE = re.compile(r"^(```|~~~)")
ABS_RE = re.compile(r"^[A-Za-z]:[\\/]")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def strip_code(text: str) -> str:
    """Remove code blocks and inline code so example links in templates are ignored."""
    out, fenced = [], False
    for line in text.splitlines():
        if FENCE_RE.match(line.strip()):
            fenced = not fenced
            continue
        if not fenced:
            out.append(re.sub(r"`[^`]*`", "", line))
    return "\n".join(out)


def links(text: str) -> list[tuple[str, str]]:
    """Return (title, target), ignoring URLs and in-page anchors."""
    found = []
    for title, target in LINK_RE.findall(strip_code(text)):
        if re.match(r"^[a-z]+://", target) or target.startswith(("#", "mailto:")):
            continue
        found.append((title, target.split("#")[0]))
    return found


def frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    data = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return data
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip("\"'")
    return {}


def norm(path: str | Path) -> str:
    return os.path.normcase(os.path.normpath(os.path.expanduser(str(path))))


def load_config(root: Path) -> dict:
    cfg = {
        "include": ["."],
        "skip_dirs": [".git"],
        "legacy": [],
        "root_entries": ["INDEX.md"],
        "skill_links": None,
        "skill_links_ignore": ["synced", ".trash"],
    }
    cfg_path = root / "hub.json"
    if cfg_path.exists():
        cfg.update(json.loads(read(cfg_path)))
    return cfg


def collect(root: Path, cfg: dict) -> list[Path]:
    skip = set(cfg["skip_dirs"]) | {".git"}
    files: set[Path] = set()
    for item in cfg["include"]:
        base = (root / item).resolve()
        if base.is_file():
            files.add(base)
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in skip]
            files.update(Path(dirpath) / f for f in filenames if f.lower().endswith(".md"))
    return sorted(files)


def skill_dir(path: Path, root: Path) -> Path | None:
    """The skill unit folder that contains path (itself or an ancestor with SKILL.md), else None."""
    d = path.parent
    while True:
        if (d / "SKILL.md").exists():
            return d
        if d == root or d.parent == d:
            return None
        d = d.parent


def is_legacy(rel: str, cfg: dict) -> bool:
    return any(fnmatch.fnmatch(rel, pat) for pat in cfg["legacy"])


def exception_paths(root: Path) -> list[str] | None:
    """Paths written in backticks inside EXCEPTIONS.md. None when the file is absent (no check)."""
    path = root / "EXCEPTIONS.md"
    if not path.exists():
        return None
    tokens = re.findall(r"`([^`]+)`", read(path))
    return [norm(t) for t in tokens if ABS_RE.match(t) or t.startswith("~")]


def check(root: Path) -> tuple[list[str], list[str]]:
    root = root.resolve()
    cfg = load_config(root)
    files = collect(root, cfg)
    in_scope = {norm(f) for f in files}
    errors: list[str] = []
    warnings: list[str] = []
    allowed_external = exception_paths(root)
    targets: dict[str, list[str]] = {}  # file -> checked files it links to
    names: dict[str, str] = {}

    def rel(path: Path | str) -> str:
        return Path(os.path.relpath(str(path), root)).as_posix()

    for f in files:
        r = rel(f)
        text = read(f)
        legacy = is_legacy(r, cfg)
        special = f.stem in SPECIAL
        sdir = skill_dir(f, root)
        if sdir is not None:
            targets[norm(f)] = []
            if f.name != "SKILL.md" or f.parent != sdir:
                continue  # companion file
            fm = frontmatter(text)
            missing = [k for k in ("name", "description") if not fm.get(k)]
            if missing:
                errors.append(f"E4 frontmatter missing {','.join(missing)} {r}")
            elif fm["name"] != sdir.name:
                errors.append(f"E4 skill name does not match folder name {r} ({fm['name']})")
            if not NAME_RE.match(sdir.name):
                errors.append(f"E5 folder name is not allowed {r} ({sdir.name})")
            continue
        n_lines = len(text.splitlines())

        # links
        out = []
        for _, target in links(text):
            if ABS_RE.match(target) or target.startswith("~"):
                if not Path(os.path.expanduser(target)).exists():
                    errors.append(f"E2 broken link {r} -> {target}")
                elif norm(target) in in_scope:
                    out.append(norm(target))
                elif allowed_external is not None and not any(
                    norm(target).startswith(p) for p in allowed_external
                ):
                    errors.append(f"E7 external link not registered in EXCEPTIONS.md {r} -> {target}")
                continue
            dest = (f.parent / target).resolve()
            if not dest.exists():
                errors.append(f"E2 broken link {r} -> {target}")
                continue
            if dest.is_dir() or dest.suffix.lower() != ".md":
                continue
            out.append(norm(dest))
            if not legacy:
                inside = norm(dest).startswith(norm(f.parent) + os.sep)
                if not inside and not (special and dest.parent == f.parent):
                    warnings.append(f"W1 link does not point downward {r} -> {rel(dest)}")
        targets[norm(f)] = out

        if legacy:
            continue

        # length
        if f.name == "INDEX.md" and n_lines > MAX_INDEX_LINES:
            errors.append(f"E3 index is longer than {MAX_INDEX_LINES} lines {r} ({n_lines})")
        elif special and n_lines > MAX_SPECIAL_LINES:
            errors.append(f"E3 file is longer than {MAX_SPECIAL_LINES} lines {r} ({n_lines})")
        elif not special and n_lines > MAX_NOTE_LINES:
            warnings.append(f"W3 note is longer than {MAX_NOTE_LINES} lines, consider splitting it {r} ({n_lines})")

        # naming
        for part in Path(r).parts[:-1]:
            if not NAME_RE.match(part) and part not in (".", ".."):
                errors.append(f"E5 folder name is not allowed {r} ({part})")
                break
        if not special and not NAME_RE.match(f.stem):
            errors.append(f"E5 file name is not allowed {r}")

        # frontmatter
        if not special:
            fm = frontmatter(text)
            missing = [k for k in ("name", "description", "status", "updated") if not fm.get(k)]
            if missing:
                errors.append(f"E4 frontmatter missing {','.join(missing)} {r}")
            else:
                if fm["name"] != f.stem:
                    errors.append(f"E4 name does not match file name {r} ({fm['name']})")
                if fm["status"] not in STATUSES:
                    errors.append(f"E4 status must be one of {'/'.join(sorted(STATUSES))} {r}")
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", fm["updated"]):
                    errors.append(f"E4 updated must be written as YYYY-MM-DD {r}")
                if fm["name"] in names:
                    warnings.append(f"W2 duplicate name {r} and {names[fm['name']]}")
                names[fm["name"]] = r

    # Every folder that holds notes needs an INDEX.md
    for d in sorted({f.parent for f in files
                     if not is_legacy(rel(f), cfg) and skill_dir(f, root) is None}):
        if d == root:
            continue
        if not (d / "INDEX.md").exists():
            errors.append(f"E6 folder has no INDEX.md {rel(d)}")

    # Walk down from the entries following links; anything unreachable is an orphan
    # (only entry and index files can lead downward).
    reached: set[str] = set()
    queue = [norm(root / e) for e in cfg["root_entries"]]
    for entry in queue:
        if entry not in in_scope:
            errors.append(f"E1 entry file missing or outside the checked scope {rel(entry)}")
    while queue:
        cur = queue.pop()
        if cur in reached or cur not in in_scope:
            continue
        reached.add(cur)
        if Path(cur).stem.upper() in SPECIAL:
            queue.extend(targets.get(cur, []))
    for f in files:
        sdir = skill_dir(f, root)
        if sdir is not None and norm(f) != norm(sdir / "SKILL.md"):
            continue  # companion files follow SKILL.md
        if norm(f) not in reached:
            errors.append(f"E1 orphan: no index points to it {rel(f)}")

    # Link directory for global skills (not checked at all when hub.json omits skill_links)
    if cfg.get("skill_links"):
        tools_dir = str(Path(__file__).resolve().parent)
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        from link_skills import plan_links

        link_dir = Path(os.path.expanduser(str(cfg["skill_links"])))
        hint = " (run py <HUB>/tools/link_skills.py)"
        if not link_dir.is_dir():
            errors.append(f"E8 link directory does not exist {os.path.normpath(str(link_dir))}{hint}")
        else:
            plan = plan_links(root, link_dir, cfg.get("skill_links_ignore") or [])
            for item in plan.missing:
                errors.append(f"E8 missing link {item.link} -> {item.target}{hint}")
            for item in plan.conflict:
                errors.append(f"E8 link conflict {item.link}: {item.reason}{hint}")
            for item in plan.dangling:
                errors.append(f"E8 dangling link {item.link}{hint}")
            for item in plan.unmanaged:
                warnings.append(f"W4 skill folder not managed by the hub {item.link} (move it into the hub and rerun link_skills.py)")

    return sorted(set(errors)), sorted(set(warnings))


def main() -> int:
    parser = argparse.ArgumentParser(description="Hub structure checker")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--quiet", action="store_true", help="print only the final line")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    errors, warnings = check(Path(args.root))
    if not args.quiet:
        for line in errors + warnings:
            print(line)
    print(f"checked {args.root}: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
