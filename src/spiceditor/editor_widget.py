import os
import re

from PyQt5.QtCore import Qt, QEvent, QFileSystemWatcher, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QTextCursor, QKeyEvent, QColor
from PyQt5.QtWidgets import QVBoxLayout, QToolBar, QStatusBar, QWidget, QComboBox, QShortcut, QTabWidget, QFileDialog, \
    QApplication, QDialog, QMessageBox, QLabel, QHBoxLayout, QPushButton, QSizePolicy

from spiceditor import utils

import spiceditor.resources  # noqa
from spiceditor.jupyter_console import JupyterConsole


class MyStatusBar(QStatusBar):
    def __init__(self):
        super().__init__()
        self.setSizeGripEnabled(False)
        self.label = QLabel()

        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.label.setContentsMargins(0, 5, 0, 0)
        self.addWidget(self.label)

        # collaboration status of this tab, independent of the messages above
        self.collab_label = QLabel()
        self.collab_label.setContentsMargins(0, 5, 8, 0)
        self.collab_label.hide()
        self.addPermanentWidget(self.collab_label)

        self.buttons = []
        self.x_button = QPushButton("❌")
        self.x_button.setMaximumWidth(25)
        self.x_button.hide()
        self.x_button.setContentsMargins(0, 5, 0, 0)
        self.x_button.clicked.connect(self.reset)
        self.addPermanentWidget(self.x_button)

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.reset)
        self.hide()

    def showMessage(self, message, msecs=0, *args, **kwargs):
        self.show()
        font = self.label.font()
        font.setBold(kwargs.get("bold", False))
        self.label.setFont(font)
        self.label.setText(message)
        self.x_button.show()

        for button in self.buttons:
            self.removeWidget(button)

        buttons = kwargs.get("buttons", [])
        for name, callback in buttons:
            button = QPushButton(name)
            button.clicked.connect(callback)
            button.show()
            self.insertPermanentWidget(1, button)
            self.buttons.append(button)

        if msecs >= 0:
            self.timer.stop()
        if msecs > 0:
            self.timer.start(msecs)

    def reset(self):
        self.label.setText("")
        self.x_button.hide()
        for button in self.buttons:
            self.removeWidget(button)
        if not self.collab_label.text():
            self.hide()

    def set_collab_status(self, text):
        self.collab_label.setText(text)
        self.collab_label.setVisible(bool(text))
        if text:
            self.show()
        elif not self.label.text():
            self.hide()


