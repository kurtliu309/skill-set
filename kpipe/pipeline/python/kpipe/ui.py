"""Shelf and Scene Manager button entry points."""

import os

import hou

from . import project, scene

TITLE = "kpipe"


class Cancel(Exception):
    pass


def _msg(text, severity=hou.severityType.Message):
    hou.ui.displayMessage(text, title=TITLE, severity=severity)


def _run(fn):
    """Run a UI action; Cancel is silent, anything else becomes an error box."""
    try:
        return fn()
    except Cancel:
        return None
    except Exception as e:
        _msg(str(e), hou.severityType.Error)


def _confirm_unsaved():
    if not hou.hipFile.hasUnsavedChanges():
        return
    i = hou.ui.displayMessage("Current hip has unsaved changes:\n" + hou.hipFile.path(),
                              buttons=("Save", "Discard", "Cancel"), close_choice=2, title=TITLE)
    if i == 2:
        raise Cancel()
    if i == 0:
        hou.hipFile.save()


# ---------------------------------------------------------------- shelf

def create():
    def flow():
        from . import create_ui
        create_ui.show()
    _run(flow)


def open_work_file():
    def flow():
        from . import open_ui
        open_ui.show()
    _run(flow)


def scene_manager():
    """Create /obj/scene_manager if missing, then select it so its parameters show."""
    def flow():
        n = scene.get_or_create()
        n.setSelected(True, clear_all_selected=True)
        n.setCurrent(True)
        pane = hou.ui.paneTabOfType(hou.paneTabType.Parm)
        if pane:
            pane.setCurrentNode(n)
    _run(flow)


def save_version():
    """One click: save the next version, then show where it went."""
    _run(lambda: _msg("Saved\n" + project.save_version()))


def snapshot():
    def flow():
        from . import flipbook
        flipbook.snapshot()
    _run(flow)


def shot_wedge():
    """Build the shot-wedge TOP template for the selected Labs File Cache.

    Without a selection, the scene's only kpipe cache (cache.create_cache) is used.
    """
    def flow():
        from . import tops, cache
        sel = [n for n in hou.selectedNodes() if n.type().name().startswith("labs::filecache")]
        if not sel:
            tagged = cache.tagged_caches()
            sel = tagged if len(tagged) == 1 else []
        net = tops.build_shot_wedge(sel[0] if sel else None)
        net.setSelected(True, clear_all_selected=True)
        hint = "" if sel else "\n\nNo Labs File Cache was selected: set ROP Path on cache_shots."
        _msg("Built {} (see the readme note inside).{}".format(net.path(), hint))
    _run(flow)


# ---------------------------------------------------------------- Scene Manager buttons

def sm_open_latest(n):
    def flow():
        proj, shot = n.evalParm("project"), n.evalParm("shot")
        path = project.latest_hip(proj, shot) if proj and shot else None
        if not path:
            raise ValueError("No work file for this shot yet. Create one with the Create shelf tool.")
        _confirm_unsaved()
        project.open_hip(path, force=True)
    _run(flow)


def sm_save(n):
    save_version()


def sm_sync(n):
    _run(lambda: scene.sync_playbar(n))


def sm_update_context(n):
    _run(lambda: hou.ui.setStatusMessage("Context updated: " + scene.update_context(n)))


def sm_select_shot(n):
    def flow():
        from . import shot_picker
        shot_picker.select(n)
    _run(flow)


def sm_reset_custom(n):
    _run(lambda: scene.reset_custom_range(n))


def sm_pick_shots(n):
    def flow():
        from . import shot_picker
        shot_picker.show(n, "wedge_shots")
    _run(flow)


def sm_pick_slice(n):
    def flow():
        from . import shot_picker
        shot_picker.show(n, "slice_shots")
    _run(flow)


def sm_sync_wedge(n):
    def flow():
        from . import tops
        wedges = tops.sync_wedges(n)
        hou.ui.setStatusMessage("Synced {} shot wedge(s): {}".format(len(wedges), scene.sent_list(n)))
    _run(flow)


def sm_clear_work_item(n):
    _run(scene.clear_work_item)
