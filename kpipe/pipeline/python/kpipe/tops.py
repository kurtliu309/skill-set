"""TOP template: run a cache once per shot by wedging the Scene Manager's shot parm.

    wedge_shots  (Wedge)     string attribute "shot", Value List = shot codes,
                             Target Parameter = /obj/scene_manager/shot
    cache_shots  (ROP Fetch) ROP Path = <Labs File Cache>/render,
                             Frame Generation = ROP Node Configuration

Each work item sets the shot parm, the Scene Manager's live var_* follow, so the cache
writes to <shot>/cache with that shot's frame range (its remembered Custom Range, else its
Project Range). Shots and assets can be mixed.

The shot list is picked on the Scene Manager (Wedge Shots, or the Slice List when Enable
Slice is on) and written into every shot wedge by sync_wedges(); don't edit the Value List
by hand.
"""

import hou

from . import config, scene

NOTE = """Shot wedge template (kpipe)

wedge_shots: one work item per shot (or asset).
  Attribute "shot" (String, Value List). The list is synced from the Scene Manager:
  pick shots there (Wedge Shots, or Slice List with Enable Slice on), don't edit it here.
  Target Parameter: {sm}/shot (switches the Scene Manager per work item).
  Click a work item to preview that shot: the Scene Manager's var_* follow it.

cache_shots: ROP Fetch.
  ROP Path: the Labs File Cache's "render" node, e.g. /obj/fx/cache_x/render.
  Frame Generation: ROP Node Configuration (uses each shot's var_start / var_end:
  its remembered Custom Range, else its Project Range).

Cook: select cache_shots and press Shift+V (or Cook Output Node).
Results: <shot or asset folder>/cache/<cache node>/
Save the hip first: ROP Fetch cooks a saved copy out of process."""


def _picked(n):
    """Slice List when Enable Slice is on, otherwise Wedge Shots."""
    if n.evalParm("enable_slice"):
        return [s for s in scene.shot_list(n, "slice_shots") if s in scene.shot_list(n, "wedge_shots")]
    return scene.shot_list(n, "wedge_shots")


def follows_current(n=None):
    """True when no shots are picked, so the wedges run the current shot."""
    n = n or scene.node()
    return n is not None and not _picked(n)


def selected_shots(n=None):
    """Shots sent to the shot wedges, in project order.

    Slice List (Enable Slice on) or Wedge Shots; nothing picked = the current shot.
    """
    n = n or scene.node()
    if n is None:
        return []
    picked = _picked(n)
    if picked:
        return picked
    shot = n.evalParm("shot")
    return [shot] if shot in scene.project_shots(n) else []


def find_wedges(root="/obj"):
    """Wedge TOPs whose first attribute is "shot" and targets the Scene Manager's shot parm."""
    out = []
    for n in hou.node(root).allSubChildren():
        if n.type().category() != hou.topNodeTypeCategory() or n.type().name() != "wedge":
            continue
        if n.parm("name1") is None or n.parm("channel1") is None:
            continue
        if n.evalParm("name1") == "shot" and n.evalParm("channel1") == config.SM_PATH + "/shot":
            out.append(n)
    return out


def _set_values(wedge, shots):
    wedge.parm("wedgecount").set(len(shots))
    wedge.parm("values1").set(len(shots))
    for i, shot in enumerate(shots, 1):
        wedge.parm("strvalue1_{}".format(i)).set(shot)


def sync_wedges(n=None):
    """Write the Scene Manager's shot selection into every shot wedge. Returns the wedges."""
    shots = selected_shots(n)
    wedges = find_wedges()
    for wedge in wedges:
        if [wedge.evalParm("strvalue1_{}".format(i)) for i in range(1, wedge.evalParm("values1") + 1)] != shots:
            _set_values(wedge, shots)
    return wedges


def build_shot_wedge(cache_node=None, shots=None, parent="/obj"):
    """Create <parent>/shot_wedge: Wedge over shots -> ROP Fetch of `cache_node`.

    Shots default to the Scene Manager's selection (see selected_shots).
    """
    sm = scene.node()
    if sm is None or not sm.evalParm("project"):
        raise RuntimeError("Set up the Scene Manager (project / shot) first")
    shots = list(shots or selected_shots(sm))
    if not shots:
        raise RuntimeError("No shots: pick a shot on the Scene Manager first")

    par = hou.node(parent)
    net = par.createNode("topnet", "shot_wedge")
    wedge = net.createNode("wedge", "wedge_shots")
    wedge.parm("wedgeattributes").set(1)
    wedge.parm("name1").set("shot")
    wedge.parm("type1").set(4)       # String
    wedge.parm("wedgetype1").set(2)  # Value List
    _set_values(wedge, shots)
    wedge.parm("exportchannel1").set(1)
    wedge.parm("channel1").set(config.SM_PATH + "/shot")

    fetch = net.createNode("ropfetch", "cache_shots")
    fetch.setInput(0, wedge)
    fetch.parm("framegeneration").set(3)  # ROP Node Configuration
    if cache_node is not None:
        fetch.parm("roppath").set(cache_node.path() + "/render")
    fetch.setDisplayFlag(True)

    net.layoutChildren()
    note = net.createStickyNote("readme")
    note.setText(NOTE.format(sm=config.SM_PATH))
    note.setSize(hou.Vector2(7, 5))
    # left of the nodes: layoutChildren puts the local scheduler to the right
    note.setPosition(wedge.position() + hou.Vector2(-8, -3.5))
    net.moveToGoodPosition()
    return net
