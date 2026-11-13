"""Scene Manager node (/obj/scene_manager, kpipe::scene_manager::1.0).

Picks the current context (project + shot, existing ones only) and exposes live variables
that other nodes reference, e.g. `chs("/obj/scene_manager/var_cache")`.

"Shot" here means a shot (GRS_0010) or an asset (fxGrass): both have a frame range and the
same subfolders, and both can be the Current Shot or be listed in Wedge Shots.

var_* parms are Python expressions of the effective shot, so they follow it without
callbacks. The effective shot is the active TOP work item's "shot" attribute when one is
selected (preview), otherwise the Current Shot parm (`shot`, a plain text field so it can be
copied and referenced; Pick Shot opens a single-choice list). The node comment shows the effective shot.

Ranges: Project Range is the shot's range in project.json (edits are saved there).
Custom Range is the working range: typing a value remembers it for that shot in the hip
(hidden custom_ranges, JSON {shot: [start, end]}); shots without one follow Project Range.
Switching shots restores the remembered range, Reset forgets it. It drives var_start /
var_end and the playbar; TOP work items use their shot's remembered range too, else Project Range.

Shot lists: Wedge Shots is the hip's working list (the Current Shot menu lists it). The
shots sent to TOP shot wedges are the Slice List when Enable Slice is on, otherwise Wedge
Shots; either one empty falls back to the current shot. tops.sync_wedges() writes them into
the wedges. Creating projects/shots lives in create_ui.py, not here.
"""

import json
import os

import hou

from . import config, project

_PY = hou.scriptLanguage.Python
# Tuple name, not parm_name: editing one component of a 2-int parm reports e.g. "project_range1".
# kwargs has no 'parm_tuple' for typed string edits; parm.tuple() works for every parm kind
_ON_CHANGE = "import kpipe.scene; kpipe.scene.on_change(kwargs['node'], kwargs['parm'].tuple().name())"
_ON_CREATED = "import kpipe.scene\nkpipe.scene.on_created(kwargs['node'])\n"
_ON_LOADED = "import kpipe.scene\nkpipe.scene.start_watch()\n"
_VAR_EXPR = '__import__("kpipe.scene").scene.var(hou.pwd(), "{}")'
_WATCH_MS = 500

LISTS = ("wedge_shots", "slice_shots")
_SUB_HELP = {"scenes": "work files (hips)", "cache": "caches", "playblast": "flipbooks and snapshots",
             "assets": "assets used by this shot", "render": "render output"}

_manifests = {}  # project.json path -> (mtime, data)


def node():
    return hou.node(config.SM_PATH)


# ---------------------------------------------------------------- live variables

def _manifest(proj):
    path = project.manifest_path(proj)
    mtime = os.path.getmtime(path)
    cached = _manifests.get(path)
    if cached is None or cached[0] != mtime:
        cached = (mtime, project.load(proj))
        _manifests[path] = cached
    return cached[1]


def project_shots(n):
    proj = n.evalParm("project")
    try:
        return project.item_order(_manifest(proj)) if proj else []
    except Exception:
        return []


def _canonical(pool, code):
    """Code as registered (case-insensitive match against pool), or None."""
    lookup = {c.lower(): c for c in pool}
    return lookup.get((code or "").lower())


def custom_ranges(n):
    """{shot: (start, end)} remembered in the hip."""
    try:
        return {k: tuple(v) for k, v in json.loads(n.evalParm("custom_ranges") or "{}").items()}
    except Exception:
        return {}


def _set_custom_ranges(n, ranges):
    text = json.dumps({k: list(v) for k, v in sorted(ranges.items())}) if ranges else ""
    if n.evalParm("custom_ranges") != text:
        n.parm("custom_ranges").set(text)


