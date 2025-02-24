import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QVBoxLayout, QToolBar, QStatusBar, QWidget, QComboBox, QShortcut, QTabWidget, QFileDialog, \
    QApplication, QDialog, QMessageBox
from spice import utils

import spice.resources  # noqa


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
        self.config = config
        editor = config.root().addSubSection("editor", pretty="Editor")
        self.cfg_keep_code = editor.addCheckbox("keep_code",
                            pretty="Keep Code on Run",
                            default=False)
        self.cfg_show_all = editor.addCheckbox("show_all",
                            pretty="Show all Code on Open",
                            default=False)
        self.cfg_progs_path = editor.addFolderChoice("progs_path",
                                                      pretty="Programs Path",
                                                      default=str(os.getcwd()) + os.sep + "progs" + os.sep)
        self.cfg_autocomplete = editor.addString("autocomplete",
                                                  pretty="Autocomplete",
                                                  default="")
        self.cfg_delay = editor.addSlider("delay",
                                           pretty="Delay",
                                           min=0, max=100,
                                           default=25,
                                           den=1,
                                           show_value=True,
                                           suffix=" ms")

        self.cfg_show_sb = editor.addCheckbox("show_tb",
                                               pretty="Show Toolbar",
                                               default=False)


        self.language_editor = language_editor
        self.console = console

        self.prog_cb = DynamicComboBox()
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
        left_layout.addWidget(self.sb)
        left_layout.setSpacing(0)

        self.setLayout(left_layout)
        self.setLayout(left_layout)

    def update_config(self):
        print("updating config", self.cfg_progs_path.get_value())
        if not os.path.exists(self.cfg_progs_path.get_value()):
            QMessageBox.critical(self, "Warning", "The path " + self.cfg_progs_path.get_value() + " does not exist, using default")
            self.cfg_progs_path.set_value(str(os.getcwd()))
            print("risssss")

        self.prog_cb.set_folder(self.cfg_progs_path.get_value())
        self.keep_banner.setChecked(self.cfg_keep_code.get())
        self.show_all.setChecked(self.cfg_show_all.get())
        self.language_editor.append_autocomplete(self.cfg_autocomplete.get())
        self.language_editor.set_delay(self.cfg_delay.get())
        self.language_editor.set_font_size(self.config.font_size.get() + 10)

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

        with open(self.cfg_progs_path.get() + os.sep + file_name) as f:
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
