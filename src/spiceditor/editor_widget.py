import os
import re

from PyQt5.QtCore import Qt, QEvent, QFileSystemWatcher, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QTextCursor, QKeyEvent
from PyQt5.QtWidgets import QVBoxLayout, QToolBar, QStatusBar, QWidget, QComboBox, QShortcut, QTabWidget, QFileDialog, \
    QApplication, QDialog, QMessageBox, QLabel, QHBoxLayout, QPushButton, QSizePolicy

from spiceditor import utils

import spiceditor.resources  # noqa
from spiceditor.spice_console import JupyterConsole


class MyStatusBar(QStatusBar):
    def __init__(self):
        super().__init__()
        self.setSizeGripEnabled(False)
        self.label = QLabel()

        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.label.setContentsMargins(0, 5, 0, 0)
        self.addWidget(self.label)

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

    def showMessage(self, message, msecs=0, *args, **kwargs):
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

        if msecs > 0:
            self.timer.stop()
            self.timer.start(msecs)

    def reset(self):
        self.label.setText("")
        self.x_button.hide()
        for button in self.buttons:
            self.removeWidget(button)


class EditorWidget(QWidget):
    file_modified = pyqtSignal(object, bool)

    def __init__(self, language_editor, console, config):
        super().__init__()
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

        if isinstance(self.console, JupyterConsole):
            # [(key, modifier, action, event^), ...] ^if action is replace otherwise None
            self.console.jupyter_widget.set_key_override(
                [(Qt.Key_Up, Qt.NoModifier, "disable", None),
                 (Qt.Key_Up, Qt.ShiftModifier, "disable", None),
                 (Qt.Key_Return, Qt.ControlModifier, "run", self.execute_code),
                 (Qt.Key_Up, Qt.ControlModifier, "replace", QKeyEvent(QEvent.Type.KeyPress,
                                                                      Qt.Key_Up,
                                                                      Qt.KeyboardModifier.NoModifier
                                                                      )),
                 (Qt.Key_Down, Qt.ControlModifier, "replace", QKeyEvent(QEvent.Type.KeyPress,
                                                                        Qt.Key_Down,
                                                                        Qt.KeyboardModifier.NoModifier
                                                                        ))
                 ])

        # Left side layout
        left_layout = QVBoxLayout()
        self.language_editor.ctrl_enter.connect(self.execute_code)
        self.language_editor.ctrl_shift_enter.connect(self.execute_single_line)
        self.language_editor.info.connect(self.update_status_bar)

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

        left_layout.addWidget(bar)
        left_layout.addWidget(self.language_editor)

        self.sb = MyStatusBar()
        left_layout.addWidget(self.sb)
        # left_layout.setSpacing(0)

        self.setLayout(left_layout)
        self.setLayout(left_layout)

        q = QShortcut("F5", self)
        q.activated.connect(self.language_editor.format_code)

        self.file_watcher = QFileSystemWatcher()
        self.file_watcher.fileChanged.connect(self.on_file_changed)

    def is_modified(self):
        return self.modified

    def on_file_changed(self, path):

        if self.automatic_reload:
            focus = QApplication.focusWidget()
            self.reload_clicked()
            if focus:
                focus.setFocus()
            return

        if not self.modified_internally:
            self.sb.showMessage("Nothing to reload", buttons=[("Reload", self.reload_clicked),
                                                              ("Reload Automatically", self.set_automatic_reload)])

            self.file_modified.emit(self, True)
        self.modified_internally = False

    def set_automatic_reload(self):
        self.sb.showMessage("File will be reloaded automatically", 2000)
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
                print("Removing paths from file watcher", self.file_watcher.files())
                self.file_watcher.removePaths(self.file_watcher.files())
            print("Adding path to file watcher", path)
            self.file_watcher.addPath(path)
            self.file_modified.emit(self, False)
            self.modified_internally = False

        if show_all:
            self.show_all_code()

    def save_program(self, path, save_as):
        if self.path is None or save_as:
            ext = self.console.get_file_extension()
            filename, ok = QFileDialog.getSaveFileName(self, "Save code", filter="Language files (*" + ext + ")",
                                                       directory=path)
            if not filename:
                return
            if len(self.file_watcher.files()) > 0:
                self.file_watcher.removePaths(self.file_watcher.files())
            self.path = filename.replace(".py", "") + ".py"
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

    def execute_code(self):
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
