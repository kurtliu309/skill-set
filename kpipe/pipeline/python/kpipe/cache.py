"""Labs File Cache helpers.

Caches always go through the newest labs::filecache. With a Scene Manager present the
base folder and frame range follow its live variables, so TOP shot wedges cache each shot
into its own folder with its own range (basename stays $OS):
    <var_cache>/$OS/v1/$OS_v1.$F4.bgeo.sc
"""

import os
import shutil
import time

import hou

from . import config

TAG = "kpipe_cache"


def filecache_type():
    """Newest labs::filecache SOP type name, e.g. 'labs::filecache::2.0'."""
    def ver(name):
        parts = name.split("::")
        try:
            return tuple(int(x) for x in parts[2].split(".")) if len(parts) > 2 else (0,)
        except ValueError:
            return (0,)
    names = [n for n in hou.sopNodeTypeCategory().nodeTypes() if n.startswith("labs::filecache")]
    if not names:
        raise RuntimeError("SideFX Labs File Cache not installed")
    return max(names, key=ver)


def create_cache(src, name=None):
    """Append a Labs File Cache after SOP node `src` (tagged as a kpipe cache)."""
    name = name or "cache_" + src.name()
    node = src.parent().createNode(filecache_type(), name)
    node.setInput(0, src)
    node.setPosition(src.position() + hou.Vector2(0, -1.2))
    node.setColor(hou.Color(0.9, 0.6, 0.2))
    node.setUserData(TAG, "1")
    if hou.node(config.SM_PATH):
        node.parm("basedir").set('`chs("{}/var_cache")`'.format(config.SM_PATH))
        node.parm("trange").set(1)  # Frame Range
        node.parm("f1").setExpression('ch("{}/var_start")'.format(config.SM_PATH))
        node.parm("f2").setExpression('ch("{}/var_end")'.format(config.SM_PATH))
    return node


def tagged_caches(root="/obj"):
    """All kpipe-tagged cache nodes under root, in creation order."""
    nodes = [n for n in hou.node(root).allSubChildren() if n.userData(TAG) == "1"]
    return sorted(nodes, key=lambda n: n.sessionId())


def cache_dir(node):
    return node.parm("cachedir").eval()


def disk_usage(path):
    """(file count, bytes) under path."""
    count = size = 0
    for dirpath, _, files in os.walk(path):
        for f in files:
            count += 1
            size += os.path.getsize(os.path.join(dirpath, f))
    return count, size


def free_gb(path=None):
    path = path or hou.text.expandString("$HIP")
    return shutil.disk_usage(os.path.splitdrive(path)[0] + "/").free / 1024 ** 3


def log_dir():
    """<var_dir>/scenes/logs when a Scene Manager exists, else $HIP/logs."""
    sm = hou.node(config.SM_PATH)
    base = sm.evalParm("var_" + config.SCENES) if sm and sm.evalParm("var_dir") else hou.text.expandString("$HIP")
    return base + "/logs"


def _log(msg):
    logdir = log_dir()
    os.makedirs(logdir, exist_ok=True)
    line = "{} {}\n".format(time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    with open(os.path.join(logdir, "cache.log"), "a", encoding="utf-8") as f:
        f.write(line)


def cook(node, frange=None):
    """Save `node` to disk in the foreground. frange=(start, end) overrides its range.

    Returns dict(seconds, frames, files, gb, dir).
    """
    old = None
    if frange:
        old = [p.eval() for p in node.parmTuple("f")]
        exprs = [(p.expression() if p.keyframes() else None) for p in node.parmTuple("f")]
        node.parmTuple("f").deleteAllKeyframes()
        node.parmTuple("f").set((frange[0], frange[1], 1))
    try:
        start, end = node.parm("f1").eval(), node.parm("f2").eval()
        _log("start {} frames {}-{}".format(node.path(), int(start), int(end)))
        t0 = time.time()
        node.parm("execute").pressButton()
        secs = time.time() - t0
    finally:
        if old is not None:
            for p, expr, val in zip(node.parmTuple("f"), exprs, old):
                if expr:
                    p.setExpression(expr)
                else:
                    p.set(val)
    files, size = disk_usage(cache_dir(node))
    result = dict(seconds=round(secs, 1), frames=int(end - start + 1), files=files,
                  gb=round(size / 1024 ** 3, 3), dir=cache_dir(node))
    _log("done  {} {}".format(node.path(), result))
    return result


def estimate(node, frames=config.TEST_FRAMES):
    """Cache the first `frames` frames and extrapolate time / disk to the full range."""
    start, end = node.parm("f1").eval(), node.parm("f2").eval()
    total = int(end - start + 1)
    test = cook(node, (start, min(end, start + frames - 1)))
    k = total / float(test["frames"])
    return dict(test=test, total_frames=total,
                est_minutes=round(test["seconds"] * k / 60, 1),
                est_gb=round(test["gb"] * k, 2),
                free_gb=round(free_gb(), 1),
                over_limit=test["gb"] * k > config.CACHE_LIMIT_GB)
