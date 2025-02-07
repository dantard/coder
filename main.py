import os
import random
import re
import sys
import time
import typing
from easyconfig2.easyconfig import EasyConfig2 as EasyConfig

import resources  # noqa
import yaml
from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter, QTextEdit, QPushButton, QVBoxLayout, QWidget, \
    QToolBar, QComboBox, QTabWidget, QMenu, QMenuBar, QFileDialog, QShortcut, QTabBar, QStatusBar, QHBoxLayout, \
    QPlainTextEdit, QDialog
from PyQt5.QtCore import Qt, QRegExp, pyqtSignal, QTimer, QEvent
from PyQt5.QtGui import QTextCharFormat, QColor, QFont, QSyntaxHighlighter, QPixmap, QPainter, QCursor, QIcon, \
    QTextCursor, QImage
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.manager import QtKernelManager

from dialogs import Author
from editor import PythonEditor, LanguageEditor, PascalEditor
from highlighter import PythonHighlighter, PascalHighlighter
from terminal import Jupyter, Console
from textract import Slides

from utils import create_cursor_image


class CustomTabBar(QTabBar):
    def __init__(self):
        super().__init__()
        # Customize the tab bar as needed
        self.setStyleSheet("QTabBar::tab { background: lightblue; }")
        self.a = QPushButton(self)


class DynamicComboBox(QComboBox):
    def __init__(self, dir, parent=None):
        super().__init__(parent)
        self.dir = dir
        self.addItem("Select program")

    def showPopup(self):
        self.populate()
        super().showPopup()

    def populate(self):
        self.blockSignals(True)
        self.clear()  # Clear the current items
        self.addItem("Select program")
        files = list(os.listdir("progs"))
        files.sort()
        self.addItems(files)
        self.blockSignals(False)


