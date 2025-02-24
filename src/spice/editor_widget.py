import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QVBoxLayout, QToolBar, QStatusBar, QWidget, QComboBox, QShortcut, QTabWidget, QFileDialog, \
    QApplication
from spice import utils

import spice.resources  # noqa


class DynamicComboBox(QComboBox):
    def __init__(self, folder, parent=None):
        super().__init__(parent)
        self.folder = folder
        self.populate()

    def set_folder(self, folder):
        self.folder = folder

    def populate(self, item=False):
        self.blockSignals(True)
        self.clear()  # Clear the current items
        self.addItem("[Free Coding]")
        if os.path.exists(self.folder):
            files = list(os.listdir(self.folder))
            files = [f for f in files if os.path.isfile(os.path.join(self.folder, f))]
            files.sort()
            self.addItems(files)
            if item:
                self.setCurrentIndex(self.findText(item))
        self.blockSignals(False)


class EditorWidget(QWidget):

    def __init__(self, language_editor, console, config):
        super().__init__()
        self.cfg_progs_path = config.root().get_child("progs_path")
        self.cfg_show_sb = config.root().get_child("show_tb")
        self.cfg_show_all = config.root().get_child("show_all")
        self.cfg_keep_code = config.root().get_child("keep_code")

        self.language_editor = language_editor
        self.console = console

        self.prog_cb = DynamicComboBox(self.cfg_progs_path.get_value())
        self.prog_cb.currentIndexChanged.connect(self.load_program)
        font = QFont("Monospace")
        font.setStyleHint(QFont.TypeWriter)
        font.setPixelSize(16)
        self.prog_cb.setFont(font)

        q = QShortcut("Ctrl+S", self)
        q.activated.connect(self.save_program)
        q = QShortcut("Ctrl+Shift+S", self)
        q.activated.connect(lambda : self.save_program(True))

        # Left side layout
        left_layout = QVBoxLayout()

        self.language_editor.ctrl_enter.connect(self.execute_code)
        self.language_editor.info.connect(self.update_status_bar)

        bar = QToolBar()
        bar.addWidget(self.prog_cb)
        bar.addSeparator()

        a1 = bar.addAction("Play", self.execute_code)

        a2 = bar.addAction("Clear", self.clear)
        a3 = bar.addAction("Show", self.language_editor.show_code)

        self.keep_banner = bar.addAction("Keep Code on Console")
        self.keep_banner.setCheckable(True)
        self.keep_banner.setChecked(False)

        self.show_all =  bar.addAction("Show all Code on Load")
        self.show_all.setIcon(QIcon(":/icons/radio-button.svg"))
        self.show_all.setCheckable(True)

        self.text_edit_group = [a1, a2, a3, self.keep_banner]
        bar.addSeparator()

        self.prog_cb.setMinimumWidth(300)

        left_layout.addWidget(bar)
        left_layout.addWidget(self.language_editor)

        self.sb = QStatusBar()
        #if self.cfg_show_sb.get_value():
        left_layout.addWidget(self.sb)

        # left_layout.addWidget(self.run_button)
        left_layout.setSpacing(0)
        # left_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(left_layout)

        self.keep_banner.setChecked(self.cfg_keep_code.get_value())
        self.show_all.setChecked(self.cfg_show_all.get_value())

    def set_font_size(self, font_size):
        self.language_editor.set_font_size(font_size)
        self.console.set_font_size(font_size)

    def load_program(self):
        tab_wiget: QTabWidget = self.parent().parent() # noqa
        index = tab_wiget.indexOf(self)
        tab_wiget.setTabText(index, self.prog_cb.currentText())

        if self.prog_cb.currentIndex() == 0:
            self.clear()
            return

        file_name = self.prog_cb.currentText()
        folder = self.cfg_progs_path.get_value()


        with open(folder + os.sep + file_name) as f:
            #    self.text_edit.setPlainText(f.read())
            self.language_editor.set_code(f.read())
            self.console.clear()

        if self.show_all.isChecked():
            self.show_all_code()

    def save_program(self, save_as=False):
        if self.prog_cb.currentIndex() > 0 and not save_as:
            filename = self.cfg_progs_path.get_value() + os.sep + self.prog_cb.currentText()
            ok = True
        else:
            ext = self.console.get_file_extension()
            path = self.cfg_progs_path.get_value() + os.sep
            filename, ok = QFileDialog.getSaveFileName(self, "Save code", filter="Language files (*" + ext + ")",
                                                       directory=path)
            if not filename:
                return

            filename = filename.replace(ext, "") + ext
        if ok:
            with open(filename, "w") as f:
                f.write(self.language_editor.toPlainText())
            print("saving in ", filename)
            name = filename.split(os.sep)[-1]
            self.prog_cb.populate(name)
            tab_wiget: QTabWidget = self.parent().parent()  # noqa
            index = tab_wiget.indexOf(self)
            tab_wiget.setTabText(index, name)
            self.sb.showMessage("Saved in " + filename, 2000)

    def clear(self):
        self.prog_cb.setCurrentIndex(0)
        self.language_editor.clear()
        # self.console_widget.clear()

    def execute_code(self):
        self.language_editor.format_code()
        self.console.execute(self.language_editor.toPlainText(), not self.keep_banner.isChecked())

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
        if QApplication.keyboardModifiers() or self.show_all.isChecked():
            self.language_editor.show_all_code()

    def update_status_bar(self, x, diff, timeout):
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
