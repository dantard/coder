import os
import sys
from spiceditor.drive_pdf_downloader import DrivePdfDownloaderWidget
from PyQt5.QtCore import Qt, QTimer,QEvent
from PyQt5.QtGui import QIcon, QKeyEvent
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter, QPushButton, QVBoxLayout, QWidget, \
    QTabWidget, QFileDialog, QShortcut, QTabBar, QMessageBox, QToolBar, QDialog
from easyconfig2.easyconfig import EasyConfig2 as EasyConfig
import sqlite3
import spiceditor.resources  # noqa
from spiceditor.bw_timer import CountdownTimer
from spiceditor.dialogs import Author, ConnectionDialog
from spiceditor.double_tab_widget import DoubleTabWidget
from spiceditor.editor_widget import EditorWidget
from spiceditor.file_browser import FileBrowser
from spiceditor.highlighter import PythonHighlighter, PascalHighlighter
from spiceditor.jupyter_console import JupyterConsole
from spiceditor.spice_magic_editor import PythonEditor, PascalEditor
from spiceditor.spice_console import TermQtConsole
from minimal_sql_browser.msb import MiniSqlApp
#from spiceditor.sqlbrowser import SQLiteBrowser
from spiceditor.textract import Slides
import argparse


class CustomTabBar(QTabBar):
    def __init__(self):
        super().__init__()
        # Customize the tab bar as needed
        self.setStyleSheet("QTabBar::tab { background: lightblue; }")
        self.a = QPushButton(self)