def _work_item_shot(dep=True):
    """"shot" attribute of the active PDG work item (selected in the UI or cooking), or None.

    dep=True (inside parm expressions) makes the evaluating parm depend on the active work
    item, so it re-evaluates when another work item is selected.
    """
    try:
        import pdg
        ctx = pdg.EvaluationContext
        wi = ctx.workItemDep() if dep else ctx.workItem()
        return wi.attribValue("shot") if wi is not None else None
    except Exception:
        return None


def effective(n, dep=True):
    """(project, shot, from_work_item) the variables resolve to."""
    proj, shot = n.evalParm("project"), n.evalParm("shot")
    wi_shot = _work_item_shot(dep)
    if wi_shot and proj:
        try:
            if project.item_info(_manifest(proj), wi_shot):
                return proj, wi_shot, True
        except Exception:
            pass
    return proj, shot, False


def _info(n, dep=True):
    """(project, shot, from_work_item, {start, end}) or None when there is no valid shot.

    The current shot uses Custom Range; a work item uses its shot's remembered Custom Range,
    else its Project Range.
    """
    try:
        proj, shot, wi = effective(n, dep)
        info = project.item_info(_manifest(proj), shot) if proj and shot else None
    except Exception:
        return None
    if not info:
        return None
    if wi:
        custom = custom_ranges(n).get(shot)
        if custom:
            info = {"start": custom[0], "end": custom[1]}
    else:
        start, end = n.parmTuple("custom_range").eval()
        info = {"start": start, "end": end}
    return proj, shot, wi, info


def var(n, key):
    """Value of var_<key> for node n: shot, dir, start, end or a subfolder (config.ITEM_DIRS)."""
    numeric = key in ("start", "end")
    found = _info(n)
    if found is None:
        return 0 if numeric else ""
    proj, shot, _, info = found
    if numeric:
        return info[key]
    if key == "shot":
        return shot
    folder = project.item_dir(proj, shot)
    return folder if key == "dir" else folder + "/" + key


def status(n, dep=True):
    """One-line summary of the effective shot, e.g. 'grass / GRS_0020 | 1001-1100  [work item]'."""
    found = _info(n, dep)
    if found is None:
        return "No shot"
    proj, shot, wi, info = found
    text = "{} / {} | {}-{}".format(proj, shot, info["start"], info["end"])
    return text + "  [work item]" if wi else text


def source(n, dep=True):
    _, shot, wi = effective(n, dep)
    return "Work item: " + shot if wi else "Current Shot"


def shot_list(n, name):
    """Shots in list parm `name` (wedge_shots / slice_shots), valid and in project order."""
    picked = n.evalParm(name).split()
    return [s for s in project_shots(n) if s in picked]


def sent_list(n):
    """Display text for the shots the TOP shot wedges get."""
    from . import tops
    shots = tops.selected_shots(n)
    if not shots:
        return "(none)"
    text = " ".join(shots)
    return text + "  (current shot)" if tops.follows_current(n) else text


# ---------------------------------------------------------------- status displays

_DISPLAYS = {"wedge_list": sent_list, "var_source": lambda n: source(n, dep=False)}


def refresh_status(n=None):
    """Show the effective shot as the node comment and refresh the plain-text status parms.

    Status parms hold plain values (not expressions) so they look like normal fields.
    """
    n = n or node()
    if n is None:
        return
    text = status(n, dep=False)
    if n.comment() != text:
        n.setComment(text)
    if not n.isGenericFlagSet(hou.nodeFlag.DisplayComment):
        n.setGenericFlag(hou.nodeFlag.DisplayComment, True)
    with hou.undos.disabler():
        for name, fn in _DISPLAYS.items():
            parm = n.parm(name)
            if parm is None:
                continue
            if parm.keyframes():  # expression left over from older kpipe versions
                parm.deleteAllKeyframes()
            value = fn(n)
            if parm.unexpandedString() != value:
                parm.set(value)


def on_display_edit(n, parm_name):
    """Status fields are display only: restore them."""
    refresh_status(n)


def _tick():
    try:
        refresh_status()
    except Exception:
        pass


