"""KPipe - Open Work File window: browse projects, shots / assets and their versions.

Project -> shot / asset tree (Shots by sequence, Assets by category) -> versions, newest
first and selected. Double-click or Open loads the hip (asking about unsaved changes first)
and closes the window. The last opened project / shot is remembered across sessions.
"""

import time

import hou
from PySide6 import QtCore, QtWidgets

from . import config, project, shot_picker

TITLE = "KPipe - Open Work File"
_CODE = QtCore.Qt.UserRole
_window = None


def _settings():
    return QtCore.QSettings("kpipe", "open_work_file")


def visible_codes(codes, search):
    """Codes matching the search text (case-insensitive substring)."""
    text = search.strip().lower()
    return [c for c in codes if text in c.lower()]


def filter_versions(versions, artist, only_mine):
    return [v for v in versions if v["artist"] == artist] if only_mine else list(versions)


class OpenWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent or hou.qt.mainWindow(), QtCore.Qt.Window)
        self.setWindowTitle(TITLE)
        self.resize(760, 480)
        root = QtWidgets.QVBoxLayout(self)

        top = QtWidgets.QHBoxLayout()
        self.project = QtWidgets.QComboBox()
        self.artist = QtWidgets.QLineEdit(config.DEFAULT_ARTIST)
        self.artist.setMaximumWidth(120)
        self.only_mine = QtWidgets.QCheckBox("Only mine")
        self.only_mine.setToolTip("List only versions saved by the artist on the left.")
        top.addWidget(QtWidgets.QLabel("Project"))
        top.addWidget(self.project, 1)
        top.addSpacing(16)
        top.addWidget(QtWidgets.QLabel("Artist"))
        top.addWidget(self.artist)
        top.addWidget(self.only_mine)
        root.addLayout(top)

        split = QtWidgets.QSplitter()
        left = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(left)
        lay.setContentsMargins(0, 0, 0, 0)
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Search, e.g. 0040 or grass")
        self.search.setClearButtonEnabled(True)
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(("Shot / Asset", "Range"))
        self.tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        lay.addWidget(self.search)
        lay.addWidget(self.tree)
        self.table = QtWidgets.QTreeWidget()
        self.table.setRootIsDecorated(False)
        self.table.setHeaderLabels(("Version", "Artist", "Modified"))
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 100)
        split.addWidget(left)
        split.addWidget(self.table)
        split.setSizes((330, 410))
        root.addWidget(split, 1)

        self.path = QtWidgets.QLabel("")
        self.path.setStyleSheet("color: gray;")
        root.addWidget(self.path)
        row = QtWidgets.QHBoxLayout()
        row.addStretch()
        self.btn_open = QtWidgets.QPushButton("Open")
        self.btn_open.setDefault(True)
        cancel = QtWidgets.QPushButton("Cancel")
        row.addWidget(self.btn_open)
        row.addWidget(cancel)
        root.addLayout(row)

        self.leaves = {}
        self.project.addItems(project.list_projects())
        s = _settings()
        last_proj, self.last_code = s.value("project", ""), s.value("code", "")
        if last_proj in project.list_projects():
            self.project.setCurrentText(last_proj)

        self.project.currentTextChanged.connect(self.on_project)
        self.search.textChanged.connect(self.on_search)
        self.tree.currentItemChanged.connect(lambda *_: self.on_code())
        self.artist.textChanged.connect(self.on_code)
        self.only_mine.toggled.connect(self.on_code)
        self.table.currentItemChanged.connect(lambda *_: self.on_version())
        self.table.itemDoubleClicked.connect(lambda *_: self.open())
        self.btn_open.clicked.connect(self.open)
        cancel.clicked.connect(self.close)
        self.on_project()

    # ------------------------------------------------------------ state

    def _proj(self):
        return self.project.currentText()

    def code(self):
        item = self.tree.currentItem()
        return item.data(0, _CODE) if item is not None else None

    def selected(self):
        item = self.table.currentItem()
        return item.data(0, _CODE) if item is not None else None

    def on_project(self, *_):
        self.tree.clear()
        proj = self._proj()
        self.leaves = shot_picker._fill(self.tree, project.items(proj), project.load(proj)) if proj else {}
        target = self.leaves.get(self.last_code)
        if target is None and self.leaves:
            target = next(iter(self.leaves.values()))
        self.on_search()
        if target is not None:
            self.tree.setCurrentItem(target)
        else:
            self.on_code()

    def on_search(self, *_):
        shown = set(visible_codes(self.leaves, self.search.text()))
        for code, leaf in self.leaves.items():
            leaf.setHidden(code not in shown)
        for i in range(self.tree.topLevelItemCount()):  # hide empty groups
            kind = self.tree.topLevelItem(i)
            any_kind = False
            for j in range(kind.childCount()):
                grp = kind.child(j)
                any_grp = any(not grp.child(k).isHidden() for k in range(grp.childCount()))
                grp.setHidden(not any_grp)
                any_kind = any_kind or any_grp
            kind.setHidden(not any_kind)

    def on_code(self, *_):
        self.table.clear()
        proj, code = self._proj(), self.code()
        if not (proj and code):
            self.on_version()
            return
        found = filter_versions(project.hip_versions(proj, code), self.artist.text().strip(),
                                self.only_mine.isChecked())
        for v in found:
            item = QtWidgets.QTreeWidgetItem(self.table, (
                "v{:03d}".format(v["ver"]), v["artist"],
                time.strftime("%Y-%m-%d %H:%M", time.localtime(v["mtime"]))))
            item.setData(0, _CODE, v["path"])
        if found:
            self.table.setCurrentItem(self.table.topLevelItem(0))
        self.on_version()

    def on_version(self):
        path, proj = self.selected(), self._proj()
        self.btn_open.setEnabled(bool(path))
        if path:
            self.path.setText(proj + path[len(project.require_project(proj)):])
        elif self.code():
            self.path.setText("No work files" + (" by " + self.artist.text().strip()
                                                 if self.only_mine.isChecked() else "") + ".")
        else:
            self.path.setText("")

    # ------------------------------------------------------------ action

    def open(self):
        from . import ui
        path, proj, code = self.selected(), self._proj(), self.code()
        if not path:
            return
        try:
            ui._confirm_unsaved()
        except ui.Cancel:
            return
        try:
            project.open_hip(path, force=True)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, TITLE, str(e))
            return
        s = _settings()
        s.setValue("project", proj)
        s.setValue("code", code)
        self.close()


def show():
    global _window
    if _window is None or not _window.isVisible():
        _window = OpenWindow()
    _window.show()
    _window.raise_()
    _window.activateWindow()
    return _window
