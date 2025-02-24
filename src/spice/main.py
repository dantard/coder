import os
import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter, QPushButton, QVBoxLayout, QWidget, \
    QTabWidget, QFileDialog, QShortcut, QTabBar
from easyconfig2.easyconfig import EasyConfig2 as EasyConfig

import spice.resources  # noqa
from spice.dialogs import Author
from spice.editor_widget import EditorWidget
from spice.highlighter import PythonHighlighter, PascalHighlighter
from spice.spice_magic_editor import PythonEditor, PascalEditor
from spice.spice_console import JupyterConsole, TermQtConsole
from spice.textract import Slides


class CustomTabBar(QTabBar):
    def __init__(self):
        super().__init__()
        # Customize the tab bar as needed
        self.setStyleSheet("QTabBar::tab { background: lightblue; }")
        self.a = QPushButton(self)


class MainWindow(QMainWindow):

    def edit_config(self):
        if self.config.edit(min_width=400, min_height=400):
            self.config.save("spice.yaml")
            self.apply_config()

    def apply_config(self):

        if self.slides_tabs.currentIndex() != 0:
            self.update_toolbar_position()
            for i in range(1, self.slides_tabs.count()):
                self.slides_tabs.widget(i).set_toolbar_float(self.cfg_tb_float.get_value() == 1, self.slides_tabs)

        for i in range(self.editors_tabs.count()):
            editor = self.editors_tabs.widget(i)
            editor.set_dark_mode(self.cfg_dark.get_value() == 1)
            editor.set_font_size(self.cfg_font_size.get_value() + 10)
            editor.append_autocomplete(self.cfg_autocomplete.get("").split(";"), True)
            editor.set_delay(self.cfg_delay.get())

        self.console_widget.update_config()

    def set_font_size(self, delta):

        current_font_size = self.editors_tabs.currentWidget().get_font_size()
        goal = current_font_size + delta
        if goal < 10 or goal > 32:
            return
        for i in range(self.editors_tabs.count()):
            self.editors_tabs.widget(i).set_font_size(goal)
        self.console_widget.set_font_size(goal)
        self.cfg_font_size.set_value(goal - 10)

    def change_font_size(self, x):
        for i in range(1, self.editors_tabs.count()):
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

    def __init__(self):
        super().__init__()
        self.config = EasyConfig(immediate=True)

        if len(sys.argv) == 2:
            self.console_widget = TermQtConsole()
        else:
            self.console_widget = JupyterConsole()

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
        self.cfg_show_sb = general.addCheckbox("show_tb",
                                               pretty="Show Toolbar",
                                               default=False)
        general.addCheckbox("keep_code",
                            pretty="Keep Code on Run",
                            default=False)
        general.addCheckbox("show_all",
                            pretty="Show all Code on Open",
                            default=False)

        self.cfg_slides_path = general.addFolderChoice("slides_path",
                                                       pretty="Slides Path",
                                                       default=str(os.getcwd()) + os.sep + "slides" + os.sep)
        self.cfg_progs_path = general.addFolderChoice("progs_path",
                                                      pretty="Programs Path",
                                                      default=str(os.getcwd()) + os.sep + "progs" + os.sep)
        self.cfg_autocomplete = general.addString("autocomplete",
                                                  pretty="Autocomplete",
                                                  default="")
        self.cfg_delay = general.addSlider("delay",
                                           pretty="Delay",
                                           min=0, max=100,
                                           default=25,
                                           den=1,
                                           show_value=True,
                                           suffix=" ms")

        self.console_widget.set_config(self.config)
        self.config.load("spice.yaml")
        self.console_widget.config_read()
        self.dark = False

        # SPICE – Slides, Python, Interactive Creation, and Education
        # slides and python for interactive and creative education

        self.slides_tabs = QTabWidget()
        self.slides_tabs.setTabPosition(QTabWidget.South)
        self.slides_tabs.setTabsClosable(True)
        self.slides_tabs.tabCloseRequested.connect(self.close_tab_requested)
        self.slides_tabs.currentChanged.connect(self.tab_changed)
        self.slides_tabs.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)

        self.editors_tabs = QTabWidget()
        self.editors_tabs.addTab(EditorWidget(self.get_editor(), self.console_widget, self.config), "Code")
        self.editors_tabs.setTabsClosable(True)
        self.editors_tabs.tabCloseRequested.connect(self.remove_editor_tab)
        self.editors_tabs.currentChanged.connect(self.editor_tab_changed)

        helper = QWidget()
        helper.setLayout(QVBoxLayout())
        helper.layout().addWidget(self.editors_tabs)

        self.splitter = QSplitter(Qt.Horizontal)
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

        q = QShortcut("Ctrl+E", self)
        q.activated.connect(lambda: self.new_editor_tab(self.console_widget))

        q = QShortcut("Ctrl+L", self)
        q.activated.connect(self.toggle_fullscreen)

        for elem in self.cfg_last.get_value():
            self.open_slides(elem.get("filename"), elem.get("page", 0))

        if self.cfg_open_fullscreen.get_value():
            self.toggle_fullscreen()

        self.setWindowTitle("Spice")
        self.setCentralWidget(helper)

        QTimer.singleShot(10, self.finish_config)

        # Connect config after creation of widgets
        self.console_widget.done.connect(self.editors_tabs.currentWidget().language_editor.setFocus)
        self.cfg_font_size.value_changed.connect(lambda x: self.change_font_size(int(x.get() + 10)))
        self.cfg_dark.value_changed.connect(lambda x: self.apply_color_scheme(x.get()))


    def finish_config(self):
        self.splitter.setSizes([int(self.width() * 0.5), int(self.width() * 0.5)])
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
        self.config.save("spice.yaml")

    # def contextMenuEvent(self, event):
    #     menu = QMenu(self)
    #     m1 = menu.addAction("Fullscreen")
    #     menu.addSeparator()
    #     m1.setCheckable(True)
    #     m1.setChecked(self.isFullScreen())
    #     m1.triggered.connect(self.toggle_fullscreen)
    #
    #     if os.path.exists("slides"):
    #         m2 = menu.addMenu("Slides")
    #
    #         def fill():
    #             pwd = os.getcwd()
    #             for filename in os.listdir("slides"):
    #                 m2.addAction(filename,
    #                              lambda x=filename, y=filename: self.open_slides(pwd + os.sep + "slides" + os.sep + y))
    #
    #         m2.aboutToShow.connect(fill)
    #
    #     menu.addAction("Open", self.open_slides)
    #     menu.addSeparator()
    #     m3 = menu.addMenu("Mode")
    #
    #     # NONE = 0
    #     # POINTER = 1
    #     # WRITING = 2
    #     # ERASING = 3
    #     # RECTANGLES = 4
    #     # ELLIPSES = 5
    #
    #     m3.addAction("None", lambda: self.set_writing_mode(0))
    #     m3.addAction("Pointer", lambda: self.set_writing_mode(1))
    #     m3.addAction("Write", lambda: self.set_writing_mode(2))
    #     m3.addAction("Erase", lambda: self.set_writing_mode(3))
    #     m3.addAction("Rectangles", lambda: self.set_writing_mode(4))
    #     m3.addAction("Ellipses", lambda: self.set_writing_mode(5))
    #
    #     menu.addAction("Exit", self.close)
    #
    #     menu.exec_(event.globalPos())

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


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
