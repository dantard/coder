from PyQt5.QtCore import pyqtSignal,Qt
from PyQt5.QtWidgets import QSplitter, QTabWidget, QTabBar


class DoubleClickTabBar(QTabBar):
    tabDoubleClicked = pyqtSignal(object, int)  # emits the tab index

    def mouseDoubleClickEvent(self, event):
        index = self.tabAt(event.pos())
        if index >= 0:
            self.tabDoubleClicked.emit(self.parent(), index)
        super().mouseDoubleClickEvent(event)

class DoubleTabWidget(QSplitter):
    tabCloseRequested = pyqtSignal(int)
    currentChanged = pyqtSignal(int)

    def __init__(self, orientation=Qt.Vertical, parent=None):
        super().__init__(parent)
        self.left = self.add()
        self.right = self.add()

        self.setOrientation(orientation)
        if orientation == Qt.Vertical:
            self.right.setTabPosition(QTabWidget.South)
        self.right.hide()

        self.left.tabCloseRequested.connect(self.left_tab_close_requested)
        self.right.tabCloseRequested.connect(self.right_tab_close_requested)

    def left_tab_close_requested(self, index):
        if self.left.count() > 1:
            self.left.removeTab(index)

    def right_tab_close_requested(self, index):
        self.right.removeTab(index)
        if self.right.count() == 0:
            self.right.hide()

    def on_tab_double_clicked(self, tab_widget, tab_index):
        print("Tab double-clicked:", tab_widget, tab_index)

        editor_widget = tab_widget.widget(tab_index)
        title = tab_widget.tabText(tab_index)

        if tab_widget == self.left:
            if tab_widget.count() == 1:
                return
            self.right.addTab(editor_widget, title)
            self.right.show()
            self.left.removeTab(tab_index)
        else:
            self.left.addTab(editor_widget, title)
            self.left.show()
            self.right.removeTab(tab_index)
            if self.right.count() == 0:
                self.right.hide()

    def add(self, widget=None):
        widget = QTabWidget() if widget is None else widget
        tab_bar = DoubleClickTabBar()
        widget.setTabBar(tab_bar)
        tab_bar.tabDoubleClicked.connect(self.on_tab_double_clicked)
        self.addWidget(widget)
        return widget

    def addTab(self, widget, name, index=0):
        if index == 0:
            return self.left.addTab(widget, name)
        else:
            self.right.addTab(widget, name)
            self.right.show()

    def setTabsClosable(self, value):
        self.left.setTabsClosable(value)
        self.right.setTabsClosable(value)

    def currentWidget(self):
        return self.left.currentWidget()

    def widget(self, index):
        return self.left.widget(index)

    def count(self):
        return self.left.count()

    def setCurrentWidget(self, widget):
        if widget in [self.left.widget(i) for i in range(self.left.count())]:
            self.left.setCurrentWidget(widget)
        elif widget in [self.right.widget(i) for i in range(self.right.count())]:
            self.right.setCurrentWidget(widget)
