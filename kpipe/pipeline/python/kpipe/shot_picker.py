"""KPipe - shot dialogs for the Scene Manager.

select(): single choice, sets the current shot (Wedge Shots, or every shot when empty).

show(): Pick Shots dialog for the shot lists.

target="wedge_shots": pick from every shot of the project (the hip's Wedge Shots list).
target="slice_shots": pick from Wedge Shots only (the Slice List sent to TOP shot wedges).

Two groups: Shots (by sequence) and Assets (by category). Shots already in the list are
shown in bold with a "listed" mark; check shots, then Add to List (union) or Replace List.
Clear List empties it.
"""

import hou
from PySide6 import QtCore, QtGui, QtWidgets

from . import project, scene

_CHECKABLE = QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled
_CODE = QtCore.Qt.UserRole
_LABELS = {"wedge_shots": "Wedge Shots", "slice_shots": "Slice List"}


def _fill(tree, codes, data, extra=None, checkable=False):
    """Shots / Assets > sequence / category > code. Returns {code: leaf item}.

    extra(code) gives the text of the columns after Range.
    """
    flags = (_CHECKABLE | QtCore.Qt.ItemIsAutoTristate) if checkable else QtCore.Qt.ItemIsEnabled
    groups, leaves = {}, {}
    for code in codes:
        kind = "Shots" if project.is_shot(code) else "Assets"
        for key, parent, label in ((kind, tree, kind), ((kind, project.group(code)), None, project.group(code))):
            if key not in groups:
                item = QtWidgets.QTreeWidgetItem(parent if parent is not None else groups[kind], (label,))
                item.setFlags(flags)
                if checkable:
                    item.setCheckState(0, QtCore.Qt.Unchecked)
                groups[key] = item
        info = project.item_info(data, code)
        leaf = QtWidgets.QTreeWidgetItem(groups[(kind, project.group(code))],
                                         (code, "{}-{}".format(info["start"], info["end"]))
                                         + tuple(extra(code) if extra else ()))
        leaf.setData(0, _CODE, code)
        if checkable:
            leaf.setFlags(_CHECKABLE)
            leaf.setCheckState(0, QtCore.Qt.Unchecked)
        leaves[code] = leaf
    tree.expandAll()
    return leaves


def _bold(item):
    font = QtGui.QFont()
    font.setBold(True)
    for col in range(item.columnCount()):
        item.setFont(col, font)


class ShotPicker(QtWidgets.QDialog):
    def __init__(self, n, target="wedge_shots", parent=None):
        super().__init__(parent or hou.qt.mainWindow())
        self.n, self.target = n, target
        self.title = "KPipe - Pick " + _LABELS[target]
        self.setWindowTitle(self.title)
        self.setMinimumSize(420, 480)
        proj = n.evalParm("project")
        listed = scene.shot_list(n, target)
        pool = scene.project_shots(n) if target == "wedge_shots" else scene.shot_list(n, "wedge_shots")
        data = project.load(proj)
        root = QtWidgets.QVBoxLayout(self)

        text = "Project: {}\n{} now: {}".format(proj, _LABELS[target], " ".join(listed) or "(empty)")
        if target == "slice_shots":
            text += "\nShowing Wedge Shots only."
        label = QtWidgets.QLabel(text)
        label.setWordWrap(True)
        root.addWidget(label)

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(("Shot", "Range", ""))
        self.tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.leaves = _fill(self.tree, pool, data, lambda c: ("listed" if c in listed else "",), checkable=True)
        for code in listed:
            if code in self.leaves:
                _bold(self.leaves[code])
        root.addWidget(self.tree)

        row = QtWidgets.QHBoxLayout()
        for text, slot in (("Check All", lambda: self._check_all(QtCore.Qt.Checked)),
                           ("Uncheck All", lambda: self._check_all(QtCore.Qt.Unchecked))):
            btn = QtWidgets.QPushButton(text)
            btn.clicked.connect(slot)
            row.addWidget(btn)
        row.addStretch()
        root.addLayout(row)

        row = QtWidgets.QHBoxLayout()
        buttons = (("Add to List", "Add the checked shots to the list.", "add"),
                   ("Replace List", "Use only the checked shots.", "replace"),
                   ("Clear List", "Empty the list (the wedges then run the current shot).", "clear"))
        for text, tip, mode in buttons:
            btn = QtWidgets.QPushButton(text)
            btn.setToolTip(tip)
            btn.clicked.connect(lambda _=False, m=mode: self.apply(m))
            row.addWidget(btn)
        cancel = QtWidgets.QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        root.addLayout(row)

    def _check_all(self, state):
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setCheckState(0, state)

    def checked(self):
        return [code for code, it in self.leaves.items() if it.checkState(0) == QtCore.Qt.Checked]

    def apply(self, mode):
        shots = self.checked()
        if mode != "clear" and not shots:
            QtWidgets.QMessageBox.warning(self, self.title, "Check at least one shot.")
            return
        try:
            wedges = scene.pick_shots(shots, mode, self.n, self.target)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, self.title, str(e))
            return
        hou.ui.setStatusMessage("Sent to wedge: {} (synced {} wedge{})".format(
            scene.sent_list(self.n), len(wedges), "" if len(wedges) == 1 else "s"))
        self.accept()


class ShotSelect(QtWidgets.QDialog):
    """Single choice: pick the current shot. Double-click or OK switches, Cancel keeps it."""

    def __init__(self, n, parent=None):
        super().__init__(parent or hou.qt.mainWindow())
        self.n = n
        self.setWindowTitle("KPipe - Pick Shot")
        self.setMinimumSize(420, 480)
        proj, current = n.evalParm("project"), n.evalParm("shot")
        data = project.load(proj)
        root = QtWidgets.QVBoxLayout(self)
        root.addWidget(QtWidgets.QLabel("Project: {}\nCurrent: {}".format(proj, current or "(none)")))

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(("Shot", "Range"))
        self.tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        leaves = _fill(self.tree, scene.selectable_shots(n), data)
        if current in leaves:
            _bold(leaves[current])
            self.tree.setCurrentItem(leaves[current])
        self.tree.itemDoubleClicked.connect(lambda item, _col: self.apply(item))
        root.addWidget(self.tree)

        row = QtWidgets.QHBoxLayout()
        row.addStretch()
        ok = QtWidgets.QPushButton("OK")
        ok.setDefault(True)
        ok.clicked.connect(lambda: self.apply(self.tree.currentItem()))
        cancel = QtWidgets.QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        row.addWidget(ok)
        row.addWidget(cancel)
        root.addLayout(row)

    def apply(self, item):
        code = item.data(0, _CODE) if item is not None else None
        if not code:  # nothing or a group row
            return
        try:
            self.n.parm("shot").set(code)
            scene.on_change(self.n, "shot")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, self.windowTitle(), str(e))
            return
        self.accept()


def select(n=None):
    """Open the single-choice Pick Shot dialog for the Scene Manager's current shot."""
    n = n or scene.node()
    if n is None or not n.evalParm("project"):
        raise RuntimeError("Set up the Scene Manager (project) first")
    return ShotSelect(n).exec()


def show(n=None, target="wedge_shots"):
    n = n or scene.node()
    if n is None or not n.evalParm("project"):
        raise RuntimeError("Set up the Scene Manager (project / shot) first")
    if target == "slice_shots" and not scene.shot_list(n, "wedge_shots"):
        raise RuntimeError("Wedge Shots is empty: pick Wedge Shots first, the Slice List is picked from them")
    return ShotPicker(n, target).exec()
