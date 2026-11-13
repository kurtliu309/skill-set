"""Projects, shots, assets and work-file versions (folders + project.json).

Shots (GRS_0010) and assets (fxGrass) are both "items": each has a frame range in
project.json and the same subfolders (config.ITEM_DIRS). An asset code is its category
(lowercase) followed by a capitalized name, so the category can be read from the code.

Functions that load or save hips import hou lazily, so the rest works outside Houdini.
"""

import glob
import json
import os
import re
import time

from . import config

PROJECT_RE = re.compile(r"[a-z][a-z0-9_]*")       # grass
SEQ_RE = re.compile(r"[A-Z]{3}")                  # GRS
SHOT_RE = re.compile(r"[A-Z]{3}_\d{4}")           # GRS_0010
CATEGORY_RE = re.compile(r"[a-z]+")               # fx
ASSET_RE = re.compile(r"[a-z]+[A-Z][A-Za-z0-9]*")  # fxGrass
ARTIST_RE = re.compile(r"[a-z0-9]+")
_HIP = re.compile(r"^(?P<stem>.+)_v(?P<ver>\d{3})_(?P<artist>[a-z0-9]+)\.hip$")
_KINDS = ("shots", "assets")


def _check(regex, value, what):
    if not regex.fullmatch(value or ""):
        raise ValueError("bad {}: {!r} (expected {})".format(what, value, regex.pattern))


# ---------------------------------------------------------------- projects

def project_dir(project, playground=False):
    _check(PROJECT_RE, project, "project code")
    return "{}/{}".format(config.PLAYGROUND if playground else config.ROOT, project)


def find_project(project):
    """Existing project folder (projects/ first, then playground) or None."""
    if not PROJECT_RE.fullmatch(project or ""):
        return None
    for playground in (False, True):
        d = project_dir(project, playground)
        if os.path.isfile(os.path.join(d, config.MANIFEST)):
            return d
    return None


def require_project(project):
    d = find_project(project)
    if not d:
        raise ValueError("project {!r} not found".format(project))
    return d


def manifest_path(project):
    return os.path.join(require_project(project), config.MANIFEST)


def load(project):
    with open(manifest_path(project), encoding="utf-8") as f:
        data = json.load(f)
    for kind in _KINDS:
        data.setdefault(kind, {})
    return data