class MainWindow(QMainWindow):

    def __init__(self, console):
        super().__init__()

        parser = argparse.ArgumentParser()
        parser.add_argument("--userid", type=str, help="User ID for collaborative editing", default=None)
        parser.add_argument("--host", action="store_true", help="Start in host mode for collaborative editing")
        args = parser.parse_args()

        self.userid = args.userid
        self.script_path = os.path.dirname(os.path.abspath(__file__)) + os.sep
        self.show_iter = 0
        self.sizes = None
        self.master_widget = None

        self.config = EasyConfig(immediate=True)
        general = self.config.root()
        self.cfg_dark = general.addCombobox("dark", pretty="Mode", items=["Light", "Dark"], default=0)
        self.cfg_open_fullscreen = general.addCheckbox("open_fullscreen",
                                                       pretty="Open Fullscreen",
                                                       default=False)
        self.cfg_remote_folder_id = general.addString("remote_folder_id", pretty="Remote Slides Folder ID", default="")
        self.cfg_font_size = general.addCombobox("font_size", pretty="Font size", items=[str(i) for i in range(10, 65)],
                                                 default=0)
        self.cfg_tb_orintation = general.addCombobox("tb_orientation",
                                                     pretty="Toolbar mode (relaunch needed)",
                                                     items=["Vertical", "Horizontal"],
                                                     default=0)
        self.cfg_split_view_mode = general.addCombobox("split_view_mode",
                                                     pretty="Split view mode (relaunch needed)",
                                                     items=["Vertical", "Horizontal"],
                                                     default=0)
        hidden = self.config.root().addHidden("parameters")
        self.cfg_last = hidden.addList("last", default=[])

        self.cfg_slides_path = general.addFolderChoice("slides_path",
                                                       pretty="Slides Path",
                                                       default=str(os.getcwd()) + os.sep + "slides" + os.sep)
        self.cfg_progs_path = general.addFolderChoice("progs_path",
                                                      pretty="Programs Path",
                                                      default=str(os.getcwd()))
        self.cfg_show_all = general.getCheckBox("show_all",
                                                pretty="Show all Code on Open",
                                                default=False)

        self.cfg_format_before_run = general.getCheckBox("format_code_before_run",
                                                pretty="Format Code before Run",
                                                default=False)
        self.cfg_click_to_next = general.addCombobox("click_to_next", pretty="Click to go to next slide",
                                                     items=["1", "2", "3"], default=0)
        self.cfg_override_keys = general.getCheckBox("override_keys", pretty="Override Keys",
                                                     default=False)

        self.dark = False
        self.timers = []

        # SPICE – Slides, Python, Interactive Creation, and Education
        # slides and python for interactive and creative education

        self.slides_tabs = QTabWidget()
        self.slides_tabs.setTabPosition(QTabWidget.South)
        self.slides_tabs.setTabsClosable(True)
        self.slides_tabs.tabCloseRequested.connect(self.close_tab_requested)
        self.slides_tabs.currentChanged.connect(self.tab_changed)
        self.slides_tabs.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        self.slides_tabs.tabBarDoubleClicked.connect(self.slide_tab_double_clicked)
        self.console_widget = console(self.config)

        self.base_editor = EditorWidget(self.get_editor(), self.console_widget, self.config)
        self.base_editor.file_modified.connect(self.file_modified)
        self.base_editor.execute_called.connect(self.execute_called)
        if args.host:
            self.base_editor.get_editor().start_server(args.userid if args.userid else "host")

        self.config.load(self.script_path + "spiceditor.yaml")
        self.console_widget.config_read()

        self.editors_tabs = DoubleTabWidget(Qt.Vertical if self.cfg_split_view_mode.get_value() == 0 else Qt.Horizontal)
        self.editors_tabs.addTab(self.base_editor, "Code")
        self.editors_tabs.setTabsClosable(True)
        self.editors_tabs.tabCloseRequested.connect(self.tab_close_requested)
        self.editors_tabs.currentChanged.connect(self.editor_tab_changed)
        self.editors_tabs.set_master_requested.connect(self.set_master_requested)
        self.editors_tabs.new_tab_requested.connect(lambda index: self.new_editor_tab(self.console_widget, index))

        helper = QWidget()
        helper.setLayout(QVBoxLayout())
        helper.layout().addWidget(self.editors_tabs)
        helper.setContentsMargins(0, 0, 0, 0)
        helper.layout().setContentsMargins(0,5,0,0)
        helper.layout().setSpacing(0)

        self.file_browser = FileBrowser(self.cfg_progs_path.get_value(), filters=[".py", ".csv", ".txt", ".yaml", ".db", ".sqlite"], )
        self.file_browser.signals.file_selected.connect(self.file_clicked)
        self.file_browser.signals.directory_changed.connect(lambda path: self.cfg_progs_path.set_value(path))

        self.splitter = QSplitter(Qt.Horizontal)

        helper2 = QWidget()
        v_layout = QVBoxLayout()
        helper2.setLayout(v_layout)
        self.general_toolbar = QToolBar()
        v_layout.addWidget(self.general_toolbar)
        v_layout.addWidget(self.file_browser)
        self.show_all_code_action = self.general_toolbar.addAction("Show all code")
        self.show_all_code_action.setIcon(QIcon(":/icons/radio-button.svg"))
        self.show_all_code_action.setCheckable(True)
        self.show_all_code_action.setChecked(self.cfg_show_all.get_value())

        self.new_dir = self.general_toolbar.addAction("New Folder")
        self.new_dir.setIcon(QIcon(":/icons/folder.svg"))
        self.new_dir.triggered.connect(self.file_browser.new_folder)

        self.splitter.addWidget(helper2)
        self.splitter.addWidget(helper)
        ### TODO: new
        self.slides_helper = QWidget()
        self.slides_helper.setLayout(QVBoxLayout())
        self.slides_helper.layout().setContentsMargins(0, 0, 0, 0)
        self.slides_helper.layout().addWidget(self.console_widget)
        self.back_to_tabs_btn = QPushButton("Back to tabs")
        self.back_to_tabs_btn.clicked.connect(self.back_to_tabs)
        self.back_to_tabs_btn.setVisible(False)
        self.slides_helper.layout().addWidget(self.back_to_tabs_btn)
        self.splitter.addWidget(self.slides_helper)


    ### TODO: old
        #self.splitter.addWidget(self.console_widget)

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
        file.addAction("Download", self.download)
        file.addSeparator()
        file.addAction("Connect", self.connect_to_host)
        file.addAction("Create Database", self.open_db_browser)
        file.addAction("Exit", self.close)
        m4 = menu.addMenu("Timer")
        m4.addAction("5 min", lambda: self.create_timer(minutes=5))
        m4.addAction("10 min", lambda: self.create_timer(minutes=10))
        m4.addAction("15 min", lambda: self.create_timer(minutes=15))

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

        q = QShortcut("Ctrl+O", self)
        q.activated.connect(self.toggle_split_view_mode)

        q = QShortcut("Ctrl+M", self)
        q.activated.connect(self.toggle_color_scheme)

        q = QShortcut("Ctrl++", self)
        q.activated.connect(lambda: self.modify_font_size(1))

        q = QShortcut("Ctrl+-", self)
        q.activated.connect(lambda: self.modify_font_size(-1))

        q = QShortcut("Ctrl+E", self)
        q.activated.connect(lambda: self.new_editor_tab(self.console_widget))

        q = QShortcut("Ctrl+Q", self)
        q.activated.connect(lambda: self.new_editor_tab2(self.console_widget))


        q = QShortcut("Ctrl+L", self)
        q.activated.connect(self.toggle_fullscreen)

        q = QShortcut("Ctrl+S", self)
        q.activated.connect(self.save_requested)

        q = QShortcut("Ctrl+Shift+S", self)
        q.activated.connect(lambda: self.save_as_requested())

        q = QShortcut("Ctrl+K", self)
        q.activated.connect(self.show_only)

        q = QShortcut("Ctrl+P", self)
        q.activated.connect(self.console_widget.toggle_key_override)

        q = QShortcut("Ctrl+R", self)
        q.activated.connect(lambda: self.editors_tabs.currentWidget().reload_clicked())


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

        if self.cfg_override_keys.get_value():
            self.console_widget.toggle_key_override()


        QTimer.singleShot(10, self.finish_config)

    def download(self):
        if not self.cfg_remote_folder_id.get_value() or not self.cfg_slides_path.get_value():
            QMessageBox.warning(self, "Configuration needed", "Please set the Remote Slides Folder ID and Slides Path in the configuration first.")
            return
        self.widget = DrivePdfDownloaderWidget(self.cfg_remote_folder_id.get_value(), self.cfg_slides_path.get_value())
        self.widget.done.connect(lambda path: self.open_slides(path))
        self.widget.setWindowTitle("Drive PDF Downloader")
        self.widget.show()
        QTimer.singleShot(100, self.adjustSize)

    def open_db_browser(self):
        path = QFileDialog.getSaveFileName(self, "Create SQLite Database", filter="SQLite files (*.sqlite);;All files (*.*)", directory=self.cfg_progs_path.get_value())[0]
        try:
            conn = sqlite3.connect(path)
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot create database:\n{e}")
            return


        #widget = SQLiteBrowser()
        #self.editors_tabs.addTab(widget, "Browser")


    def set_master_requested(self, widget):
        if self.master_widget is widget:
            self.master_widget = None
        else:
            self.master_widget = widget

        self.editors_tabs.set_master(self.master_widget)

        print("Master widget set to:", self.master_widget)

    def toggle_split_view_mode(self):
        self.editors_tabs.toggle_orientation()

    def connect_to_host(self):
        dialog = ConnectionDialog(self.userid if self.userid else "User", self)
        if dialog.exec_() == QDialog.Accepted:
            values = dialog.get_values()
            host = values.get("host_address")
            port = values.get("host_port")
            user_id = values.get("user_id")
            sock = self.base_editor.get_editor().connect_to_host(user_id, host=host, port=int(port))
            sock.connected.connect(
                lambda: QMessageBox.information(self, "Connected",
                                                f"Successfully connected to {host}:{port} as user '{user_id}'"))
            sock.errorOccurred.connect(
                lambda: QMessageBox.critical(self, "Connection Error", f"Failed to connect to {host}:{port}"))

    def create_timer(self, hours=0, minutes=0, seconds=0):
        total_seconds = hours * 3600 + minutes * 60 + seconds
        if total_seconds <= 0:
            return

        timer_widget = CountdownTimer(hours=hours, minutes=minutes, seconds=seconds, auto_start=True, show_buttons=True)
        timer_widget.setWindowTitle('Countdown Timer')
        timer_widget.resize(300, 150)
        timer_widget.show()
        self.timers.append(timer_widget)

    def show_only(self):
        if self.show_iter == 0:
            self.sizes = self.splitter.sizes()

        self.show_iter = (self.show_iter + 1) % 4
        if self.show_iter == 1:
            self.splitter.setSizes([0, 0, int(self.width() * 0.4)])
        elif self.show_iter == 2:
            self.splitter.setSizes([0, int(self.width() * 0.4), 0])
        elif self.show_iter == 3:
            self.splitter.setSizes([0, int(self.width() * 0.4), int(self.width() * 0.4)])
        else:
            self.splitter.setSizes(self.sizes)

    def save_requested(self):
        #self.editors_tabs.currentWidget().save_program(self.cfg_progs_path.get_value(), False)
        for widget in self.editors_tabs.widgets(): #type: EditorWidget
            if widget.language_editor.hasFocus():
                widget.save_program(self.cfg_progs_path.get_value(), False)
                break

    def save_as_requested(self):
        #self.editors_tabs.currentWidget().save_program(self.cfg_progs_path.get_value(), False)
        for widget in self.editors_tabs.widgets(): #type: EditorWidget
            if widget.language_editor.hasFocus():
                widget.save_program(self.cfg_progs_path.get_value(), True)
                break

    def file_clicked(self, path):
        for i in range(self.editors_tabs.count()):
            widget = self.editors_tabs.widget(i)
            if isinstance(widget, EditorWidget) and widget.path == path:
                self.editors_tabs.setCurrentWidget(widget)
                return

        if ".db" in path or ".sqlite" in path:
            editor = MiniSqlApp(path) #SQLiteBrowser(path)
            editor.set_font_size(self.cfg_font_size.get_value() + 10)
            self.editors_tabs.addTab(editor, "DBrowser")
        else:
            editor = EditorWidget(self.get_editor(), self.console_widget, self.config)
            editor.file_modified.connect(self.file_modified)
            editor.execute_called.connect(self.execute_called)
            editor.load_program(path, self.show_all_code_action.isChecked())
            self.editors_tabs.addTab(editor, os.path.basename(path))

        editor.set_dark_mode(self.cfg_dark.get_value() == 1)
        self.editors_tabs.setCurrentWidget(editor)
        self.apply_config()

    def edit_config(self):
        if self.config.edit(min_width=400, min_height=400):
            self.config.save(self.script_path + "spiceditor.yaml")
            self.apply_config()

    def execute_called(self, editor_widget):
        for editor in range(self.editors_tabs.count()): #type: EditorWidget
            editor = self.editors_tabs.widget(editor)
            if editor.on_disk():
                editor.save_program(None, False)

        if self.master_widget is not None:
            self.master_widget.run_code()
        else:
            editor_widget.run_code()


    def apply_config(self):

        if self.slides_tabs.currentIndex() != 0:
            pass
            # self.update_toolbar_position()
            # for i in range(1, self.slides_tabs.count()):
            #    self.slides_tabs.widget(i).set_toolbar_float(self.cfg_tb_float.get_value() == 1, self.slides_tabs)

        for i in range(self.editors_tabs.count()):
            editor = self.editors_tabs.widget(i)
            editor.update_config()

        self.console_widget.update_config()
        self.file_browser.set_root(self.cfg_progs_path.get_value())

    def modify_font_size(self, delta):

        current_font_size = self.editors_tabs.currentWidget().get_font_size()
        goal = current_font_size + delta
        if goal < 10 or goal > 64:
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
        # if len(sys.argv) == 2:
        #     editor = PascalEditor()
        # else:
        editor = PythonEditor(PythonHighlighter())
        return editor

    def tab_close_requested(self, index):
        widget = self.editors_tabs.widget(index)
        if widget is self.master_widget:
            self.set_master_requested(None)

    def file_modified(self, widget, value):
        idx = self.editors_tabs.indexOf(widget)
        if idx == -1:
            return
        title = self.editors_tabs.tabText(idx)
        title = title.replace("*", "")
        title = title + "*" if value else title
        self.editors_tabs.setTabText(idx, title)

    def new_editor_tab(self, console, index=0):
        editor = EditorWidget(self.get_editor(), console, self.config)
        editor.file_modified.connect(self.file_modified)
        editor.execute_called.connect(self.execute_called)

        self.editors_tabs.addTab(editor, "Code", index)
        editor.set_dark_mode(self.cfg_dark.get_value() == 1)
        self.editors_tabs.setCurrentWidget(editor)
        self.apply_config()
        return editor

    def new_editor_tab2(self, console):
        editor = EditorWidget(self.get_editor(), console, self.config)
        editor.file_modified.connect(self.file_modified)
        editor.execute_called.connect(self.execute_called)

        self.editors_tabs.addTab(editor, "Code", 1)
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
        if self.editors_tabs.currentWidget().language_editor.hasFocus():
            self.console_widget: JupyterConsole
            self.console_widget.set_editor_focus()
        else:
            editor: EditorWidget = self.editors_tabs.currentWidget()
            editor.language_editor.setFocus()

    def set_writing_mode(self, mode):
        for i, elem in enumerate(self.group):
            elem.blockSignals(True)
            elem.setChecked(i == mode)
            elem.blockSignals(False)

        self.slides_tabs.currentWidget().set_writing_mode(mode)

    def keyPressEvent(self, a0):
        if a0.key() == Qt.Key_F12:
            self.editors_tabs.currentWidget().execute_code()
        elif Qt.Key_F1 <= a0.key() <= Qt.Key_F10:
            idx = a0.key() - Qt.Key_F1

            if idx < self.slides_tabs.count():
                self.slides_tabs.setCurrentIndex(idx)
        elif a0.key() == Qt.Key_F11:
            self.editors_tabs.currentWidget().execute_single_line(True)
        if a0.key() == Qt.Key_F1:
            self.toggle_focus()

        super().keyPressEvent(a0)

    def move_to(self, forward):
        self.slides_tabs.currentWidget().move_to(forward)

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        # self.update_toolbar_position()

    def tab_changed(self, index):
        pass
        # for i in range(1, self.slides_tabs.count()):
        #     widget = self.slides_tabs.widget(i)
        #     if not widget.is_toolbar_float():
        #         widget.toolbar.hide()

        if index == 0:
            self.apply_color_scheme(self.cfg_dark.get_value() == 1)
        else:
            # self.update_toolbar_position()
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

            name = name[0:12] + "..." + name[-12:] if len(name) > 27 else name

            if os.path.exists(filename):
                slides = Slides(self.config, filename, page)
                slides.play_code.connect(self.code_from_slide)
                self.slides_tabs.addTab(slides, name)
                self.slides_tabs.setCurrentWidget(slides)
                slides.view.setFocus()

        #self.slides_tabs.setCurrentIndex(0)

    def closeEvent(self, a0):
        last = []
        for i in range(1, self.slides_tabs.count()):
            widget = self.slides_tabs.widget(i)
            if isinstance(widget, Slides):
                last.append({"filename": widget.filename, "page": widget.page})
        self.cfg_last.set_value(last)
        self.config.save(self.script_path + "spiceditor.yaml")

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.menuBar().show()
        else:
            self.showFullScreen()
            self.menuBar().hide()
        self.cfg_open_fullscreen.set_value(self.isFullScreen())

    def code_from_slide(self, code):
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            editor = self.editors_tabs.currentWidget()
            if not isinstance(editor, EditorWidget):
                return
            editor.language_editor.set_code(editor.language_editor.code + "\n" + code)
        else:
            editor = self.new_editor_tab(self.console_widget)
            editor.language_editor.set_code(code)

        editor.language_editor.set_mode(1)
        editor.language_editor.setFocus()
        self.slides_tabs.setCurrentIndex(0)
        editor.show_all_code()

    def back_to_tabs(self):
        slides = self.slides_helper.layout().itemAt(2).widget()
        print("Back to tabs:", slides)
        self.slides_tabs.addTab(slides, slides.filename)
        self.slides_tabs.setCurrentWidget(slides)
        slides.view.setFocus()
        self.back_to_tabs_btn.setVisible(False)


    def slide_tab_double_clicked(self, index):
        if index == 0:
            return
        if self.slides_helper.layout().count() > 2:
            self.back_to_tabs()
        widget = self.slides_tabs.widget(index)
        self.slides_helper.layout().addWidget(widget)
        self.back_to_tabs_btn.setVisible(True)
        widget.show()
        self.slides_tabs.setCurrentIndex(0)
