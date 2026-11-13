"""Scan the hub and the registered projects, and generate the interactive hierarchy map map.html. Standard library only.

Usage:  py build_map.py [--out <path>]
Starts at the global entry and follows the links in the indexes downward, exactly the
same path an AI takes when it looks something up.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check import ABS_RE, FENCE_RE, LINK_RE, frontmatter, norm, read  # noqa: E402

HUB = Path(__file__).resolve().parent.parent
GLOBAL_ENTRY = Path(os.path.expanduser("~/.claude/CLAUDE.md"))
GUIDES = {"INDEX", "AGENTS", "CLAUDE"}  # links inside these files are expanded further
SKILL_TOKEN = re.compile(r"`skill:([^`]+)`")
YES = {"yes", "true", "y", "是"}


def rows(text: str):
    """Yield (title, link target or None, skill name or None, when to read) for every row."""
    fenced = False
    for line in text.splitlines():
        if FENCE_RE.match(line.strip()):
            fenced = not fenced
            continue
        if fenced:
            continue
        link = LINK_RE.search(re.sub(r"`[^`]*`", lambda m: " " * len(m.group()), line))
        token = SKILL_TOKEN.search(line)
        if not link and not token:
            continue
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            when = cells[-1] if len(cells) > 1 else ""
        else:
            tail = line[(link.end() if link else token.end()):]
            when = tail.strip(" —-:：。")
        when = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", when).replace("`", "")
        if link and not re.match(r"^[a-z]+://", link.group(2)):
            yield link.group(1), link.group(2).split("#")[0], None, when
        elif token:
            yield token.group(1), None, token.group(1), when


def title_of(path: Path, text: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, re.M)
    return m.group(1).strip() if m else fallback


def role_of(path: Path) -> str:
    if path.name == "SKILL.md":
        return "skill"
    if path.stem in ("AGENTS", "CLAUDE"):
        return "entry"
    if path.stem == "INDEX":
        return "index"
    return "note"


def node_for(path: Path, label: str, when: str, seen: set[str]) -> dict:
    node = {"title": label, "when": when, "path": str(path), "children": []}
    if not path.exists():
        node.update(role="missing", desc="file does not exist")
        return node
    if path.is_dir() or path.suffix.lower() != ".md":
        node.update(role="file", desc="")
        return node
    text = read(path)
    fm = frontmatter(text)
    node["role"] = role_of(path)
    node["desc"] = fm.get("description", "")
    node["status"] = fm.get("status", "")
    node["updated"] = fm.get("updated", "")
    node["lines"] = len(text.splitlines())
    if node["role"] == "skill":
        node["title"] = fm.get("name", label)
        for extra in sorted(path.parent.rglob("*")):
            if extra.is_file() and extra != path and "__pycache__" not in extra.parts:
                node["children"].append({
                    "title": extra.relative_to(path.parent).as_posix(), "role": "file",
                    "when": "companion file of the skill; read it only when SKILL.md mentions it", "desc": "",
                    "path": str(extra), "children": [],
                })
        return node
    if node["role"] in ("index", "entry"):
        node["title"] = title_of(path, text, label) if node["role"] == "index" else label
    key = norm(path)
    if path.stem in GUIDES and key not in seen:
        seen.add(key)
        node["children"] = children_of(path, text, seen)
    return node


def children_of(path: Path, text: str, seen: set[str]) -> list[dict]:
    kids = []
    for label, target, skill, when in rows(text):
        if skill:
            kids.append({"title": skill, "role": "skill-ext", "when": when, "children": [],
                         "desc": "skill outside the hub (installed in the app or a plugin); load it by name", "path": ""})
            continue
        if ABS_RE.match(target) or target.startswith("~"):
            dest = Path(os.path.expanduser(target))
        else:
            dest = (path.parent / target).resolve()
        kids.append(node_for(dest, label, when, seen))
    return kids


def project_nodes(seen: set[str]) -> list[dict]:
    text = read(HUB / "projects" / "INDEX.md")
    out = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or not re.match(r"^`[A-Za-z]:", cells[1]):
            continue
        root = Path(cells[1].strip("`"))
        entry = root / "AGENTS.md"
        organized = cells[2].lower() in YES
        node = {"title": cells[0], "role": "project", "when": cells[3], "path": str(root),
                "desc": "organized following the protocol" if organized else "registered only, not organized yet",
                "children": []}
        if organized and entry.exists():
            node["children"] = [node_for(entry, "AGENTS.md (project entry)", "loaded automatically when a session starts in this project", seen)]
        out.append(node)
    return out


def build() -> dict:
    seen: set[str] = set()
    hub_index = node_for(HUB / "INDEX.md", "Hub index", "the global entry points here", seen)
    for child in hub_index["children"]:
        if child.get("path") and norm(child["path"]) == norm(HUB / "projects" / "INDEX.md"):
            child["children"] = project_nodes(seen)
    return {
        "title": "Global entry CLAUDE.md", "role": "entry", "path": str(GLOBAL_ENTRY),
        "when": "loaded automatically in every session", "desc": "hard rules only, plus 'go read the hub index'",
        "lines": len(read(GLOBAL_ENTRY).splitlines()) if GLOBAL_ENTRY.exists() else 0,
        "children": [hub_index],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(HUB / "map.html"))
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    tree = build()
    template = read(Path(__file__).resolve().parent / "map_template.html")
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    data = json.dumps(tree, ensure_ascii=False).replace("</", "<\\/")
    Path(args.out).write_text(
        template.replace("/*__DATA__*/null", data).replace("__STAMP__", stamp), encoding="utf-8"
    )

    def count(n):
        return 1 + sum(count(c) for c in n["children"])

    print(f"generated {args.out}: {count(tree)} nodes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