def _save(project, data):
    with open(manifest_path(project), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def list_projects():
    names = set()
    for root in (config.ROOT, config.PLAYGROUND):
        for m in glob.glob(os.path.join(root, "*", config.MANIFEST)):
            name = os.path.basename(os.path.dirname(m))
            if PROJECT_RE.fullmatch(name):
                names.add(name)
    return sorted(names)


def new_project(project, playground=False):
    """Create <root>/<project>/{shot,asset}/ and an empty project.json."""
    if find_project(project):
        raise FileExistsError("project already exists: " + find_project(project))
    base = project_dir(project, playground)
    for sub in ("shot", "asset"):
        os.makedirs("{}/{}".format(base, sub), exist_ok=True)
    with open(os.path.join(base, config.MANIFEST), "w", encoding="utf-8") as f:
        json.dump(dict(created=time.strftime("%Y-%m-%d"), shots={}, assets={}), f, indent=2)
    return base


# ---------------------------------------------------------------- items (shots + assets)

def is_shot(code):
    return bool(SHOT_RE.fullmatch(code or ""))


def is_asset(code):
    return bool(ASSET_RE.fullmatch(code or ""))


def group(code):
    """Sequence of a shot (GRS) or category of an asset (fx)."""
    return code[:3] if is_shot(code) else re.match(r"[a-z]+", code).group(0)


def asset_code(category, name):
    """fx + grass -> fxGrass."""
    name = (name or "").strip()
    return category + name[:1].upper() + name[1:]


def shot_code(seq, number):
    return "{}_{:04d}".format(seq, int(number))


def _kind(code):
    return "shots" if is_shot(code) else "assets"


def item_order(data):
    """Shots (sorted), then assets (sorted by category, name)."""
    return sorted(data["shots"]) + sorted(data["assets"], key=lambda a: (group(a), a))


def items(project):
    return item_order(load(project))


def shots(project):
    return sorted(load(project)["shots"])


def assets(project):
    return sorted(load(project)["assets"], key=lambda a: (group(a), a))


def item_info(data, code):
    """{start, end} of a shot or asset in loaded project.json data, or None."""
    if not code:
        return None
    return data["shots"].get(code) if is_shot(code) else data["assets"].get(code)


def sequences(project):
    return sorted({group(s) for s in shots(project)})


def categories(project):
    """Default categories plus the ones the project uses."""
    used = {group(a) for a in assets(project)}
    return list(config.ASSET_CATEGORIES) + sorted(used - set(config.ASSET_CATEGORIES))


def item_dir(project, code):
    """<project>/shot/<SEQ>/<SHOT> or <project>/asset/<category>/<asset>."""
    kind = "shot" if is_shot(code) else "asset"
    return "{}/{}/{}/{}".format(require_project(project), kind, group(code), code)


shot_dir = item_dir


def scenes_dir(project, code):
    return item_dir(project, code) + "/" + config.SCENES


def default_range(project):
    """Range of the last registered shot (else asset), else config.DEFAULT_RANGE."""
    data = load(project)
    for kind in _KINDS:
        if data[kind]:
            last = data[kind][sorted(data[kind])[-1]]
            return last["start"], last["end"]
    return config.DEFAULT_RANGE


def next_shot_number(project, seq):
    """Next free shot number of a sequence, step 10 (10, 20, ...)."""
    nums = [int(s[4:]) for s in shots(project) if s.startswith(seq + "_")]
    return (max(nums) // 10 + 1) * 10 if nums else 10


def next_shot_name(project, seq):
    return shot_code(seq, next_shot_number(project, seq))


def _register(project, code, start, end):
    data = load(project)
    kind = _kind(code)
    if code in data[kind]:
        raise FileExistsError("{} already exists: {}".format(kind[:-1], code))
    d_start, d_end = default_range(project)
    data[kind][code] = dict(start=int(d_start if start is None else start),
                            end=int(d_end if end is None else end))
    _save(project, data)
    for sub in config.ITEM_DIRS:
        os.makedirs("{}/{}".format(item_dir(project, code), sub), exist_ok=True)
    return data[kind][code]


def new_shot(project, shot, start=None, end=None):
    """Register a shot (GRS_0010) and create shot/<SEQ>/<SHOT>/{ITEM_DIRS}."""
    _check(SHOT_RE, shot, "shot code (e.g. GRS_0010)")
    return _register(project, shot, start, end)


def new_asset(project, code, start=None, end=None):
    """Register an asset (fxGrass) and create asset/<category>/<asset>/{ITEM_DIRS}."""
    _check(ASSET_RE, code, "asset code (e.g. fxGrass)")
    return _register(project, code, start, end)


def new_item(project, code, start=None, end=None):
    return (new_shot if is_shot(code) else new_asset)(project, code, start, end)


def set_range(project, code, start, end):
    data = load(project)
    kind = _kind(code)
    if code not in data[kind]:
        raise ValueError("{} not registered: {}".format(kind[:-1], code))
    data[kind][code] = dict(start=int(start), end=int(end))
    _save(project, data)


# ---------------------------------------------------------------- versions

def versions(folder, stem):
    """Sorted [(ver, path)] of <stem>_vNNN_<artist>.hip in folder."""
    out = []
    for path in glob.glob(os.path.join(folder, stem + "_v[0-9][0-9][0-9]_*.hip")):
        m = _HIP.match(os.path.basename(path))
        if m and m.group("stem") == stem:
            out.append((int(m.group("ver")), path.replace("\\", "/")))
    return sorted(out)


def hip_versions(project, code):
    """Work files of a shot / asset, newest first: [dict(ver, artist, mtime, path)]."""
    out = []
    for ver, path in reversed(versions(scenes_dir(project, code), code)):
        out.append(dict(ver=ver, artist=_HIP.match(os.path.basename(path)).group("artist"),
                        mtime=os.path.getmtime(path), path=path))
    return out


def latest_hip(project, code):
    vs = versions(scenes_dir(project, code), code)
    return vs[-1][1] if vs else None


def next_hip(folder, stem, artist=config.DEFAULT_ARTIST):
    _check(ARTIST_RE, artist, "artist")
    vs = versions(folder, stem)
    ver = vs[-1][0] + 1 if vs else 1
    return "{}/{}_v{:03d}_{}.hip".format(folder, stem, ver, artist)


# ---------------------------------------------------------------- hip operations (need hou)

def new_work_file(project, code, artist=config.DEFAULT_ARTIST, empty=False):
    """First work file of a shot / asset: point the Scene Manager at it and save v001.

    empty=True clears the current scene first (ask before discarding unsaved work).
    Raises FileExistsError (message = latest hip path) if it already has a work file.
    """
    import hou
    from . import scene
    latest = latest_hip(project, code)
    if latest:
        raise FileExistsError(latest)
    path = next_hip(scenes_dir(project, code), code, artist)
    if empty:
        hou.hipFile.clear(suppress_save_prompt=True)
    scene.ensure(project, code, artist)
    hou.hipFile.save(path)
    return path


def open_hip(path, force=False):
    import hou
    if not force and hou.hipFile.hasUnsavedChanges():
        raise RuntimeError("current hip has unsaved changes; save or discard first")
    hou.hipFile.load(path, suppress_save_prompt=True, ignore_load_warnings=True)
    return path


def save_version(artist=None):
    """Save the current hip as the next version in its Scene Manager shot's scenes/."""
    import hou
    from . import scene
    n = scene.node()
    if n is None or not (n.evalParm("project") and n.evalParm("shot")):
        raise RuntimeError("Scene Manager has no project / shot")
    code = n.evalParm("shot")
    folder = scenes_dir(n.evalParm("project"), code)
    os.makedirs(folder, exist_ok=True)
    path = next_hip(folder, code, artist or n.evalParm("artist"))
    hou.hipFile.save(path)
    return path