class MainWindow(QMainWindow):

    def edit_config(self):
        #self.config.set_dialog_minimum_size(500, 300)
        print("TTTTTTTTTTT", self.cfg_font_size.get_value())

        if self.config.edit(min_width=400, min_height=400):
            self.config.save("spice.yaml")
            for i in range(1,self.tabs.count()):
                self.tabs.widget(i).set_toolbar_float(self.cfg_tb_float.get_value()==1, self.tabs)
            self.update_toolbar_position()
            #self.apply_color_scheme(self.cfg_dark.get_value()==1)
            self.language_editor.set_font_size(self.cfg_font_size.get_value() + 10)
            self.console_widget.set_font_size(self.cfg_font_size.get_value() + 10)
            print("TTTTTTTTTTT",self.cfg_font_size.get_value())

    def set_font_size(self, delta):
        current_font_size = self.language_editor.text_edit.font().pixelSize()
        goal = current_font_size + delta
        if goal < 10 or goal > 32:
            return
        self.language_editor.set_font_size(goal)
        self.console_widget.set_font_size(goal)
        self.cfg_font_size.set_value(goal - 10)

    def change_font_size(self, x):
        self.language_editor.set_font_size(x)
        self.console_widget.set_font_size(x)
        #self.cfg_font_size.set_value(x - 10)

    def __init__(self, language_editor, console):
        super().__init__()

        self.config = EasyConfig(immediate=True)

        general = self.config.root()
        self.cfg_dark = general.addCombobox("dark", pretty="Mode", items=["Light", "Dark"], default=0)
        self.cfg_dark.value_changed.connect(lambda x: self.apply_color_scheme(x.get()))

        self.cfg_font_size = general.addCombobox("font_size", pretty="Font size", items=[str(i) for i in range(10, 33)],
                                                 default=0)
        self.cfg_font_size.value_changed.connect(lambda x: self.change_font_size(int(x.get()+10)))

        self.cfg_tb_float = general.addCombobox("tb_float", pretty="Toolbar mode", items=["Fixed", "Float"], default=0)
        hidden = self.config.root().addHidden("parameters")
        self.cfg_last = hidden.addList("last", default=[])
        self.cfg_show_sb = general.addCheckbox("show_tb", pretty="Show Toolbar", default=False)
        self.cfg_open_fullscreen = general.addCheckbox("open_fullscreen", pretty="Open Fullscreen", default=False)
        self.cfg_slides_path = general.addFolderChoice("slides_path", pretty="Slides Path",
                                                       default=str(os.getcwd()) + os.sep + "slides/")
        self.cfg_progs_path = general.addFolderChoice("progs_path", pretty="Programs Path", default=str(os.getcwd()) + os.sep + "progs/")

        console.set_config(self.config)

        self.config.load("spice.yaml")
        print("Loaded config", self.cfg_font_size.get_value())

        console.config_read()

        self.font_size = self.cfg_font_size.get_value() + 10
        self.toolbar_float = self.cfg_tb_float.get_value()
        self.dark = self.cfg_dark.get_value() == 1
        self.setWindowTitle("Spice")

        # SPICE – Slides, Python, Interactive Creation, and Education
        # slides and python for interactive and creative education

        # self.resize(1000, 600)

        self.tabs = QTabWidget()

        # put tabs bottom
        self.tabs.setTabPosition(QTabWidget.South)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab_requested)
        self.tabs.currentChanged.connect(self.tab_changed)
        tab_bar = self.tabs.tabBar()

        splitter = QSplitter(Qt.Horizontal)

        self.prog_cb = DynamicComboBox("progs")
        self.prog_cb.currentTextChanged.connect(self.load_program)
        font = QFont("Monospace")
        font.setStyleHint(QFont.TypeWriter)
        font.setPixelSize(16)
        self.prog_cb.setFont(font)

        # Left side layout
        left_widget = QWidget()
        left_layout = QVBoxLayout()

        # self.text_edit = LanguageEditor(PythonEditor(PythonHighlighter()))
        self.language_editor = language_editor
        self.language_editor.ctrl_enter.connect(self.execute_code)
        self.language_editor.info.connect(self.update_status_bar)
        self.language_editor.set_font_size(self.cfg_font_size.get_value()+10)

        bar = QToolBar()
        a1 = bar.addAction("Play", self.execute_code)
        a2 = bar.addAction("Clear", self.clear_all)
        a3 = bar.addAction("Show", self.language_editor.show_code)

        self.keep_banner = bar.addAction("#")
        self.keep_banner.setCheckable(True)
        self.keep_banner.setChecked(False)

        self.text_edit_group = [a1, a2, a3, self.keep_banner]

        left_layout.addWidget(bar)
        left_layout.addWidget(self.prog_cb)

        # lay = QHBoxLayout()
        #
        # self.line_number_area.setReadOnly(True)
        # self.line_number_area.setMaximumWidth(50)
        # lay.addWidget(self.line_number_area)
        # lay.addWidget(self.text_edit)

        # self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # self.line_number_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # self.line_number_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # def text_changed():
        #     text = self.text_edit.toPlainText()
        #     lines = text.split("\n")
        #     cursor_pos = self.text_edit.textCursor().position()
        #     v1 = self.line_number_area.verticalScrollBar().value()
        #     self.line_number_area.blockSignals(True)
        #     self.line_number_area.clear()
        #     text = ""
        #
        #     for i in range(len(lines)):  # TODO: was +`11 (maybe for when the editor is full)
        #         # self.line_number_area.append("{:3d}".format(i + 1))
        #         text += "{:3d}\n".format(i + 1)
        #     self.line_number_area.setPlainText(text)
        #
        #     # self.text_edit.setTextCursor(self.text_edit.textCursor())
        #     self.line_number_area.verticalScrollBar().setValue(v1)
        #     self.line_number_area.blockSignals(False)
        #
        # self.text_edit.textChanged.connect(text_changed)
        # self.text_edit.verticalScrollBar().valueChanged.connect(self.line_number_area.verticalScrollBar().setValue)
        # self.text_edit.horizontalScrollBar().rangeChanged.connect(text_changed)
        # self.line_number_area.verticalScrollBar().valueChanged.connect(self.text_edit.verticalScrollBar().setValue)

        left_layout.addWidget(self.language_editor)

        self.sb = QStatusBar()
        if self.cfg_show_sb.get_value():
            left_layout.addWidget(self.sb)

        # left_layout.addWidget(self.run_button)
        left_widget.setLayout(left_layout)

        #        lay.setSpacing(0)
        #        lay.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        left_layout.setContentsMargins(0, 0, 0, 0)

        splitter.addWidget(left_widget)

        # Right side: RichJupyterWidget
        self.console_widget = console
        splitter.addWidget(self.console_widget)
        self.console_widget.set_font_size(self.cfg_font_size.get_value()+10)


        self.tabs.addTab(splitter, "Code Execution")
        tab_bar.setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        helper = QWidget()
        helper.setContentsMargins(0, 0, 0, 0)
        helper.setLayout(QVBoxLayout())
        helper.layout().setContentsMargins(0, 0, 0, 0)
        helper.layout().setSpacing(0)
        helper.layout().addWidget(self.tabs)
        # helper.layout().addWidget(QStatusBar())
        self.setCentralWidget(helper)

        menu = self.menuBar()
        file = menu.addMenu("File")
        file.addAction("Open", self.open_slides)
        m1 = file.addMenu("Slides")
        file.addSeparator()
        file.addAction("Save As", self.save_as)
        file.addSeparator()
        file.addAction("Exit", self.close)
        m3 = menu.addMenu("Edit")
        m3.addAction("Preferences", self.edit_config)
        m2 = menu.addMenu("Help")
        m2.addAction("About", lambda: Author().exec_())

        def fill():
            m1.clear()
            path = self.cfg_slides_path.get_value()
            if not os.path.exists(path):
                os.makedirs(path)
            for filename in os.listdir(path):
                m1.addAction(filename, lambda x=filename, y=filename: self.open_slides(path + y))

        m1.aboutToShow.connect(fill)

        q = QShortcut("Ctrl+M", self)
        q.activated.connect(self.toggle_color_scheme)

        q = QShortcut("Ctrl++", self)
        q.activated.connect(lambda: self.set_font_size(1))

        q = QShortcut("Ctrl+-", self)
        q.activated.connect(lambda: self.set_font_size(-1))

        q = QShortcut("Ctrl+K", self)
        q.activated.connect(self.clear_all)

        q = QShortcut("Ctrl+S", self)
        q.activated.connect(self.save_as)

        q = QShortcut("Ctrl+L", self)
        q.activated.connect(self.toggle_fullscreen)

        q = QShortcut("Ctrl+O", self)
        q.activated.connect(self.open_slides)

        q = QShortcut("Ctrl+Tab", self)
        q.activated.connect(self.toggle_focus)

        q = QShortcut("Ctrl+F", self)

        #        q.activated.connect(self.text_edit.format_code)

        def resize():
            splitter.setSizes([int(self.width() * 0.5), int(self.width() * 0.5)])

        QTimer.singleShot(100, resize)

        self.tab_changed(0)

        for elem in self.cfg_last.get_value():
            self.open_slides(elem.get("filename"), elem.get("page", 0))

        if self.cfg_open_fullscreen.get_value():
            self.toggle_fullscreen()

        QTimer.singleShot(100, self.update_toolbar_position)

    def toggle_color_scheme(self):
        self.dark = not self.dark
        self.apply_color_scheme(self.dark)
        self.cfg_dark.set_value(1 if self.dark else 0)

    def apply_color_scheme(self, dark):
        self.console_widget.set_dark_mode(dark)
        self.language_editor.set_dark_mode(dark)

        if self.tabs.currentIndex() == 0:
            self.setStyleSheet("background-color: #000000; color: white" if dark else "")

        color = Qt.white if dark else Qt.black
        a1, a2, a3, a4 = self.text_edit_group
        a1.setIcon(QIcon(self.color(":/icons/play.svg", color)))
        a2.setIcon(QIcon(self.color(":/icons/refresh.svg", color)))
        a3.setIcon(QIcon(self.color(":/icons/download.svg", color)))
        a4.setIcon(QIcon(self.color(":/icons/hash.svg", color)))

    def color(self, icon_path, color):
        # Load the pixmap from the icon path
        pixmap = QPixmap(icon_path)

        # Create an empty QPixmap with the same size
        colored_pixmap = QPixmap(pixmap.size())
        colored_pixmap.fill(Qt.transparent)

        # Paint the new color onto the QPixmap
        painter = QPainter(colored_pixmap)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(colored_pixmap.rect(), QColor(color))
        painter.end()
        return colored_pixmap

    def color2(self, icon_path, target_color="white"):
        # Load the icon as a QImage
        image = QImage(icon_path)

        # Iterate through each pixel to recolor black pixels
        for y in range(image.height()):
            for x in range(image.width()):
                color = QColor(image.pixel(x, y))
                if color.red() == 0 and color.green() == 0 and color.blue() == 0:  # Black pixel
                    image.setPixelColor(x, y, QColor(target_color))

        # Convert back to QPixmap
        pixmap = QPixmap.fromImage(image)
        return pixmap

    def set_color(self, color):
        for i, elem in enumerate(self.color_group):
            elem.blockSignals(True)
            elem.setChecked(i == color)
            elem.blockSignals(False)
        self.tabs.currentWidget().set_color(color)

    def toggle_focus(self):
        if self.language_editor.hasFocus():
            self.console_widget._control.setFocus()
        else:
            self.language_editor.setFocus()

    def set_writing_mode(self, mode):
        for i, elem in enumerate(self.group):
            elem.blockSignals(True)
            elem.setChecked(i == mode)
            elem.blockSignals(False)

        self.tabs.currentWidget().set_writing_mode(mode)

    def keyPressEvent(self, a0):
        if a0.key() == Qt.Key_F11:
            self.toggle_fullscreen()
        elif Qt.Key_F1 <= a0.key() <= Qt.Key_F10:
            idx = a0.key() - Qt.Key_F1

            if idx < self.tabs.count():
                self.tabs.setCurrentIndex(idx)

        super().keyPressEvent(a0)

    def save_as(self):
        path = self.cfg_progs_path.get_value()
        filename, ok = QFileDialog.getSaveFileName(self, "Save code", filter="Python files (*.py)", directory=path)
        if ok:
            filename = filename.replace(".py", "") + ".py"
            with open(filename, "w") as f:
                f.write(self.language_editor.get_text())

    def update_status_bar(self, x, timeout):
        if self.cfg_show_sb.get_value():
            x = x.replace("\n", "")
            diff = self.language_editor.get_remaining_chars()
            if timeout != 0:
                x = "{:5d} | {}".format(diff, x)
                self.sb.showMessage(x, 1000)
            else:
                self.sb.showMessage(x)

            # red if diff is negative
            if diff < 10:
                self.sb.setStyleSheet("color: red")
            else:
                self.sb.setStyleSheet("color: black")

    def move_to(self, forward):
        self.tabs.currentWidget().move_to(forward)

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        self.update_toolbar_position()

    def update_toolbar_position(self):
        if self.tabs.currentIndex() == 0:
            return
        widget = self.tabs.currentWidget()

        if not widget.is_toolbar_float():
            toolbar = widget.get_toolbar()
            toolbar.setParent(self.tabs)
            toolbar.show()

            if self.isFullScreen():
                toolbar.setGeometry(self.width() - toolbar.sizeHint().width() - 20, self.height() - 34,
                                    toolbar.sizeHint().width(),
                                    40)
            else:
                toolbar.setGeometry(self.width() - toolbar.sizeHint().width() - 20, self.height() - 56,
                                    toolbar.sizeHint().width(),
                                    40)

    def clear_all(self):
        self.console_widget.clear()
        self.language_editor.clear()
        self.prog_cb.setCurrentIndex(0)

    def tab_changed(self, index):
        for i in range(1, self.tabs.count()):
            widget = self.tabs.widget(i)
            if not widget.is_toolbar_float():
                widget.toolbar.hide()

        if index == 0:
            self.apply_color_scheme(self.cfg_dark.get_value() == 1)
        else:
            self.update_toolbar_position()
            self.setStyleSheet("")

    def set_touchable(self):
        self.tabs.currentWidget().set_touchable(not self.action_touchable.isChecked())

    def close_tab_requested(self, index):
        if index > 0:
            self.tabs.removeTab(index)

    def open_slides(self, filename=None, page=0):
        # open pdf file
        path = self.cfg_slides_path.get_value()
        if filename is None:
            filename, ok = QFileDialog.getOpenFileName(self, "Open PDF file", filter="PDF files (*.pdf)",
                                                       directory=path, options=QFileDialog.Options())

        if filename:
            print("FF", filename)
            name = filename.split("/")[-1].replace(".pdf", "")
            if os.path.exists(filename):
                slides = Slides(self.config, filename, page)
                slides.set_toolbar_float(self.cfg_tb_float.get_value() == 1, self.tabs)
                slides.play_code.connect(self.code_from_slide)
                self.tabs.addTab(slides, name)
                self.tabs.setCurrentWidget(slides)
                slides.view.setFocus()

    def closeEvent(self, a0):
        last = []
        for i in range(1, self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, Slides):
                last.append({"filename": widget.filename, "page": widget.page})
        self.cfg_last.set_value(last)

        self.config.save("spice.yaml")

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        m1 = menu.addAction("Fullscreen")
        menu.addSeparator()
        m1.setCheckable(True)
        m1.setChecked(self.isFullScreen())
        m1.triggered.connect(self.toggle_fullscreen)

        if os.path.exists("slides"):
            m2 = menu.addMenu("Slides")

            def fill():
                pwd = os.getcwd()
                for filename in os.listdir("slides"):
                    m2.addAction(filename, lambda x=filename, y=filename: self.open_slides(pwd + "/slisdes//" + y))

            m2.aboutToShow.connect(fill)

        menu.addAction("Open", self.open_slides)
        menu.addSeparator()
        m3 = menu.addMenu("Mode")

        # NONE = 0
        # POINTER = 1
        # WRITING = 2
        # ERASING = 3
        # RECTANGLES = 4
        # ELLIPSES = 5

        m3.addAction("None", lambda: self.set_writing_mode(0))
        m3.addAction("Pointer", lambda: self.set_writing_mode(1))
        m3.addAction("Write", lambda: self.set_writing_mode(2))
        m3.addAction("Erase", lambda: self.set_writing_mode(3))
        m3.addAction("Rectangles", lambda: self.set_writing_mode(4))
        m3.addAction("Ellipses", lambda: self.set_writing_mode(5))

        menu.addAction("Exit", self.close)

        menu.exec_(event.globalPos())

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.menuBar().show()
        else:
            self.showFullScreen()
            self.menuBar().hide()
        self.cfg_open_fullscreen.set_value(self.isFullScreen())

    def code_from_slide(self, code):
        self.language_editor.set_text("")
        self.language_editor.set_code(code)
        self.language_editor.set_mode(1)
        self.tabs.setCurrentIndex(0)
        self.language_editor.setFocus()

    def load_program(self, filename):
        if filename == "Select program":
            self.clear_all()
            return

        with open(f"progs/{filename}") as f:
            #    self.text_edit.setPlainText(f.read())
            self.language_editor.set_code(f.read())
            self.console_widget.clear()

    def execute_code(self):
        self.language_editor.format_code()
        self.console_widget.execute(self.language_editor.get_text(), not self.keep_banner.isChecked())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    if len(sys.argv) > 1:
        window = MainWindow(LanguageEditor(PascalEditor(PascalHighlighter())), Console())
    else:
        window = MainWindow(LanguageEditor(PythonEditor(PythonHighlighter())), Jupyter())

    window.show()

    sys.exit(app.exec_())
