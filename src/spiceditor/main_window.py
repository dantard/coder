import os
import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter, QPushButton, QVBoxLayout, QWidget, \
    QTabWidget, QFileDialog, QShortcut, QTabBar, QMessageBox, QToolBar
from easyconfig2.easyconfig import EasyConfig2 as EasyConfig

import spiceditor.resources  # noqa
from spiceditor.dialogs import Author
from spiceditor.editor_widget import EditorWidget
from spiceditor.file_browser import FileBrowser
from spiceditor.highlighter import PythonHighlighter, PascalHighlighter
from spiceditor.spice_magic_editor import PythonEditor, PascalEditor
from spiceditor.spice_console import JupyterConsole, TermQtConsole
from spiceditor.textract import Slides


class CustomTabBar(QTabBar):
    def __init__(self):
        super().__init__()
        # Customize the tab bar as needed
        self.setStyleSheet("QTabBar::tab { background: lightblue; }")
        self.a = QPushButton(self)


class MainWindow(QMainWindow):

    def __init__(self, console):
        super().__init__()
        self.config = EasyConfig(immediate=True)
        general = self.config.root()
        self.cfg_dark = general.addCombobox("dark", pretty="Mode", items=["Light", "Dark"], default=0)
        self.cfg_open_fullscreen = general.addCheckbox("open_fullscreen",
                                                       pretty="Open Fullscreen",
                                                       default=False)

        self.cfg_font_size = general.addCombobox("font_size", pretty="Font size", items=[str(i) for i in range(10, 33)],
                                                 default=0)
        self.cfg_tb_float = general.addCombobox("tb_float",
                                                pretty="Toolbar mode",
                                                items=["Fixed", "Float"],
                                                default=0)
        hidden = self.config.root().addHidden("parameters")
        self.cfg_last = hidden.addList("last", default=[])

        self.cfg_slides_path = general.addFolderChoice("slides_path",
                                                       pretty="Slides Path",
                                                       default=str(os.getcwd()) + os.sep + "slides" + os.sep)
        self.cfg_progs_path = general.addFolderChoice("progs_path",
                                                      pretty="Programs Path",
                                                      default=str(os.getcwd()))


        self.dark = False

        # SPICE – Slides, Python, Interactive Creation, and Education
        # slides and python for interactive and creative education

        self.slides_tabs = QTabWidget()
        self.slides_tabs.setTabPosition(QTabWidget.South)
        self.slides_tabs.setTabsClosable(True)
        self.slides_tabs.tabCloseRequested.connect(self.close_tab_requested)
        self.slides_tabs.currentChanged.connect(self.tab_changed)
        self.slides_tabs.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        self.console_widget = console(self.config)

        self.base_editor = EditorWidget(self.get_editor(), self.console_widget, self.config)


        self.config.load("spiceditor.yaml")
        self.console_widget.config_read()

        self.editors_tabs = QTabWidget()
        self.editors_tabs.addTab(self.base_editor, "Code")
        self.editors_tabs.setTabsClosable(True)
        self.editors_tabs.tabCloseRequested.connect(self.remove_editor_tab)
        self.editors_tabs.currentChanged.connect(self.editor_tab_changed)

        helper = QWidget()
        helper.setLayout(QVBoxLayout())
        helper.layout().addWidget(self.editors_tabs)

        self.file_browser = FileBrowser(self.cfg_progs_path.get_value(), filters=["*.py", "*.pas"])
        self.file_browser.signals.file_selected.connect(self.file_clicked)
        self.splitter = QSplitter(Qt.Horizontal)

        helper2 = QWidget()
        v_layout = QVBoxLayout()
        helper2.setLayout(v_layout)
        self.general_toolbar = QToolBar()
        v_layout.addWidget(self.general_toolbar)
        v_layout.addWidget(self.file_browser)
        self.show_all_action = self.general_toolbar.addAction("Show all code")
        self.show_all_action.setIcon(QIcon(":/icons/radio-button.svg"))
        self.show_all_action.setCheckable(True)

        self.new_dir = self.general_toolbar.addAction("New Folder")
        self.new_dir.setIcon(QIcon(":/icons/folder.svg"))
        self.new_dir.triggered.connect(self.file_browser.new_folder)

        self.splitter.addWidget(helper2)
        self.splitter.addWidget(helper)
        self.splitter.addWidget(self.console_widget)
        self.slides_tabs.addTab(self.splitter, "Code Execution")

        helper = QWidget()
        helper.setContentsMargins(0, 0, 0, 0)
        helper.setLayout(QVBoxLayout())
        helper.layout().setContentsMargins(0, 0, 0, 0)
        helper.layout().setSpacing(0)
        helper.layout().addWidget(self.slides_tabs)

        menu = self.menuBar()
        file = menu.addMenu("File")
        file.addAction("Open", self.open_slides)
        m1 = file.addMenu("Slides")
        file.addSeparator()
        file.addAction("Save Code", self.save_as)
        file.addSeparator()
        file.addAction("Exit", self.close)
        m3 = menu.addMenu("Edit")
        m3.addAction("Preferences", self.edit_config)
        m2 = menu.addMenu("Help")
        m2.addAction("About", lambda: Author().exec_())

        def fill():
            m1.clear()
            path = self.cfg_slides_path.get_value() + os.sep
            if not os.path.exists(path):
                return
            for filename in os.listdir(path):
                m1.addAction(filename, lambda x=filename, y=filename: self.open_slides(path + y))

        m1.aboutToShow.connect(fill)

        q = QShortcut("Ctrl+M", self)
        q.activated.connect(self.toggle_color_scheme)

        q = QShortcut("Ctrl++", self)
        q.activated.connect(lambda: self.modify_font_size(1))

        q = QShortcut("Ctrl+-", self)
        q.activated.connect(lambda: self.modify_font_size(-1))

        q = QShortcut("Ctrl+E", self)
        q.activated.connect(lambda: self.new_editor_tab(self.console_widget))

        q = QShortcut("Ctrl+L", self)
        q.activated.connect(self.toggle_fullscreen)

        q = QShortcut("Ctrl+S", self)
        q.activated.connect(self.save_requested)

        q = QShortcut("Ctrl+Shift+S", self)
        q.activated.connect(lambda : self.save_as_requested)


        for elem in self.cfg_last.get_value():
            self.open_slides(elem.get("filename"), elem.get("page", 0))

        if self.cfg_open_fullscreen.get_value():
            self.toggle_fullscreen()

        self.setWindowTitle("Spice")
        self.setCentralWidget(helper)

        # Connect config after creation of widgets
        self.console_widget.done.connect(self.editors_tabs.currentWidget().language_editor.setFocus)
        self.cfg_font_size.value_changed.connect(lambda x: self.set_font_size(int(x.get() + 10)))
        self.cfg_dark.value_changed.connect(lambda x: self.apply_color_scheme(x.get()))

        QTimer.singleShot(10, self.finish_config)


    def save_requested(self):
        self.editors_tabs.currentWidget().save_program(self.cfg_progs_path.get_value(), False)

    def save_as_requested(self):
        self.editors_tabs.currentWidget().save_program(self.cfg_progs_path.get_value(), True)


    def file_clicked(self, path):
        editor = EditorWidget(self.get_editor(), self.console_widget, self.config)
        editor.load_program(path, self.show_all_action.isChecked())
        self.editors_tabs.addTab(editor, os.path.basename(path))
        editor.set_dark_mode(self.cfg_dark.get_value() == 1)
        self.editors_tabs.setCurrentWidget(editor)
        self.apply_config()

    def edit_config(self):
        if self.config.edit(min_width=400, min_height=400):
            self.config.save("spiceditor.yaml")
            self.apply_config()

    def apply_config(self):

        if self.slides_tabs.currentIndex() != 0:
            self.update_toolbar_position()
            for i in range(1, self.slides_tabs.count()):
                self.slides_tabs.widget(i).set_toolbar_float(self.cfg_tb_float.get_value() == 1, self.slides_tabs)

        for i in range(self.editors_tabs.count()):
            editor = self.editors_tabs.widget(i)
            editor.update_config()

        self.console_widget.update_config()
        self.file_browser.set_root(self.cfg_progs_path.get_value())

    def modify_font_size(self, delta):

        current_font_size = self.editors_tabs.currentWidget().get_font_size()
        goal = current_font_size + delta
        if goal < 10 or goal > 32:
            return
        for i in range(self.editors_tabs.count()):
            self.editors_tabs.widget(i).set_font_size(goal)
        self.console_widget.set_font_size(goal)
        self.cfg_font_size.set_value(goal - 10)

    def set_font_size(self, x):
        for i in range(0, self.editors_tabs.count()):
            self.editors_tabs.widget(i).set_font_size(x)
        self.console_widget.set_font_size(x)

    def get_editor(self):
        if len(sys.argv) == 2:
            editor = PascalEditor()
        else:
            editor = PythonEditor(PythonHighlighter())
        return editor

    def remove_editor_tab(self, index):
        if index > 0:
            self.editors_tabs.removeTab(index)
        else:
            self.editors_tabs.widget(0).clear()

    def new_editor_tab(self, console):
        editor = EditorWidget(self.get_editor(), console, self.config)

        self.editors_tabs.addTab(editor, "Code")
        editor.set_dark_mode(self.cfg_dark.get_value() == 1)
        self.editors_tabs.setCurrentWidget(editor)
        self.apply_config()

    def editor_tab_changed(self, index):
        pass

    def finish_config(self):
        self.splitter.setSizes([int(self.width() * 0.15), int(self.width() * 0.4), int(self.width() * 0.4)])
        # self.splitter.setSizes([int(self.width() * 0.5), int(self.width() * 0.5)])
        self.apply_config()

    def toggle_color_scheme(self):
        self.dark = not self.dark
        self.apply_color_scheme(self.dark)
        self.cfg_dark.set_value(1 if self.dark else 0)

    def apply_color_scheme(self, dark):
        self.console_widget.set_dark_mode(dark)
        for editor in range(self.editors_tabs.count()):
            self.editors_tabs.widget(editor).set_dark_mode(dark)

        if self.slides_tabs.currentIndex() == 0:
            self.setStyleSheet("background-color: #000000; color: white" if dark else "")

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

        self.slides_tabs.currentWidget().set_writing_mode(mode)

    def keyPressEvent(self, a0):
        if a0.key() == Qt.Key_F11:
            self.toggle_fullscreen()
        elif Qt.Key_F1 <= a0.key() <= Qt.Key_F10:
            idx = a0.key() - Qt.Key_F1

            if idx < self.slides_tabs.count():
                self.slides_tabs.setCurrentIndex(idx)

        super().keyPressEvent(a0)

    def save_as(self):
        self.editors_tabs.currentWidget().save_program()

    def move_to(self, forward):
        self.slides_tabs.currentWidget().move_to(forward)

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        self.update_toolbar_position()

    def update_toolbar_position(self):
        if self.slides_tabs.currentIndex() == 0:
            return

        widget = self.slides_tabs.currentWidget()

        if not widget.is_toolbar_float():
            toolbar = widget.get_toolbar()
            toolbar.setParent(self.slides_tabs)
            toolbar.show()

            if self.isFullScreen():
                toolbar.setGeometry(self.width() - toolbar.sizeHint().width() - 20, self.height() - 34,
                                    toolbar.sizeHint().width(), 40)
            else:
                toolbar.setGeometry(self.width() - toolbar.sizeHint().width() - 20, self.height() - 56,
                                    toolbar.sizeHint().width(), 40)

    def tab_changed(self, index):
        for i in range(1, self.slides_tabs.count()):
            widget = self.slides_tabs.widget(i)
            if not widget.is_toolbar_float():
                widget.toolbar.hide()

        if index == 0:
            self.apply_color_scheme(self.cfg_dark.get_value() == 1)
        else:
            self.update_toolbar_position()
            self.setStyleSheet("")

    def set_touchable(self):
        self.slides_tabs.currentWidget().set_touchable(not self.action_touchable.isChecked())

    def close_tab_requested(self, index):
        if index > 0:
            self.slides_tabs.removeTab(index)

    def open_slides(self, filename=None, page=0):
        # open pdf file
        path = self.cfg_slides_path.get_value() + os.sep
        if filename is None:
            filename, ok = QFileDialog.getOpenFileName(self, "Open PDF file", filter="PDF files (*.pdf)",
                                                       directory=path, options=QFileDialog.Options())

        if filename:
            name = filename.split(os.sep)[-1].replace(".pdf", "")
            if os.path.exists(filename):
                slides = Slides(self.config, filename, page)
                slides.set_toolbar_float(self.cfg_tb_float.get_value() == 1, self.slides_tabs)
                slides.play_code.connect(self.code_from_slide)
                self.slides_tabs.addTab(slides, name)
                self.slides_tabs.setCurrentWidget(slides)
                slides.view.setFocus()

    def closeEvent(self, a0):
        last = []
        for i in range(1, self.slides_tabs.count()):
            widget = self.slides_tabs.widget(i)
            if isinstance(widget, Slides):
                last.append({"filename": widget.filename, "page": widget.page})
        self.cfg_last.set_value(last)
        self.config.save("spiceditor.yaml")

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.menuBar().show()
        else:
            self.showFullScreen()
            self.menuBar().hide()
        self.cfg_open_fullscreen.set_value(self.isFullScreen())

    def code_from_slide(self, code):
        editor = self.editors_tabs.currentWidget()
        editor.language_editor.set_text("")
        editor.language_editor.set_code(code)
        editor.language_editor.set_mode(1)
        editor.language_editor.setFocus()
        self.slides_tabs.setCurrentIndex(0)
        editor.show_all_code()



