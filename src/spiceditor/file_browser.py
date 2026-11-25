import os
import shutil

from PyQt5.QtCore import QObject, QSortFilterProxyModel, Qt, pyqtSignal
from PyQt5.QtWidgets import (QFileDialog, QFileSystemModel, QHBoxLayout, QInputDialog, QLabel, QMenu,
                             QMessageBox, QPushButton, QTreeView, QVBoxLayout, QWidget)

# the files Spice can open; everything else is not shown
EXTENSIONS = (".txt", ".py", ".csv", ".yaml", ".json", ".sqlite", ".db")
HIDDEN_DIRS = ("__pycache__",)


class FileSystemModelWithTooltip(QFileSystemModel):
    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.ToolTipRole:
            return self.filePath(index)
        return super().data(index, role)


class FileFilterProxy(QSortFilterProxyModel):
    """Shows folders and the files with one of the given extensions, at
    every level of the tree. Extensions are compared ignoring case."""

    def __init__(self, extensions, parent=None):
        super().__init__(parent)
        self.extensions = {e.lower() for e in extensions}

    def filterAcceptsRow(self, row, parent):
        model = self.sourceModel()
        index = model.index(row, 0, parent)
        name = model.fileName(index)
        if model.isDir(index):
            return name not in HIDDEN_DIRS
        return os.path.splitext(name)[1].lower() in self.extensions


class FileBrowser(QWidget):
    class Signals(QObject):
        file_selected = pyqtSignal(str)
        directory_changed = pyqtSignal(str)

    def __init__(self, path, filters=None, hide_details=True):
        super().__init__()
        self.signals = self.Signals()
        self.path = path
        self.extensions = tuple(filters or EXTENSIONS)

        self.dirModel = FileSystemModelWithTooltip()
        self.proxy = FileFilterProxy(self.extensions, self)
        self.proxy.setSourceModel(self.dirModel)

        self.treeview = QTreeView()
        self.treeview.setModel(self.proxy)
        self.treeview.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeview.customContextMenuRequested.connect(self.show_context_menu)
        self.treeview.doubleClicked.connect(self.on_double_clicked)

        self.label = QLabel()
        self.button = QPushButton("...")
        self.button.setMaximumWidth(20)
        self.button.setFlat(True)
        self.button.clicked.connect(self.btn_path_clicked)

        vlayout = QVBoxLayout(self)
        vlayout.setSpacing(0)
        vlayout.setContentsMargins(0, 0, 0, 0)
        hb = QHBoxLayout()
        hb.addWidget(self.label)
        hb.addWidget(self.button)
        vlayout.addLayout(hb)
        vlayout.addWidget(self.treeview)

        if hide_details:
            for i in range(1, self.proxy.columnCount()):
                self.treeview.header().hideSection(i)

        self.set_root(path)

    # ------------------------------------------------------------------
    # paths <-> tree indexes (the tree shows the filter, not the model)
    # ------------------------------------------------------------------
    def path_of(self, index):
        return self.dirModel.filePath(self.proxy.mapToSource(index))

    def index_of(self, path):
        return self.proxy.mapFromSource(self.dirModel.index(path))

    # ------------------------------------------------------------------
    def set_root(self, path):
        if not os.path.isdir(path):
            return
        self.dirModel.setRootPath(path)
        self.treeview.setRootIndex(self.index_of(path))
        self.path = path
        self.label.setText("..." + path[-20:] if len(path) > 30 else path)
        self.label.setToolTip(path)

    def get_path(self):
        return self.path

    def btn_path_clicked(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory", self.path)
        if path:
            self.set_root(path)
            self.signals.directory_changed.emit(path)

    def on_double_clicked(self, index):
        path = self.path_of(index)
        if os.path.isfile(path) and os.path.splitext(path)[1].lower() in self.extensions:
            self.signals.file_selected.emit(path)

    def select(self, filename, emit=True):
        index = self.index_of(filename)
        if not index.isValid():
            return
        parent = index.parent()
        while parent.isValid():
            self.treeview.setExpanded(parent, True)
            parent = parent.parent()
        selection = self.treeview.selectionModel()
        blocked = selection.blockSignals(not emit)
        self.treeview.setCurrentIndex(index)
        selection.blockSignals(blocked)

    # ------------------------------------------------------------------
    # file operations: report errors instead of crashing Spice
    # ------------------------------------------------------------------
    def _fail(self, action, error):
        QMessageBox.warning(self, action, f"{action} failed:\n{error}")

    def show_context_menu(self, pos):
        index = self.treeview.indexAt(pos)
        if not index.isValid():
            return
        self.treeview.setCurrentIndex(index)
        path = self.path_of(index)
        menu = QMenu(self)
        delete = menu.addAction("Delete")
        move = menu.addAction("Move")
        chosen = menu.exec_(self.treeview.viewport().mapToGlobal(pos))
        if chosen == delete:
            self.delete_path(path)
        elif chosen == move:
            self.move_path(path)

    def delete_path(self, path):
        if QMessageBox.question(self, "Delete", f"Are you sure you want to delete {path}?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except OSError as e:
            self._fail("Delete", e)

    def move_path(self, path):
        target = QFileDialog.getExistingDirectory(self, "Select Directory", os.path.dirname(path))
        if not target:
            return
        try:
            shutil.move(path, target)
        except (OSError, shutil.Error) as e:
            self._fail("Move", e)

    def new_folder(self):
        # inside the selected folder if there is one, otherwise in the current directory
        parent = self.path
        selected = self.treeview.selectionModel().selectedIndexes()
        if selected and os.path.isdir(self.path_of(selected[0])):
            parent = self.path_of(selected[0])

        name, ok = QInputDialog.getText(self, "Folder Name", "Enter the folder name")
        name = name.strip()
        if not ok or not name:
            return
        if name in (".", "..") or "/" in name or (os.sep in name) or (os.altsep and os.altsep in name):
            QMessageBox.warning(self, "New folder", f"'{name}' is not a valid folder name.")
            return
        try:
            os.makedirs(os.path.join(parent, name), exist_ok=True)
        except OSError as e:
            self._fail("New folder", e)