def start_watch():
    """Keep the node comment up to date (work item selection has no callback)."""
    if not hou.isUIAvailable():
        return
    from PySide6 import QtCore
    old = getattr(hou.session, "_kpipe_watch", None)
    if old is not None:
        old.stop()
    timer = QtCore.QTimer()
    timer.setInterval(_WATCH_MS)
    timer.timeout.connect(_tick)
    timer.start()
    hou.session._kpipe_watch = timer


def clear_work_item():
    """Deselect the active TOP work item so the variables follow the Current Shot parm again."""
    import pdg
    for n in hou.node("/").allSubChildren():
        if n.type().name() == "topnet" and hasattr(n, "deselectWorkItem"):
            n.deselectWorkItem()
    pdg.EvaluationContext.setGlobalWorkItem(None, True)
    refresh_status()


# ---------------------------------------------------------------- menus

def _pairs(names):
    out = []
    for name in names:
        out += [name, name]
    return out


def menu_projects():
    return _pairs(project.list_projects())


def selectable_shots(n):
    """Shots offered by Pick Shot: Wedge Shots, or every shot when Wedge Shots is empty."""
    return shot_list(n, "wedge_shots") or project_shots(n)


# ---------------------------------------------------------------- HDA interface

def _menu(name, label, fn, help_text):
    pt = hou.StringParmTemplate(
        name, label, 1, default_value=("",),
        item_generator_script="import kpipe.scene as s\nreturn s.{}()".format(fn),
        item_generator_script_language=_PY, menu_type=hou.menuType.Normal,
        script_callback=_ON_CHANGE, script_callback_language=_PY)
    pt.setHelp(help_text)
    return pt


def _spacer(name, hide_when=None):
    pt = hou.LabelParmTemplate(name, "", column_labels=("",))
    pt.hideLabel(True)
    if hide_when:
        pt.setConditional(hou.parmCondType.HideWhen, hide_when)
    return pt


def row(name, *pts, hide_when=None, spacers=1):
    """One parm row: pts joined, then blank labels that take the spare width so fields stay short.

    More spacers = shorter fields (Houdini splits a joined row between its items).
    """
    for pt in pts:
        pt.setJoinWithNext(True)
    out = list(pts)
    for i in range(spacers):
        sp = _spacer("sp_{}{}".format(name, i or ""), hide_when)
        if i < spacers - 1:
            sp.setJoinWithNext(True)
        out.append(sp)
    return out


def _button(name, label, fn, help_text):
    pt = hou.ButtonParmTemplate(name, label,
                                script_callback="import kpipe.ui; kpipe.ui.{}(kwargs['node'])".format(fn),
                                script_callback_language=_PY)
    pt.setHelp(help_text)
    return pt


def _var(name, cls, help_text):
    pt = cls("var_" + name, "var_" + name, 1, default_expression=(_VAR_EXPR.format(name),),
             default_expression_language=(_PY,))
    pt.setHelp(help_text + " Live expression of the effective shot: the selected TOP work item's"
                           " shot when previewing one, otherwise the Current Shot parm.")
    return pt


def _display(name, label, help_text):
    """Status string kept up to date by refresh_status(); edits are restored."""
    pt = hou.StringParmTemplate(
        name, label, 1, default_value=("",),
        script_callback="import kpipe.scene; kpipe.scene.on_display_edit(kwargs['node'], kwargs['parm_name'])",
        script_callback_language=_PY)
    pt.setHelp(help_text)
    return pt


def _list(name, label, help_text):
    pt = hou.StringParmTemplate(name, label, 1, default_value=("",),
                                script_callback=_ON_CHANGE, script_callback_language=_PY)
    pt.setHelp(help_text)
    pt.setJoinWithNext(True)
    return pt


