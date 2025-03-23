import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QVBoxLayout, QToolBar, QStatusBar, QWidget, QComboBox, QShortcut, QTabWidget, QFileDialog, \
    QApplication, QDialog, QMessageBox
from spiceditor import utils

import spiceditor.resources  # noqa


class DynamicComboBox(QComboBox):
    def __init__(self, folder=None, parent=None):
        super().__init__(parent)
        self.folder = folder
        self.populate()

    def set_folder(self, folder):
        self.folder = folder
        self.populate()


    def populate(self, item=None):
        self.blockSignals(True)
        self.clear()  # Clear the current items
        self.addItem("[Free Coding]")
        if self.folder is not None and os.path.exists(self.folder):
            files = list(x for x in os.listdir(self.folder) if x.endswith(".py"))

            files = [f for f in files if os.path.isfile(os.path.join(self.folder, f))]
            files.sort()
            self.addItems(files)
            if item is not None:
                index = self.findText(item)
                if index >=0:
                    self.setCurrentIndex(index)
            self.blockSignals(False)



class EditorWidget(QWidget):

    def __init__(self, language_editor, console, config):
        super().__init__()
        self.path = None
        self.config = config
        editor = config.root().getSubSection("editor", pretty="Editor")
        self.cfg_keep_code = editor.getCheckBox("keep_code",
                            pretty="Keep Code on Run",
                            default=False)
        self.cfg_show_all = editor.getCheckBox("show_all",
                            pretty="Show all Code on Open",
                            default=False)
        self.cfg_autocomplete = editor.getString("autocomplete",
                                                  pretty="Autocomplete",
                                                  default="")
        self.cfg_delay = editor.getSlider("delay",
                                           pretty="Delay",
                                           min=0, max=100,
                                           default=25,
                                           den=1,
                                           show_value=True,
                                           suffix=" ms")

        self.cfg_show_sb = editor.getCheckBox("show_tb",
                                               pretty="Show Toolbar",
                                               default=False)


        self.language_editor = language_editor
        self.console = console

        # Left side layout
        left_layout = QVBoxLayout()

        self.language_editor.ctrl_enter.connect(self.execute_code)
        self.language_editor.info.connect(self.update_status_bar)

        bar = QToolBar()

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

        left_layout.addWidget(bar)
        left_layout.addWidget(self.language_editor)

        self.sb = QStatusBar()
        left_layout.addWidget(self.sb)
        left_layout.setSpacing(0)

        self.setLayout(left_layout)
        self.setLayout(left_layout)

    def update_config(self):
        self.keep_banner.setChecked(self.cfg_keep_code.get())
        self.show_all.setChecked(self.cfg_show_all.get())
        self.language_editor.append_autocomplete(self.cfg_autocomplete.get())
        self.language_editor.set_delay(self.cfg_delay.get())
        self.language_editor.set_font_size(self.config.root().get_node("font_size").get() + 10)

    def set_font_size(self, font_size):
        self.language_editor.set_font_size(font_size)
        self.console.set_font_size(font_size)

    def load_program(self, path, show_all=False):
        self.path = path
        with open(path) as f:
            self.language_editor.set_code(f.read())
            self.console.clear()

        if self.show_all.isChecked() or show_all:
            self.show_all_code()

    def save_program(self, path, save_as):
        if self.path is None or save_as:
            ext = self.console.get_file_extension()
            filename, ok = QFileDialog.getSaveFileName(self, "Save code", filter="Language files (*" + ext + ")",
                                                       directory=path)
            if not filename:
                return

            self.path = filename.replace(".py","") + ".py"

        with open(self.path, "w") as f:
            f.write(self.language_editor.toPlainText())

        name = os.path.basename(self.path)
        tab_wiget: QTabWidget = self.parent().parent()  # noqa
        index = tab_wiget.indexOf(self)
        tab_wiget.setTabText(index, name)
        self.sb.showMessage("Saved in " + self.path, 2000)

    def clear(self):
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
        self.language_editor.show_all_code()

    def set_progs_path(self, path):
        value = self.prog_cb.currentText()
        self.prog_cb.set_folder(path)
        self.populate_progs()
        self.prog_cb.setCurrentIndex(self.prog_cb.findText(value))

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
