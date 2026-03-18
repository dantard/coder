from PyQt5.QtCore import pyqtSignal, Qt, QEvent
from PyQt5.QtWidgets import QSplitter, QTabWidget, QTabBar, QMenu, QPushButton, QWidget, QHBoxLayout, QLabel


class PlusButton(QWidget):
    def __init__(self, text, parent=None):
        super(PlusButton, self).__init__(parent)
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(QLabel(" ", self))
        self.pb = QPushButton(text, self)
        self.pb.setFixedSize(20, 20)
        self.layout().addWidget(self.pb)
        self.pb.setVisible(True)
        self.pb.setContentsMargins(0, 0, 5, 8)
        self.layout().setContentsMargins(0, 0, 5, 5)


class MyTabWidget(QTabWidget):
    new_tab_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super(MyTabWidget, self).__init__(parent)
        self.orientation = QTabWidget.North
        self.plus_button = QPushButton("+", self)
        self.plus_button.clicked.connect(self.new_tab_requested.emit)  # type: ignore

        plus_button_overflow = PlusButton("+")
        plus_button_overflow.pb.clicked.connect(self.new_tab_requested.emit)  # type: ignore
        self.setCornerWidget(plus_button_overflow, Qt.TopRightCorner)
        self.setAcceptDrops(True)
        self.move_plus_button()

    def setTabText(self, index,a1):
        super().setTabText(index, a1)
        self.move_plus_button()
    def setTabPosition(self, position):
        super().setTabPosition(position)
        self.orientation = position
    def addTab(self, widget, a1) -> int:
        index = super().addTab(widget, a1)
        self.move_plus_button()
        return index

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        self.move_plus_button()

    def move_plus_button(self):
        xpos = 0
        for i in range(self.tabBar().count()):
            rect = self.tabBar().tabRect(i)
            xpos += rect.width()
        if self.orientation == QTabWidget.North:
            self.plus_button.setGeometry(xpos + 5, 5, 20, 20)
        else:
            self.plus_button.setGeometry(xpos + 5, self.height() - 25, 20, 20)

        if xpos > self.width() - 35:
            self.plus_button.hide()
            self.cornerWidget().show()
        else:
            self.plus_button.show()
            self.cornerWidget().hide()


class DoubleClickTabBar(QTabBar):
    tabDoubleClicked = pyqtSignal(object, int)  # emits the tab index
    context_menu_requested = pyqtSignal(object, str, int)  # emits the tab index

    def mouseDoubleClickEvent(self, event):
        index = self.tabAt(event.pos())
        if index >= 0:
            self.tabDoubleClicked.emit(self.parent(), index)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, a0):
        menu = QMenu()
        sam = menu.addAction("Toggle Master")
        result = menu.exec(a0.globalPos())
        if result == sam:
            index = self.tabAt(a0.pos())
            if index >= 0:
                self.context_menu_requested.emit(self.parent(), "SAM", index)


