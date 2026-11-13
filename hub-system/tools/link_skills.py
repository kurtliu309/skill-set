"""Create the missing directory junctions for global skills, based on hub.json. Standard library only.

Usage:  py link_skills.py [--root <hub path>] [--dry-run] [--quiet]
hub.json:
  skill_links         link directory, e.g. "~/.claude/skills"; if the key is absent, do nothing
  skill_links_ignore  names in the link directory that the hub does not manage,
                      default ["synced", ".trash"]
A skill unit is any folder under global/ that contains SKILL.md (no recursion below it);
the junction name is the folder name. Only missing junctions are created and dangling
junctions that point at a vanished target inside the hub are removed; real folders and
junctions pointing elsewhere are only reported.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_IGNORE = ["synced", ".trash"]


def norm(path: str | Path) -> str:
    return os.path.normcase(os.path.normpath(os.path.expanduser(str(path))))


def junction_target(link: Path) -> str:
    """The normalized target of a junction, with the Windows long-path prefix removed."""
    raw = os.readlink(link)
    prefix = "\\" * 2 + "?" + "\\"
    if raw.startswith(prefix):
        raw = raw[len(prefix):]
    return norm(raw)


@dataclass
class Item:
    name: str
    link: Path
    target: Path | None = None
    reason: str = ""


@dataclass
class Plan:
    missing: list[Item] = field(default_factory=list)
    ok: list[Item] = field(default_factory=list)
    conflict: list[Item] = field(default_factory=list)
    dangling: list[Item] = field(default_factory=list)
    unmanaged: list[Item] = field(default_factory=list)


def find_skills(hub_root: Path) -> list[tuple[str, Path]]:
    """Folders under global/ that contain SKILL.md: (name, path). No recursion below a hit."""
    base = hub_root / "global"
    found: list[tuple[str, Path]] = []
    if not base.is_dir():
        return found
    for dirpath, dirnames, filenames in os.walk(base):
        d = Path(dirpath)
        if "SKILL.md" in filenames:
            found.append((d.name, d))
            dirnames[:] = []
            continue
        dirnames.sort()
    return found


def inside(path: str, root: str) -> bool:
    return path == root or path.startswith(root + os.sep)


def plan_links(hub_root: Path, link_dir: Path, ignore: list[str]) -> Plan:
    """Pure decision logic: classify every entry in the link directory without touching the disk."""
    hub_root = Path(hub_root).resolve()
    link_dir = Path(link_dir)
    hub_norm = norm(hub_root)
    ignore_set = set(ignore or [])
    plan = Plan()

    by_name: dict[str, Path] = {}
    dupes: set[str] = set()
    for name, path in find_skills(hub_root):
        if name in by_name:
            dupes.add(name)
        else:
            by_name[name] = path

    present: set[str] = set()
    entries = sorted(link_dir.iterdir(), key=lambda p: os.path.normcase(p.name)) if link_dir.is_dir() else []
    for entry in entries:
        name = entry.name
        present.add(name)
        if os.path.isjunction(entry):
            target = junction_target(entry)
            if name in dupes:
                plan.conflict.append(Item(name, entry, None, "two skills in the hub share this name"))
            elif name in by_name:
                if target == norm(by_name[name]):
                    plan.ok.append(Item(name, entry, by_name[name]))
                else:
                    plan.conflict.append(Item(name, entry, Path(target), "junction points elsewhere"))
            elif inside(target, hub_norm):
                if os.path.exists(target):
                    plan.unmanaged.append(Item(name, entry, Path(target), "points to a non-skill folder inside the hub"))
                else:
                    plan.dangling.append(Item(name, entry, Path(target)))
            # A junction pointing outside the hub whose name is not a hub skill: leave it alone, do not report.
        else:
            if name in ignore_set:
                continue
            if name in by_name or name in dupes:
                plan.conflict.append(Item(name, entry, None, "an item with this name is a real folder/file"))
            else:
                plan.unmanaged.append(Item(name, entry, None, "real folder"))

    for name in sorted(by_name):
        if name in present or name in ignore_set:
            continue
        if name in dupes:
            plan.conflict.append(Item(name, link_dir / name, None, "two skills in the hub share this name"))
        else:
            plan.missing.append(Item(name, link_dir / name, by_name[name]))
    return plan


def make_junction(link: Path, target: Path) -> bool:
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True
    )
    return result.returncode == 0


def run(root: Path, dry_run: bool = False, quiet: bool = False) -> int:
    root = Path(root).resolve()
    cfg_path = root / "hub.json"
    cfg: dict = {}
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig", errors="replace"))
    link_cfg = cfg.get("skill_links")
    if not link_cfg:
        print("hub.json has no skill_links, skipping")
        return 0

    link_dir = Path(os.path.expanduser(str(link_cfg)))
    ignore = cfg.get("skill_links_ignore") or DEFAULT_IGNORE
    plan = plan_links(root, link_dir, ignore)
    failed = False

    def say(text: str) -> None:
        if not quiet:
            print(text)

    for item in plan.ok:
        say(f"exists {item.link} -> {item.target}")
    for item in plan.missing:
        if dry_run:
            say(f"would create {item.link} -> {item.target}")
            continue
        link_dir.mkdir(parents=True, exist_ok=True)
        if make_junction(item.link, item.target):
            say(f"created {item.link} -> {item.target}")
        else:
            failed = True
            say(f"failed to create junction {item.link} -> {item.target}")
    for item in plan.dangling:
        if dry_run:
            say(f"would remove dangling junction {item.link}")
            continue
        try:
            os.rmdir(item.link)  # remove the junction only, never recurse
            say(f"removed dangling junction {item.link}")
        except OSError as exc:
            failed = True
            say(f"failed to remove dangling junction {item.link} ({exc})")
    for item in plan.conflict:
        say(f"conflict {item.link}: {item.reason}")
    for item in plan.unmanaged:
        say(f"unmanaged {item.link} (move it into the hub and run again)")

    print(
        f"links {os.path.normpath(str(link_dir))}: "
        f"created {len(plan.missing)}, existing {len(plan.ok)}, removed {len(plan.dangling)}, "
        f"conflicts {len(plan.conflict)}, unmanaged {len(plan.unmanaged)}"
    )
    return 1 if plan.conflict or failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create the missing junctions for hub skills")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--dry-run", action="store_true", help="only print what would happen, change nothing")
    parser.add_argument("--quiet", action="store_true", help="print only the final line")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    return run(Path(args.root), dry_run=args.dry_run, quiet=args.quiet)


if __name__ == "__main__":
    sys.exit(main())
