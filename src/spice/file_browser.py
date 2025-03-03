import os
import shutil

from PyQt5 import QtGui
from PyQt5.QtCore import pyqtSignal, QObject, Qt, QDir, QSortFilterProxyModel
from PyQt5.QtWidgets import QWidget, QFileSystemModel, QMenu, QLabel, QToolBar, QMessageBox, QTreeView, QVBoxLayout, \
    QInputDialog


class Tree(QTreeView):
    delete_requested = pyqtSignal(str)

    # def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
    #     print("mousePressEvent")
    #     if e.button() != Qt.RightButton:
    #         super().mousePressEvent(e)

    def contextMenuEvent(self, a0: QtGui.QContextMenuEvent) -> None:
        super().contextMenuEvent(a0)
        return
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


class PycacheFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.excluded_dirs = ["__pycache__"]

    def filterAcceptsRow(self, source_row, source_parent):
        source_model = self.sourceModel()
        source_index = source_model.index(source_row, 0, source_parent)

        if not source_index.isValid():
            return True

        # Get file info and check if it's in excluded list
        file_path = source_model.filePath(source_index)
        dir_name = os.path.basename(file_path)

        if dir_name in self.excluded_dirs:
            return False

        return True


class FileBrowser(QWidget):
    class Signals(QObject):
        file_selected = pyqtSignal(str)

    def __init__(self, path, filters=["*.py"], hide_details=True):
        super().__init__()
        self.path = path
        self.signals = self.Signals()
        self.treeview = Tree()  # Assuming Tree is defined elsewhere
        self.treeview.delete_requested.connect(self.delete_requested)

        # Set up the base file system model
        self.fileModel = QFileSystemModel()
        self.fileModel.setNameFilters(filters)
        self.fileModel.setNameFilterDisables(False)
        self.fileModel.setRootPath(path)

        # Set up the proxy model for filtering
        self.dirModel = PycacheFilterProxyModel()
        self.dirModel.setSourceModel(self.fileModel)

        # Use the proxy model with the tree view
        self.treeview.setModel(self.dirModel)
        source_root_index = self.fileModel.index(path)
        proxy_root_index = self.dirModel.mapFromSource(source_root_index)
        self.treeview.setRootIndex(proxy_root_index)

        vlayout = QVBoxLayout(self)
        self.setLayout(vlayout)
        tb = QToolBar()
        tb.addAction("↑", self.btn_up_clicked)
        tb.addAction("⟳", self.refresh)
        tb.addSeparator()
        self.label = QLabel()
        self.label.setContentsMargins(10, 0, 0, 0)
        tb.addWidget(self.label)

        vlayout.addWidget(tb)

        self.label.setText(os.path.dirname(path) if os.path.isfile(path) else path)

        self.layout().addWidget(self.treeview)
        self.treeview.selectionModel().selectionChanged.connect(self.on_current_changed)
        self.treeview.doubleClicked.connect(self.on_double_clicked)
        if hide_details:
            for i in range(1, self.treeview.model().columnCount()):
                self.treeview.header().hideSection(i)

    def delete_requested(self, path):
        if QMessageBox.question(self, "Delete", f"Are you sure you want to delete {path}?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
            return
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        self.refresh()

    def on_double_clicked(self, index):
        # Map the proxy index to the source model index
        source_index = self.dirModel.mapToSource(index)
        path = self.fileModel.fileInfo(source_index).absoluteFilePath()
        if os.path.isdir(path):
            return
        self.signals.file_selected.emit(path)

    def btn_up_clicked(self):
        index = self.treeview.rootIndex()
        if index.isValid():
            index = index.parent()
            self.set_root_index(index)

    def set_root(self, path):
        source_root_index = self.fileModel.setRootPath(path)
        proxy_root_index = self.dirModel.mapFromSource(source_root_index)
        self.treeview.setRootIndex(proxy_root_index)
        self.label.setText(path)

    def set_root_index(self, index):
        self.treeview.setRootIndex(index)
        source_index = self.dirModel.mapToSource(index)
        path = self.fileModel.fileInfo(source_index).absoluteFilePath()
        self.label.setText(path)

    def select(self, filename, emit=True):
        if not emit:
            self.treeview.selectionModel().blockSignals(True)

        source_index = self.fileModel.index(filename)
        proxy_index = self.dirModel.mapFromSource(source_index)

        indices = []
        index = proxy_index
        while index.isValid():
            indices.append(index)
            index = index.parent()

        for index in reversed(indices):
            self.treeview.setExpanded(index, True)

        self.treeview.setCurrentIndex(proxy_index)
        self.treeview.selectionModel().blockSignals(False)

    def on_current_changed(self, selected, deselected):
        pass

    def refresh(self):
        current_path = self.fileModel.rootPath()
        self.fileModel.setRootPath("")
        self.fileModel.setRootPath(current_path)

        # If the toolbar refresh button was clicked with no arguments,
        # show the folder creation dialog
        if self.sender() and self.sender().text() == "⟳":
            folder_name, ok = QInputDialog.getText(self, "Folder Name", "Enter the folder name")
            if ok and folder_name:
                new_folder_path = os.path.join(self.path, folder_name)
                os.makedirs(new_folder_path, exist_ok=True)
                self.fileModel.setRootPath("")
                self.fileModel.setRootPath(current_path)