class DoubleTabWidget(QSplitter):
    tabCloseRequested = pyqtSignal(int)
    currentChanged = pyqtSignal(int)
    set_master_requested = pyqtSignal(object)
    new_tab_requested = pyqtSignal(int)

    def __init__(self, orientation=Qt.Vertical, parent=None):
        super().__init__(parent)
        self.current_widget = None
        self.left = self.add()
        self.left.new_tab_requested.connect(lambda: self.new_tab_requested.emit(0))
        self.right = self.add()
        self.right.new_tab_requested.connect(lambda: self.new_tab_requested.emit(1))
        self.setContentsMargins(0, 0, 0, 0)
        self.master = None

        self.setOrientation(orientation)
        if orientation == Qt.Vertical:
            self.right.setTabPosition(QTabWidget.South)
        else:
            self.right.setTabPosition(QTabWidget.North)
        self.right.hide()

        self.left.tabCloseRequested.connect(self.left_tab_close_requested)
        self.right.tabCloseRequested.connect(self.right_tab_close_requested)
        self.left.currentChanged.connect(self.left_current_changed)
        self.right.currentChanged.connect(self.right_current_changed)

    def left_current_changed(self, index):
        self.currentChanged.emit(index)
        widget = self.left.widget(index)
        self.widget_focused(widget)

    def right_current_changed(self, index):
        self.currentChanged.emit(index + self.left.count())
        widget = self.left.widget(index)
        self.widget_focused(widget)

    def set_master(self, master):
        self.master = master
        for i in range(self.left.count()):
            self.left.tabBar().setTabTextColor(i, Qt.black)
        for i in range(self.right.count()):
            self.right.tabBar().setTabTextColor(i, Qt.black)
        if master in [self.left.widget(i) for i in range(self.left.count())]:
            index = self.left.indexOf(master)
            self.left.tabBar().setTabTextColor(index, Qt.blue)
        elif master in [self.right.widget(i) for i in range(self.right.count())]:
            index = self.right.indexOf(master)
            self.right.tabBar().setTabTextColor(index, Qt.blue)

    def left_tab_close_requested(self, index):
        self.tabCloseRequested.emit(index)
        if self.left.count() > 1:
            self.left.removeTab(index)

    def right_tab_close_requested(self, index):
        self.tabCloseRequested.emit(index + self.left.count())
        self.right.removeTab(index)
        if self.right.count() == 0:
            self.right.hide()

    def indexOf(self, w):
        index = self.left.indexOf(w)
        if index != -1:
            return index
        index = self.right.indexOf(w)
        if index != -1:
            return self.left.count() + index
        return -1

    def tabText(self, index):
        if index < self.left.count():
            return self.left.tabText(index)
        else:
            return self.right.tabText(index - self.left.count())

    def setTabText(self, index, text):
        if index < self.left.count():
            self.left.setTabText(index, text)
        else:
            self.right.setTabText(index - self.left.count(), text)

    def on_tab_double_clicked(self, tab_widget, tab_index):
        print("Tab double-clicked:", tab_widget, tab_index)

        editor_widget = tab_widget.widget(tab_index)
        title = tab_widget.tabText(tab_index)

        if tab_widget == self.left:
            if tab_widget.count() == 1:
                return
            print("hhhh")
            self.left.removeTab(tab_index)
            self.right.addTab(editor_widget, title)
            self.right.show()

        else:
            self.left.addTab(editor_widget, title)
            self.left.show()
            self.right.removeTab(tab_index)
            if self.right.count() == 0:
                self.right.hide()

    def add(self, widget=None):
        widget = MyTabWidget() if widget is None else widget
        tab_bar = DoubleClickTabBar()
        widget.setTabBar(tab_bar)
        tab_bar.tabDoubleClicked.connect(self.on_tab_double_clicked)
        tab_bar.context_menu_requested.connect(self.on_context_menu_requested)
        self.addWidget(widget)
        return widget

    def on_context_menu_requested(self, tab_widget, action, index):
        editor_widget = tab_widget.widget(index)
        # editor_widget_index = self.indexOf(editor_widget)
        self.set_master_requested.emit(editor_widget)

    def widget_focused(self, widget):
        if self.master is not None:
            return
        if widget is None:
            widget = self.left.currentWidget()
        self.current_widget = widget
        for i in range(self.left.count()):
            self.left.tabBar().setTabTextColor(i, Qt.black)
        for i in range(self.right.count()):
            self.right.tabBar().setTabTextColor(i, Qt.black)

        if widget in [self.left.widget(i) for i in range(self.left.count())]:
            index = self.left.indexOf(widget)
            self.left.tabBar().setTabTextColor(index, Qt.red)
        elif widget in [self.right.widget(i) for i in range(self.right.count())]:
            index = self.right.indexOf(widget)
            self.right.tabBar().setTabTextColor(index, Qt.red)

    def addTab(self, widget, name, index=0):
        self.current_widget = widget
        widget.focus_in.connect(self.widget_focused)
        if index == 0:
            return self.left.addTab(widget, name)
        else:
            self.right.addTab(widget, name)
            self.right.show()

    def setTabsClosable(self, value):
        self.left.setTabsClosable(value)
        self.right.setTabsClosable(value)

    def currentWidget(self):
        return self.current_widget

    def widget(self, index):
        if index < self.left.count():
            return self.left.widget(index)
        else:
            return self.right.widget(index - self.left.count())

    def count(self):
        return self.left.count() + self.right.count()

    def setCurrentWidget(self, widget):
        if widget in [self.left.widget(i) for i in range(self.left.count())]:
            self.left.setCurrentWidget(widget)
        elif widget in [self.right.widget(i) for i in range(self.right.count())]:
            self.right.setCurrentWidget(widget)
        self.current_widget = widget

    def toggle_orientation(self):
        if self.orientation() == Qt.Vertical:
            self.setOrientation(Qt.Horizontal)
            self.right.setTabPosition(QTabWidget.North)
        else:
            self.setOrientation(Qt.Vertical)
            self.right.setTabPosition(QTabWidget.South)
