import os
import shutil

from PyQt5 import QtGui
from PyQt5.QtCore import QObject, pyqtSignal, QDir, QItemSelectionModel, QModelIndex, Qt
from PyQt5.QtWidgets import QWidget, QTreeView, QFileSystemModel, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QMenu, QMessageBox, QToolBar, QInputDialog


class Tree(QTreeView):
    delete_requested = pyqtSignal(str)

    def filter_rows(self):
        for i in range(self.model().rowCount(self.rootIndex())):
            child_index = self.model().index(i, 0, self.rootIndex())  # Get index of each row
            filename = self.model().data(child_index)  # Get file name
            if filename == "__pycache__":
                self.setRowHidden(i, self.rootIndex(), True)

    def contextMenuEvent(self, a0: QtGui.QContextMenuEvent) -> None:
        super().contextMenuEvent(a0)
        indexes = self.selectedIndexes()
        if indexes:
            index = self.indexAt(a0.pos())
            if index.isValid():
                dirModel = self.model()
                path = dirModel.fileInfo(index).absoluteFilePath()
                menu = QMenu()
                delete = menu.addAction("Delete")
                res = menu.exec_(self.viewport().mapToGlobal(a0.pos()))
                if res == delete:
                    self.delete_requested.emit(path)


class FileBrowser(QWidget):
    class Signals(QObject):
        file_selected = pyqtSignal(str)

    def __init__(self, path, filters=None, hide_details=True):
        super().__init__()
        if filters is None:
            filters = ["*.pdf"]
        self.signals = self.Signals()
        self.path = path
        self.treeview = Tree()
        self.treeview.delete_requested.connect(self.delete_requested)
        self.dirModel = QFileSystemModel()
        self.dirModel.directoryLoaded.connect(self.treeview.filter_rows)
        self.dirModel.setNameFilters(filters)
        self.dirModel.setNameFilterDisables(False)

        self.treeview.setModel(self.dirModel)
        self.treeview.setRootIndex(self.dirModel.setRootPath(path))

        vlayout = QVBoxLayout(self)
        vlayout.setSpacing(0)
        vlayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(vlayout)
        #tb = QToolBar()
        #tb.addAction("🗀", self.refresh)

        #vlayout.addWidget(tb)

        self.layout().addWidget(self.treeview)
        self.treeview.selectionModel().selectionChanged.connect(self.on_current_changed)
        self.treeview.doubleClicked.connect(self.on_double_clicked)

        if hide_details:
            for i in range(1, self.treeview.model().columnCount()):
                self.treeview.header().hideSection(i)

    def delete_requested(self, path):
        if QMessageBox.question(self, "Delete", f"Are you sure you want to delete {path}?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
            return
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)


    def on_double_clicked(self, index):
        # Map the proxy index to the source model index
        path = self.dirModel.fileInfo(index).absoluteFilePath()
        if os.path.isdir(path):
            return
        self.signals.file_selected.emit(path)

    def btn_up_clicked(self):
        index = self.treeview.rootIndex()
        if index.isValid():
            index = index.parent()
            self.set_root_index(index)

    def set_root(self, path):
        self.treeview.setRootIndex(self.dirModel.setRootPath(path))

    def set_root_index(self, index):
        self.treeview.setRootIndex(index)
        path = self.dirModel.fileInfo(index).absoluteFilePath()
        self.label.setText(path)

    def select(self, filename, emit=True):
        if not emit:
            self.treeview.selectionModel().blockSignals(True)
        index = self.dirModel.index(filename)
        indices = []
        while index.isValid():
            indices.append(index)
            index = index.parent()

        for index in reversed(indices):
            self.treeview.setExpanded(index, True)

        self.treeview.setCurrentIndex(index)
        self.treeview.selectionModel().blockSignals(False)

    def on_current_changed(self, selected, deselected):
        pass
        # if deselected.indexes():
        #     print("deselected1", deselected.indexes())
        #     # Check if the deselected index is valid
        #     for index in deselected.indexes():
        #         if not os.path.isfile(self.dirModel.filePath(index)):
        #             self.treeview.clearSelection()
        #             return
        #
        # if selected is None or len(selected.indexes()) < 1:
        #     return
        # path = self.dirModel.fileInfo(selected.indexes()[0]).absoluteFilePath()
        # # self.listview.setRootIndex(self.fileModel.setRootPath(path))
        # if os.path.isfile(path):
        #     self.signals.file_selected.emit(path)

    def new_folder(self):
        current_path = self.dirModel.rootPath()

        # If the toolbar refresh button was clicked with no arguments,
        # show the folder creation dialog
        folder_name, ok = QInputDialog.getText(self, "Folder Name", "Enter the folder name")
        if ok and folder_name:
            new_folder_path = os.path.join(self.path, folder_name)
            os.makedirs(new_folder_path, exist_ok=True)
            self.dirModel.setRootPath("")
            self.dirModel.setRootPath(current_path)