def _templates():
    """Parm layout. Each row ends with a blank label that takes the spare width (short fields)."""
    top = []
    proj = _menu("project", "Project", "menu_projects",
                 "Current project. Lists existing projects only; create new ones with the Create shelf tool.")
    top += row("project", proj, _button("btn_update", "Update Context", "sm_update_context",
                                        "Re-read project.json and refresh everything: ranges, variables,"
                                        " playbar and shot wedges."))
    shot = hou.StringParmTemplate("shot", "Current Shot", 1, default_value=("",),
                                  script_callback=_ON_CHANGE, script_callback_language=_PY)
    shot.setHelp("The shot or asset you are working in. Type a code (GRS_0010, fxGrass) or use Pick Shot"
                 " (lists Wedge Shots, or everything when Wedge Shots is empty). Unknown codes are rejected."
                 " Copy this parm to read the current shot elsewhere.")
    top += row("shot", shot, _button("btn_pick_shot", "Pick Shot...", "sm_select_shot",
                                     "Pick the current shot from a list."), spacers=3)
    last = hou.StringParmTemplate("last_shot", "last_shot", 1, default_value=("",))
    last.hide(True)
    top.append(last)

    ctx = hou.FolderParmTemplate("context", "Context", folder_type=hou.folderType.Simple)
    prng = hou.IntParmTemplate("project_range", "Project Range", 2, default_value=config.DEFAULT_RANGE,
                               naming_scheme=hou.parmNamingScheme.Base1,
                               script_callback=_ON_CHANGE, script_callback_language=_PY)
    prng.setHelp("The shot's range in project.json. Editing it saves it there.")
    crng = hou.IntParmTemplate("custom_range", "Custom Range", 2, default_value=config.DEFAULT_RANGE,
                               naming_scheme=hou.parmNamingScheme.Base1,
                               script_callback=_ON_CHANGE, script_callback_language=_PY)
    crng.setHelp("Working range of the current shot: drives var_start / var_end and the playbar"
                 " (Sync Playbar). Follows Project Range until you type a value; a typed range is"
                 " remembered per shot in this hip (switching back restores it, TOP shot wedges use it)."
                 " Reset forgets it.")
    link = hou.StringParmTemplate("custom_ranges", "custom_ranges", 1, default_value=("",))
    link.hide(True)
    artist = hou.StringParmTemplate("artist", "Artist", 1, default_value=(config.DEFAULT_ARTIST,))
    artist.setHelp("Name written into saved file names, e.g. artist. MCP sessions use mcp.")
    rows = (row("prange", prng, spacers=2)
            + row("crange", crng, _button("btn_reset_custom", "Reset", "sm_reset_custom",
                                          "Forget this shot's Custom Range and follow Project Range again."),
                    spacers=2)
            + [link]
            + row("artist", artist, spacers=3)
            + row("files",
                  _button("btn_open", "Open Latest", "sm_open_latest", "Open the newest work file of the current shot."),
                  _button("btn_save", "Save Version", "sm_save",
                          "Save the scene as the next version in the current shot's scenes folder (one click)."),
                  _button("btn_sync", "Sync Playbar", "sm_sync", "Set the playbar to Custom Range.")))
    for pt in rows:
        ctx.addParmTemplate(pt)

    wedge = hou.FolderParmTemplate("wedge", "Wedge", folder_type=hou.folderType.Simple)
    slice_on = hou.ToggleParmTemplate("enable_slice", "Enable Slice", default_value=False,
                                      script_callback=_ON_CHANGE, script_callback_language=_PY)
    slice_on.setHelp("Send only the Slice List to TOP shot wedges instead of all Wedge Shots.")
    sl = _list("slice_shots", "Slice List",
               "Shots sent to TOP shot wedges while Enable Slice is on; picked from Wedge Shots."
               " Empty = the current shot only.")
    sl.setConditional(hou.parmCondType.DisableWhen, "{ enable_slice == 0 }")
    pick_slice = _button("btn_pick_slice", "Pick Slice...", "sm_pick_slice",
                         "Open the shot picker for the Slice List (shows Wedge Shots only).")
    pick_slice.setConditional(hou.parmCondType.DisableWhen, "{ enable_slice == 0 }")
    rows = (row("wedge", _list("wedge_shots", "Wedge Shots",
                               "The hip's shot list (space separated). Pick Shot lists it, and TOP"
                               " shot wedges run it unless Enable Slice is on. Empty = the current shot only."),
                _button("btn_pick", "Pick Shots...", "sm_pick_shots", "Open the shot picker for Wedge Shots."))
            + [slice_on]
            + row("slice", sl, pick_slice)
            + row("sent", _display("wedge_list", "Sent to Wedge",
                                   "Shots the TOP shot wedges run right now. Display only."),
                  _button("btn_sync_wedge", "Sync Wedge", "sm_sync_wedge",
                          "Write the shots into every shot wedge TOP (done automatically"
                          " on every change; this is a safety net).")))
    for pt in rows:
        wedge.addParmTemplate(pt)

    var = hou.FolderParmTemplate("variables", "Variables", folder_type=hou.folderType.Simple)
    hint = hou.LabelParmTemplate("hint_vars", "", column_labels=(
        'Reference from other nodes, e.g. chs("/obj/scene_manager/var_cache")',))
    hint.hideLabel(True)
    rows = ([hint]
            + row("source", _display("var_source", "Source",
                                     "What drives the variables: the Current Shot parm, or a selected TOP"
                                     " work item. Display only; edits are restored."),
                  _button("btn_clear_wi", "Clear Work Item", "sm_clear_work_item",
                          "Deselect the TOP work item so the variables follow the Current Shot parm again."))
            + row("vshot", _var("shot", hou.StringParmTemplate, "Effective shot or asset code."), spacers=3)
            + [_var("dir", hou.StringParmTemplate,
                    "Shot folder: <project>/shot/<SEQ>/<SHOT> or <project>/asset/<category>/<asset>.")]
            + [_var(sub, hou.StringParmTemplate, "Subfolder <var_dir>/{}: {}.".format(sub, _SUB_HELP[sub]))
               for sub in config.ITEM_DIRS]
            + row("vstart", _var("start", hou.IntParmTemplate, "Start frame (Custom Range for the current shot)."))
            + row("vend", _var("end", hou.IntParmTemplate, "End frame (Custom Range for the current shot).")))
    for pt in rows:
        var.addParmTemplate(pt)
    return top + [ctx, wedge, var]


