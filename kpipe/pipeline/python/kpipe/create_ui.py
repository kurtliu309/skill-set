"""KPipe - Create window: new projects, shots / assets and first work files.

Shots are typed as Sequence (GRS) + number (0050 -> GRS_0050); assets as Category (fx) +
name (Grass -> fxGrass).

A small non-modal PySide6 window parented to Houdini's main window. Fields validate as you
type, a preview shows exactly what will be created, and every action asks for confirmation.
"""

import hou
from PySide6 import QtCore, QtWidgets

from . import config, project

_window = None


def _hint(text):
    label = QtWidgets.QLabel(text)
    label.setStyleSheet("color: gray;")
    return label


class CreateWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent or hou.qt.mainWindow(), QtCore.Qt.Window)
        self.setWindowTitle("KPipe - Create")
        self.setMinimumWidth(560)
        root = QtWidgets.QVBoxLayout(self)

        # project
        box = QtWidgets.QGroupBox("Project")
        form = QtWidgets.QGridLayout(box)
        self.project = QtWidgets.QComboBox(editable=True)
        self.project.setToolTip("Pick an existing project or type a new project code.")
        self.loc_projects = QtWidgets.QRadioButton("Projects folder")
        self.loc_test = QtWidgets.QRadioButton("Test playground")
        self.loc_projects.setChecked(True)
        self.loc_projects.setToolTip(config.ROOT)
        self.loc_test.setToolTip(config.PLAYGROUND)
        self.btn_project = QtWidgets.QPushButton("Create Project")
        form.addWidget(QtWidgets.QLabel("Project"), 0, 0)
        form.addWidget(self.project, 0, 1, 1, 2)
        form.addWidget(_hint("e.g. grass (lowercase letters, digits, _)"), 1, 1, 1, 2)
        form.addWidget(self.loc_projects, 2, 1)
        form.addWidget(self.loc_test, 2, 2)
        form.addWidget(self.btn_project, 3, 2)
        root.addWidget(box)

        # shot / asset
        box = QtWidgets.QGroupBox("Shot / Asset")
        form = QtWidgets.QGridLayout(box)
        self.kind_shot = QtWidgets.QRadioButton("Shot")
        self.kind_asset = QtWidgets.QRadioButton("Asset")
        self.kind_shot.setChecked(True)
        self.group_label = QtWidgets.QLabel("Sequence")
        self.group = QtWidgets.QComboBox(editable=True)
        self.name_label = QtWidgets.QLabel("Shot")
        self.name = QtWidgets.QLineEdit()
        self.name_hint = _hint("")
        self.start, self.end = QtWidgets.QSpinBox(), QtWidgets.QSpinBox()
        for spin, value in ((self.start, config.DEFAULT_RANGE[0]), (self.end, config.DEFAULT_RANGE[1])):
            spin.setRange(-100000, 1000000)
            spin.setValue(value)
        self.shot_preview = _hint("")
        self.btn_shot = QtWidgets.QPushButton("Register")
        kind = QtWidgets.QHBoxLayout()
        kind.addWidget(self.kind_shot)
        kind.addWidget(self.kind_asset)
        kind.addStretch()
        form.addWidget(QtWidgets.QLabel("Type"), 0, 0)
        form.addLayout(kind, 0, 1, 1, 3)
        form.addWidget(self.group_label, 1, 0)
        form.addWidget(self.group, 1, 1)
        form.addWidget(self.name_label, 1, 2)
        form.addWidget(self.name, 1, 3)
        form.addWidget(self.name_hint, 2, 1, 1, 3)
        rng = QtWidgets.QHBoxLayout()
        rng.addWidget(self.start)
        rng.addWidget(QtWidgets.QLabel("-"))
        rng.addWidget(self.end)
        rng.addStretch()
        form.addWidget(QtWidgets.QLabel("Range"), 3, 0)
        form.addLayout(rng, 3, 1, 1, 3)
        form.addWidget(self.shot_preview, 4, 1, 1, 3)
        form.addWidget(self.btn_shot, 5, 3)
        root.addWidget(box)

        # work file
        box = QtWidgets.QGroupBox("Work file")
        form = QtWidgets.QGridLayout(box)
        self.wf_shot = QtWidgets.QComboBox()
        self.wf_current = QtWidgets.QRadioButton("Current scene")
        self.wf_empty = QtWidgets.QRadioButton("Empty scene")
        self.wf_current.setChecked(True)
        self.artist = QtWidgets.QLineEdit(config.DEFAULT_ARTIST)
        self.wf_preview = _hint("")
        self.btn_wf = QtWidgets.QPushButton("Create Work File")
        form.addWidget(QtWidgets.QLabel("Shot / Asset"), 0, 0)
        form.addWidget(self.wf_shot, 0, 1, 1, 2)
        form.addWidget(QtWidgets.QLabel("Start from"), 1, 0)
        form.addWidget(self.wf_current, 1, 1)
        form.addWidget(self.wf_empty, 1, 2)
        form.addWidget(QtWidgets.QLabel("Artist"), 2, 0)
        form.addWidget(self.artist, 2, 1, 1, 2)
        form.addWidget(self.wf_preview, 3, 1, 1, 2)
        form.addWidget(self.btn_wf, 4, 2)
        root.addWidget(box)

        self.status = QtWidgets.QLabel("")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        self.project.addItems(project.list_projects())
        self.project.setCurrentText("")
        self.project.currentTextChanged.connect(self.on_project)
        self.kind_shot.toggled.connect(self.on_kind)
        self.group.currentTextChanged.connect(self.on_group)
        self.name.textChanged.connect(self.refresh)
        self.wf_shot.currentTextChanged.connect(self.refresh)
        self.artist.textChanged.connect(self.refresh)
        self.btn_project.clicked.connect(self.create_project)
        self.btn_shot.clicked.connect(self.create_shot)
        self.btn_wf.clicked.connect(self.create_work_file)
        self.on_project()

    # ------------------------------------------------------------ state

    def _proj(self):
        return self.project.currentText().strip()

    def _is_shot(self):
        return self.kind_shot.isChecked()

    def _exists(self):
        return bool(project.find_project(self._proj()))

    def on_project(self, *_):
        proj = self._proj()
        self.wf_shot.clear()
        if self._exists():
            self.wf_shot.addItems(project.items(proj))
            start, end = project.default_range(proj)
            self.start.setValue(start)
            self.end.setValue(end)
        self.on_kind()

    def on_kind(self, *_):
        """Shot: Sequence + number. Asset: Category + name."""
        shot = self._is_shot()
        proj = self._proj()
        self.group_label.setText("Sequence" if shot else "Category")
        self.name_label.setText("Number" if shot else "Name")
        self.group.blockSignals(True)
        self.group.clear()
        if self._exists():
            self.group.addItems(project.sequences(proj) if shot else project.categories(proj))
        elif not shot:
            self.group.addItems(config.ASSET_CATEGORIES)
        self.group.setToolTip("Pick or type a sequence: 3 capital letters, e.g. GRS." if shot else
                              "Pick or type a category: lowercase letters, e.g. fx.")
        self.name.setPlaceholderText("0010" if shot else "Grass")
        self.name_hint.setText("Shot number (step 10; insert with e.g. 0015). Code: <SEQ>_<number>."
                               if shot else "Asset name. Code: <category><Name>, e.g. fxGrass.")
        self.group.blockSignals(False)
        self.name.clear()
        self.on_group()

    def on_group(self, *_):
        """Suggest the next shot number of the sequence."""
        proj, seq = self._proj(), self.group.currentText().strip()
        if self._is_shot() and self._exists() and project.SEQ_RE.fullmatch(seq):
            self.name.setText("{:04d}".format(project.next_shot_number(proj, seq)))
        self.refresh()

    @staticmethod
    def _rel(proj, path):
        """Path relative to the project folder, e.g. <proj>/shot/RGS/RGS_0010 (fits the window)."""
        return proj + path[len(project.require_project(proj)):]

    def code(self):
        """Code being registered (GRS_0050 / fxGrass), or "" while the fields are invalid."""
        grp, name = self.group.currentText().strip(), self.name.text().strip()
        if self._is_shot():
            if project.SEQ_RE.fullmatch(grp) and name.isdigit() and len(name) <= 4:
                return project.shot_code(grp, name)
            return ""
        code = project.asset_code(grp, name)
        return code if project.CATEGORY_RE.fullmatch(grp) and project.ASSET_RE.fullmatch(code) else ""

    def refresh(self, *_):
        proj = self._proj()
        exists = self._exists()
        valid_proj = bool(project.PROJECT_RE.fullmatch(proj))
        self.btn_project.setEnabled(valid_proj and not exists)
        self.loc_projects.setEnabled(not exists)
        self.loc_test.setEnabled(not exists)

        code = self.code()
        taken = exists and bool(code) and code in project.items(proj)
        shot_ok = exists and bool(code) and not taken
        self.btn_shot.setEnabled(shot_ok)
        self.btn_shot.setText("Register Shot" if self._is_shot() else "Register Asset")
        self.shot_preview.setText("Will create {}: {}/{{{}}}".format(
            code, self._rel(proj, project.item_dir(proj, code)), ",".join(config.ITEM_DIRS)) if shot_ok else "")

        wf = self.wf_shot.currentText()
        artist = self.artist.text().strip()
        latest = project.latest_hip(proj, wf) if exists and wf else None
        wf_ok = exists and bool(wf) and not latest and bool(project.ARTIST_RE.fullmatch(artist))
        self.btn_wf.setEnabled(wf_ok)
        self.wf_preview.setText(
            "Will save: " + self._rel(proj, project.next_hip(project.scenes_dir(proj, wf), wf, artist))
            if wf_ok else "")

        typed = self.name.text().strip()
        if not proj:
            msg = "Pick a project or type a new project code."
        elif not valid_proj:
            msg = "Invalid project code: use lowercase letters, digits and _ (start with a letter)."
        elif not exists:
            msg = "New project. Choose a location and press Create Project."
        elif typed and not code:
            msg = ("Invalid shot: sequence = 3 capitals (GRS), number = up to 4 digits (0010)."
                   if self._is_shot() else
                   "Invalid asset: category = lowercase letters (fx), name = letters/digits (Grass).")
        elif taken:
            msg = "{} already exists.".format(code)
        elif latest:
            msg = "{} already has work files (latest: {}). Use the Scene Manager to open it.".format(
                wf, latest.rsplit("/", 1)[-1])
        else:
            msg = "Ready."
        self.status.setText(msg)

    def _confirm(self, text):
        return QtWidgets.QMessageBox.question(self, "KPipe - Create", text) == QtWidgets.QMessageBox.Yes

    def _run(self, fn):
        try:
            fn()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "KPipe - Create", str(e))

    # ------------------------------------------------------------ actions

    def create_project(self):
        proj, test = self._proj(), self.loc_test.isChecked()

        def go():
            if self._confirm("Create project?\n\n{}/".format(project.project_dir(proj, test))):
                project.new_project(proj, test)
                self.project.addItem(proj)
                self.on_project()
        self._run(go)

    def create_shot(self):
        proj, code = self._proj(), self.code()
        start, end = self.start.value(), self.end.value()
        kind = "shot" if self._is_shot() else "asset"

        def go():
            if end < start:
                raise ValueError("End frame is before start frame.")
            if self._confirm("Register {} {} ({}-{})?\n\n{}/{{{}}}".format(
                    kind, code, start, end, project.item_dir(proj, code), ",".join(config.ITEM_DIRS))):
                project.new_item(proj, code, start, end)
                group = self.group.currentText().strip()
                self.on_project()
                self.group.setCurrentText(group)
                self.wf_shot.setCurrentText(code)
        self._run(go)

    def create_work_file(self):
        proj, shot, artist = self._proj(), self.wf_shot.currentText(), self.artist.text().strip()
        empty = self.wf_empty.isChecked()

        def go():
            target = project.next_hip(project.scenes_dir(proj, shot), shot, artist)
            what = "an EMPTY scene" if empty else "the CURRENT scene"
            if not self._confirm("Save {} as\n\n{}\n\nand point the Scene Manager at {}?".format(what, target, shot)):
                return
            if empty and hou.hipFile.hasUnsavedChanges():
                choice = QtWidgets.QMessageBox.question(
                    self, "KPipe - Create", "Current hip has unsaved changes. Save it first?",
                    QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel)
                if choice == QtWidgets.QMessageBox.Cancel:
                    return
                if choice == QtWidgets.QMessageBox.Save:
                    hou.hipFile.save()
            path = project.new_work_file(proj, shot, artist, empty)
            self.refresh()
            self.status.setText("Saved " + path)
        self._run(go)


def show():
    global _window
    if _window is None or not _window.isVisible():
        _window = CreateWindow()
    _window.show()
    _window.raise_()
    _window.activateWindow()
    return _window
