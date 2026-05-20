import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication, QPlainTextEdit, QTextEdit, QPushButton
from PyQt5.uic.Compiler.qtproxies import QtCore
from easyconfig2.easyconfig import EasyConfig2
from qtconsole.manager import QtKernelManager
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from termqt import Terminal

from spiceditor.silent_jupyter_widget import SilentRichJupyterWidget


# from qtpyTerminal import qtpyTerminal

class SpiceConsole(QWidget):
    done = pyqtSignal()

    def __init__(self, config):
        super().__init__()
        self.keep_code = False
        self.config = config

    def execute(self, code, clear=True):
        pass

    def clear(self):
        pass

    def set_dark_mode(self, value):
        pass

    def set_font_size(self, size):
        pass

    def set_config(self, config):
        self.config = config

    def config_read(self):
        pass

    def set_keep_code(self, value):
        self.keep_code = value

    def get_file_extension(self):
        return ".py"

    def update_config(self, **kwargs):
        pass

    def set_editor_focus(self):
        pass


class OverriddenBehaviorTextEdit(QTextEdit):  # Not used
    def __init__(self):
        super().__init__()




# noinspection PyProtectedMember



import platform


class TermQtConsole(SpiceConsole):
    def __init__(self, config):
        super().__init__(config)
        self.terminal = Terminal(600, 400, font_size=18)
        layout = QVBoxLayout()
        layout.addWidget(self.terminal)
        self.setLayout(layout)
        self.setMinimumSize(600, 400)

        my_platform = platform.system()

        if my_platform in ["Linux", "Darwin"]:
            bin = "/bin/bash"

            from termqt import TerminalPOSIXExecIO
            terminal_io = TerminalPOSIXExecIO(
                self.terminal.row_len,
                self.terminal.col_len,
                bin
            )
        elif my_platform == "Windows":
            bin = "cmd"

            from termqt import TerminalWinptyIO
            terminal_io = TerminalWinptyIO(
                self.terminal.row_len,
                self.terminal.col_len,
                bin
            )

            # it turned out that cmd prefers to handle resize by itself
            # see https://github.com/TerryGeng/termqt/issues/7
            auto_wrap_enabled = False
        else:
            sys.exit(-1)

        self.terminal.enable_auto_wrap(True)

        terminal_io.stdout_callback = self.terminal.stdout
        self.terminal.stdin_callback = terminal_io.write
        self.terminal.resize_callback = terminal_io.resize
        terminal_io.spawn()
        # self.terminal.input("python")
        self.set_config(config)

        QTimer.singleShot(100, lambda: self.resize(0))

    def resize(self, a0):
        self.terminal.resize(self.width(), self.height())

    def set_config(self, config: EasyConfig2):
        super().set_config(config)
        terminal = config.root().addSubSection("Terminal")
        self.init = terminal.addString("init", pretty="Init command (e.g. python)")
        self.temp_file = terminal.addString("temp_file", pretty="Temp file name")
        self.command = terminal.addString("command", pretty="Command")
        # self.file_extension = terminal.addCombobox("file_extension", pretty="File extension", items=[".py", ".pas"])

    def config_read(self):
        super().config_read()

        init = self.init.get_value()
        if init is not None:
            init += "\n"
            self.terminal.input(init.encode("utf-8"))

    def execute(self, code, clear=True):
        temp_file = self.temp_file.get_value()
        if temp_file is not None and temp_file.strip():
            with open(temp_file, "w") as f:
                f.write(code)
        else:
            self.terminal.input(code.encode("utf-8"))

        command = self.command.get_value()
        if command is not None and command.strip():
            command += "\r\n"
            self.terminal.input(command.encode("utf-8"))

        self.terminal.input("\n".encode("utf-8"))

    def clear(self):
        self.terminal.input("clear\r\n".encode("utf-8"))

    def get_file_extension(self):
        return self.file_extension.get_item(self.file_extension.get(0))

    def set_font_size(self, size):
        try:
            self.terminal.font_size = int(size * 0.75)
            font = QFont("Monospace")
            font.setStyleHint(QFont.Monospace)
            font.setPointSize(size)
            self.terminal.set_font(font)
            # self.terminal.input("clear\r\n".encode("utf-8"))
        except:
            pass

    def update_config(self):
        font_size = self.config.root().get_child("font_size").get_value()
        if font_size is not None:
            self.set_font_size(font_size + 10)

    def resizeEvent(self, a0):
        # TODO: self.terminal.set_canvas_size(self.width(), self.height())
        pass

# class Console2(SpiceTerminal):
#     def __init__(self):
#         super().__init__()
#         self.terminal = qtpyTerminal()
#         self.terminal.term.setFont(QFont("Monospace", 14))
#         self.terminal.term.setMinimumWidth(200)
#         self.terminal.setMinimumWidth(200)
#
#         layout = QVBoxLayout()
#         layout.addWidget(self.terminal)
#         self.setLayout(layout)
#         self.terminal.start()
#
#     def execute(self, code, clear=True):
#         with open("output.pas", "w") as f:
#             f.write(code)
#         self.terminal.push("fpc output.pas && ./output\n")
#
#     def clear(self):
#         self.terminal.push("clear\n")