def save_instances(category, type_name):
    """Parm values of every node of a type: uninstalling its HDA resets them to defaults."""
    t = hou.nodeType(category, type_name)
    return [(n.path(), n.parmsAsData()) for n in t.instances()] if t else []


def restore_instances(saved):
    for path, data in saved:
        n = hou.node(path)
        if n is None:
            continue
        try:
            n.setParmsFromData(data)
        except Exception as e:
            print("kpipe: could not restore {}: {}".format(path, e))


def installed_definition(category, type_name, path):
    """The installed HDA definition of type_name when it comes from `path`, else None."""
    t = hou.nodeType(category, type_name)
    d = t.definition() if t else None
    if d is not None and os.path.normcase(os.path.abspath(d.libraryFilePath())) == \
            os.path.normcase(os.path.abspath(path)):
        return d
    return None


def interface(category, templates):
    """Stock subnet parms (hidden) + kpipe templates."""
    ptg = hou.nodeType(category, "subnet").parmTemplateGroup()
    for entry in ptg.entries():
        ptg.hide(entry, True)
    for pt in templates:
        ptg.append(pt)
    return ptg


def build_hda(path=config.SM_HDA):
    """(Re)generate the Scene Manager HDA file.

    When it is already installed from `path`, the definition is updated in place: no
    uninstall, so existing Scene Managers keep their values.
    """
    cat = hou.objNodeTypeCategory()
    d = installed_definition(cat, config.SM_TYPE, path)
    saved = []
    if d is None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        saved = save_instances(cat, config.SM_TYPE)
        if os.path.exists(path):
            hou.hda.uninstallFile(path)
            os.remove(path)
        tmp = hou.node("/obj").createNode("subnet", "kpipe_sm_build")
        asset = tmp.createDigitalAsset(name=config.SM_TYPE, hda_file_name=path,
                                       description="KPipe Scene Manager",
                                       min_num_inputs=0, max_num_inputs=0)
        d = asset.type().definition()
        asset.destroy()
    d.setParmTemplateGroup(interface(cat, _templates()))
    restore_instances(saved)
    d.addSection("OnCreated", _ON_CREATED)
    d.setExtraFileOption("OnCreated/IsPython", True)
    d.addSection("OnLoaded", _ON_LOADED)
    d.setExtraFileOption("OnLoaded/IsPython", True)
    d.setIcon("MISC_python")
    _remove_backup(path)
    return path