class EditorWidget(QWidget):
    file_modified = pyqtSignal(object, bool)
    focus_in = pyqtSignal(object)
    execute_called = pyqtSignal(object)
    connect_requested = pyqtSignal(object)  # the Connect button: MainWindow asks for the session

    def __init__(self, language_editor, console, config):
        super().__init__()
        self.master = False
        self.automatic_reload = False
        self.path = None
        self.config = config
        self.modified_internally = False
        editor = config.root().getSubSection("editor", pretty="Editor")
        self.cfg_keep_code = editor.getCheckBox("keep_code",
                                                pretty="Keep Code on Run",
                                                default=False)
        self.cfg_autocomplete = editor.getString("autocomplete",
                                                 pretty="Autocomplete",
                                                 default="")
        self.cfg_delay = editor.getSlider("delay",
                                          pretty="Delay",
                                          min=0, max=100,
                                          default=25,
                                          den=1,
                                          show_value=True)

        self.cfg_show_sb = editor.getCheckBox("show_tb",
                                              pretty="Show Toolbar",
                                              default=False)

        self.language_editor = language_editor
        self.console = console
        self.console: JupyterConsole
        self.console.execute_code_requested.connect(self.execute_code)

        # Left side layout
        left_layout = QVBoxLayout()
        self.language_editor.ctrl_enter.connect(self.execute_code)
        self.language_editor.ctrl_shift_enter.connect(self.execute_single_line)
        self.language_editor.info.connect(self.update_status_bar)
        self.language_editor.focus_in.connect(lambda : self.focus_in.emit(self))

        bar = QToolBar()

        a1 = bar.addAction("Play", self.execute_code)
        a2 = bar.addAction("Clear", self.clear)
        a3 = bar.addAction("Show", self.language_editor.show_code)

        self.keep_banner = bar.addAction("Keep Code on Console")
        self.keep_banner.setCheckable(True)
        self.keep_banner.setChecked(False)

        # self.show_all = bar.addAction("Show all Code on Load")
        # self.show_all.setIcon(QIcon(":/icons/radio-button.svg"))
        # self.show_all.setCheckable(True)

        self.text_edit_group = [a1, a2, a3, self.keep_banner]
        bar.addSeparator()

        # collaborative editing for this tab only
        self.connect_action = bar.addAction("Connect")
        self.connect_action.setCheckable(True)
        self.connect_action.triggered.connect(self.connect_clicked)

        left_layout.addWidget(bar)
        left_layout.addWidget(self.language_editor)

        self.sb = MyStatusBar()
        left_layout.addWidget(self.sb)
        self.language_editor.collab_status.connect(self.sb.set_collab_status)
        # e.g. disconnected by the server: the button must follow
        self.language_editor.collab_status.connect(lambda _: self.update_connect_action())
        # left_layout.setSpacing(0)

        self.setLayout(left_layout)
        self.setLayout(left_layout)

        q = QShortcut("F5", self)
        q.activated.connect(self.language_editor.format_code)

        self.file_watcher = QFileSystemWatcher()
        self.file_watcher.fileChanged.connect(self.on_file_changed)

    # ------------------------------------------------------------------
    # collaborative editing
    # ------------------------------------------------------------------
    def connect_clicked(self):
        if self.is_collab_active():
            self.collab_disconnect()
        else:
            self.connect_requested.emit(self)
        self.update_connect_action()

    def collab_connect(self, server_url, session, user_name):
        self.language_editor.connect_to_server(server_url, session, user_name)
        self.update_connect_action()

    def collab_disconnect(self):
        self.language_editor.leave()
        self.sb.set_collab_status("")
        self.update_connect_action()

    def is_collab_active(self):
        return self.language_editor.collab_active

    def collab_session(self):
        return self.language_editor.doc_id if self.is_collab_active() else None

    def update_connect_action(self):
        active = self.is_collab_active()
        self.connect_action.setChecked(active)
        self.connect_action.setText("Disconnect" if active else "Connect")
        self.connect_action.setToolTip(
            f"Leave session {self.language_editor.doc_id}" if active
            else "Share this tab's code: join a session on a collaboration server")

    def is_modified(self):
        return self.modified

    def set_master(self, master):
        self.master = master


    def is_master(self):
        return self.master

    def on_file_changed(self, path):

        if self.automatic_reload:
            focus = QApplication.focusWidget()
            self.reload_clicked()
            if focus:
                focus.setFocus()
            return

        if not self.modified_internally:
            self.sb.showMessage("File changed externally", buttons=[("Reload", self.reload_clicked),
                                                              ("Reload Automatically", self.set_automatic_reload)])

            self.file_modified.emit(self, True)
        self.modified_internally = False

    def set_automatic_reload(self):
        self.sb.showMessage("File will be reloaded automatically", 2000)
        self.reload_clicked()
        self.automatic_reload = True

    def reload_clicked(self):
        self.modified_internally = True
        if self.path is not None:
            self.load_program(self.path, show_all=True)
            self.sb.showMessage("File reloaded", 2000)
        else:
            self.sb.showMessage("Nothing to reload", 2000)

    def update_config(self):
        self.keep_banner.setChecked(self.cfg_keep_code.get())
        # self.show_all.setChecked(self.cfg_show_all.get())
        self.language_editor.append_autocomplete(self.cfg_autocomplete.get())
        self.language_editor.set_delay(self.cfg_delay.get())
        self.language_editor.set_font_size(self.config.root().get_node("font_size").get() + 10)

    def set_font_size(self, font_size):
        self.language_editor.set_font_size(font_size)
        self.console.set_font_size(font_size)

    def load_program(self, path, show_all=False):
        self.path = path
        with open(path, encoding="utf-8", errors="ignore") as f:
            self.language_editor.set_code(f.read())
            self.console.clear()
            if len(self.file_watcher.files()) > 0:
                self.file_watcher.removePaths(self.file_watcher.files())
            self.file_watcher.addPath(path)
            self.file_modified.emit(self, False)
            self.modified_internally = False

        if show_all:
            self.show_all_code()

    def on_disk(self):
        return self.path is not None and os.path.exists(self.path)
    def is_selectable(self):
        return self.on_disk() == False or self.path.endswith(".py")
    def save_program(self, path, save_as):
        if self.path is None or save_as:
            ext = self.console.get_file_extension()
            filename, selected_filter = QFileDialog.getSaveFileName(self, "Save code", directory=path,
                                                       filter="All files (*.*);; Language files (*" + ext + ");;CSV files (*.csv);;YAML files (*.yaml *.yml);; TXT files (*.txt)")
            if not filename:
                return
            if len(self.file_watcher.files()) > 0:
                self.file_watcher.removePaths(self.file_watcher.files())
            if "py" in selected_filter:
                self.path = filename.replace(".py", "") + ".py"
            elif "csv" in selected_filter:
                self.path = filename.replace(".csv", "") + ".csv"
            elif "yaml" in selected_filter:
                self.path = filename.replace(".yaml", "").replace(".yml", "") + ".yaml"
            elif "txt" in selected_filter:
                self.path = filename.replace(".txt", "") + ".txt"
            else:
                self.path = filename

            self.file_watcher.addPath(self.path)
            self.file_modified.emit(self, False)

        self.modified_internally = True
        with open(self.path, "w") as f:
            #### f.write(self.language_editor.toPlainText())
            text = self.language_editor.toPlainText()
            text = text.encode("utf-8", errors="ignore").decode("utf-8")
            f.write(text)

        name = os.path.basename(self.path)
        tab_wiget: QTabWidget = self.parent().parent()  # noqa
        index = tab_wiget.indexOf(self)
        tab_wiget.setTabText(index, name)
        self.sb.showMessage("Saved in " + self.path, 2000)

    def clear(self):
        self.language_editor.clear()
        # self.console_widget.clear()

    def clean_for_utf8(self, s: str) -> str:
        # Remove surrogates, noncharacters, and invalid JSON control chars
        # \x09, \x0A, \x0D are tab, LF, CR which are safe
        return re.sub(
            r'[\ud800-\udfff\uFFFE\uFFFF\x00-\x08\x0B\x0C\x0E-\x1F]',
            '',
            s
        )

    # this goes to main_window that decides if this code
    # actually runs (run_code) or the main program must run
    def execute_code(self):
        self.execute_called.emit(self)

    def run_code(self):
        self.language_editor.setFocus()
        if self.config.root().get_child("format_code_before_run").get_value():
            self.language_editor.format_code()

        #### self.console.execute(self.language_editor.toPlainText(), not self.keep_banner.isChecked())

        text = self.language_editor.toPlainText()
        text = text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
        text = self.clean_for_utf8(text) + "\n\n"
        self.console.execute(text, not self.keep_banner.isChecked())

        if "input(" in text:
            self.console.set_editor_focus()

    def execute_single_line(self, advance=False):
        line = self.language_editor.get_current_line()
        self.console.execute(line, not self.keep_banner.isChecked())
        if advance:
            self.language_editor.moveCursor(QTextCursor.Down)

    def set_dark_mode(self, dark):
        self.language_editor.set_dark_mode(dark)
        color = Qt.white if dark else Qt.black
        a1, a2, a3, a4 = self.text_edit_group
        a1.setIcon(QIcon(utils.color(":/icons/play.svg", color)))
        a2.setIcon(QIcon(utils.color(":/icons/refresh.svg", color)))
        a3.setIcon(QIcon(utils.color(":/icons/download.svg", color)))
        a4.setIcon(QIcon(utils.color(":/icons/hash.svg", color)))
        self.connect_action.setIcon(QIcon(utils.color(":/icons/link.svg", color)))

    def get_text(self):
        self.language_editor.format_code()
        return self.language_editor.text_edit.toPlainText()

    def get_font_size(self):
        return self.language_editor.font().pixelSize()

    def append_autocomplete(self, value, val):
        self.language_editor.append_autocomplete(value, val)

    def set_delay(self, value):
        self.language_editor.set_delay(value)

    def show_all_code(self):
        self.language_editor.show_all_code()

    def set_progs_path(self, path):
        value = self.prog_cb.currentText()
        self.prog_cb.set_folder(path)
        self.populate_progs()
        self.prog_cb.setCurrentIndex(self.prog_cb.findText(value))

    def update_status_bar(self, x, diff, timeout):
        return
        if self.cfg_show_sb.get_value():
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

    def get_editor(self):
        return self.language_editor