def _remove_backup(path):
    backup = os.path.join(os.path.dirname(path), "backup")
    if os.path.isdir(backup):
        for f in os.listdir(backup):
            os.remove(os.path.join(backup, f))
        os.rmdir(backup)


def ensure_hda():
    if hou.nodeType(hou.objNodeTypeCategory(), config.SM_TYPE):
        return
    if not os.path.exists(config.SM_HDA):
        build_hda()
    hou.hda.installFile(config.SM_HDA, change_oplibraries_file=False)


def on_created(n):
    others = [c for c in hou.node("/obj").children() if c.type() == n.type() and c != n]
    if others:
        n.destroy()
        if hou.isUIAvailable():
            hou.ui.displayMessage("This hip already has " + others[0].path(), title="kpipe")
        return
    n.setName(config.SM_NAME, unique_name=True)
    n.setColor(hou.Color(1, 0, 0))
    n.setUserData("nodeshape", "circle")
    n.setDisplayFlag(False)
    start_watch()


def get_or_create():
    ensure_hda()
    return node() or hou.node("/obj").createNode(config.SM_TYPE, config.SM_NAME)


# ---------------------------------------------------------------- callbacks

def _status_message(text):
    if hou.isUIAvailable():
        hou.ui.setStatusMessage(text, hou.severityType.Warning)


def _clean_list(n, name):
    """Normalize a list parm: registered spelling, known shots only, project order; Slice within Wedge."""
    pool = project_shots(n) if name == "wedge_shots" else shot_list(n, "wedge_shots")
    typed = n.evalParm(name).replace(",", " ").split()
    known = {_canonical(pool, s) for s in typed} - {None}
    unknown = [s for s in typed if _canonical(pool, s) is None]
    clean = " ".join(s for s in pool if s in known)
    if n.evalParm(name) != clean:
        n.parm(name).set(clean)
    if unknown:
        _status_message("Ignored (not in {}): {}".format(
            "project" if name == "wedge_shots" else "Wedge Shots", " ".join(unknown)))


def on_change(n, parm_name=None):
    """Keep project/shot valid, sync ranges with project.json and the playbar, sync wedges."""
    from . import tops
    if parm_name == "custom_range":  # remember a typed range for this shot; equal to Project Range = forget
        shot = n.evalParm("shot")
        if shot:
            ranges = custom_ranges(n)
            value = tuple(n.parmTuple("custom_range").eval())
            if value == tuple(n.parmTuple("project_range").eval()):
                ranges.pop(shot, None)
            else:
                ranges[shot] = value
            _set_custom_ranges(n, ranges)
        refresh_status(n)
        return
    proj = n.evalParm("project")
    if parm_name == "project":
        for name in LISTS + ("last_shot", "custom_ranges"):  # they belong to the previous project
            n.parm(name).set("")
    shots = project_shots(n) if project.find_project(proj) else []
    shot = n.evalParm("shot")
    canon = _canonical(shots, shot)
    if canon and canon != shot:
        shot = canon
        n.parm("shot").set(shot)
    if shot not in shots:
        last = n.evalParm("last_shot")
        if shot and parm_name != "project":
            _status_message("Unknown shot {!r}: kept {}".format(shot, last or "(none)"))
        shot = last if last in shots else ""
        n.parm("shot").set(shot)
    n.parm("last_shot").set(shot)

    if parm_name in LISTS + ("enable_slice",):
        for name in LISTS:
            _clean_list(n, name)
    if shot:
        if parm_name == "project_range":
            start, end = n.parmTuple("project_range").eval()
            project.set_range(proj, shot, start, end)
        else:
            info = project.item_info(_manifest(proj), shot)
            n.parmTuple("project_range").set((info["start"], info["end"]))
        custom = custom_ranges(n).get(shot)
        n.parmTuple("custom_range").set(custom or n.parmTuple("project_range").eval())
        if parm_name in (None, "shot", "project", "project_range"):
            sync_playbar(n)
        if parm_name in ("shot", "project"):
            reset_sims()
    tops.sync_wedges(n)
    refresh_status(n)


def reset_sims(root="/obj"):
    """Press Reset Simulation on every DOP network / solver under root.

    Shot Value results are Python expressions, so a shot switch does not dirty downstream
    nodes: SOPs re-evaluate on the next cook, but DOP caches would keep the previous shot's sim.
    """
    count = 0
    for node in hou.node(root).allSubChildren(recurse_in_locked_nodes=False):
        p = node.parm("resimulate")
        if p is not None and p.parmTemplate().type() == hou.parmTemplateType.Button:
            try:
                p.pressButton()
                count += 1
            except hou.Error:
                pass
    return count


def reset_custom_range(n=None):
    """Forget the current shot's Custom Range and follow Project Range again."""
    n = n or node()
    ranges = custom_ranges(n)
    ranges.pop(n.evalParm("shot"), None)
    _set_custom_ranges(n, ranges)
    n.parmTuple("custom_range").set(n.parmTuple("project_range").eval())
    sync_playbar(n)
    refresh_status(n)


def set_custom_range(start, end, n=None):
    """Set and remember the current shot's Custom Range (API / MCP use)."""
    n = n or node()
    n.parmTuple("custom_range").set((start, end))
    on_change(n, "custom_range")


def update_context(n=None):
    """Re-read project.json and refresh menus, ranges, variables, playbar and wedges."""
    n = n or node()
    _manifests.clear()
    for name in LISTS:
        _clean_list(n, name)
    on_change(n)
    sync_playbar(n)
    n.cook(force=True)
    return status(n, dep=False)


def pick_shots(shots, mode="replace", n=None, target="wedge_shots"):
    """Set a shot list (wedge_shots or slice_shots) and sync the wedges.

    mode: "add" (union with the list), "replace", or "clear".
    """
    n = n or node()
    if mode == "clear":
        picked = []
    elif mode == "add":
        picked = shot_list(n, target) + list(shots)
    else:
        picked = list(shots)
    n.parm(target).set(" ".join(picked))
    on_change(n, target)
    from . import tops
    return tops.find_wedges()


def sync_playbar(n=None):
    n = n or node()
    start, end = n.parmTuple("custom_range").eval()
    if end >= start and tuple(hou.playbar.frameRange()) != (start, end):
        hou.playbar.setFrameRange(start, end)
        hou.playbar.setPlaybackRange(start, end)
        hou.setFrame(start)


def ensure(proj, shot, artist=config.DEFAULT_ARTIST):
    """Create (or reuse) /obj/scene_manager and point it at project/shot (API / MCP use)."""
    n = get_or_create()
    n.parm("project").set(proj)
    n.parm("shot").set(shot)
    n.parm("artist").set(artist)
    on_change(n)
    return n


def set_shot(shot):
    """Switch the Scene Manager to another registered shot."""
    n = node()
    n.parm("shot").set(shot)
    on_change(n, "shot")
    return n.evalParm("var_dir")
