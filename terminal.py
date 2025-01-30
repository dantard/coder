import os
import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication
from qtconsole.manager import QtKernelManager
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from termqt import Terminal
#from qtpyTerminal import qtpyTerminal

class SpiceTerminal(QWidget):
    def execute(self, code, clear=True):
        pass

    def clear(self):
        pass


class Jupyter(SpiceTerminal):

    def __init__(self, font_size=18):
        super().__init__()

        kernel_manager = QtKernelManager(kernel_name='python3')
        kernel_manager.start_kernel()
        kernel_client = kernel_manager.client()
        kernel_client.start_channels()

        self.jupyter_widget = RichJupyterWidget()
        font = QFont("Monospace")
        font.setStyleHint(QFont.TypeWriter)
        font.setPixelSize(font_size)
        self.jupyter_widget.font = font

        #self.jupyter_widget._set_font()
        self.jupyter_widget.kernel_manager = kernel_manager
        self.jupyter_widget.kernel_client = kernel_client

        # Customize the prompt
        self.jupyter_widget.include_other_output = False
        self.jupyter_widget.banner = ""  # Remove banner
        self.jupyter_widget.input_prompt = ""  # Remove input prompt
        self.jupyter_widget.output_prompt = ""  # Remove output prompt
        self.jupyter_widget.set_default_style(colors='linux')

        self.editor = self.jupyter_widget._control

        layout = QVBoxLayout()
        layout.addWidget(self.jupyter_widget)
        self.setLayout(layout)

    def execute(self, code, clear=True):

        # self.jupyter_widget._control.setText("")
        def filtering():
            text = self.editor.toPlainText()
            if text.endswith("   ...: "):
                if clear:
                    self.editor.clear()

        self.editor.textChanged.connect(filtering)
        # self.jupyter_widget._control.setFocus()
        QApplication.processEvents()

        def run():
            if code.strip():
                self.jupyter_widget.execute(code, interactive=True)
                # if not self.keep_banner.isChecked():
                #    self.jupyter_widget._control.clear()

        QTimer.singleShot(100, run)

    def clear(self):
        self.jupyter_widget.execute("%clear")

import platform

class Console(SpiceTerminal):
    def __init__(self):
        super().__init__()
        self.terminal = Terminal(400, 600)

        layout = QVBoxLayout()
        layout.addWidget(self.terminal)
        self.setLayout(layout)

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
        #self.terminal.input("python")




    def execute(self, code, clear=True):
        with open("output.pas", "w") as f:
            f.write(code)
        command = "FreePascal"+os.sep+"bin"+os.sep+"i386-win32"+os.sep+"fpc.exe output.pas && output.exe\r\n"
        self.terminal.input(command.encode("utf-8"))

    def clear(self):
        self.terminal.input("clear\r\n".encode("utf-8"))



class Console2(SpiceTerminal):
    def __init__(self):
        super().__init__()
        self.terminal = qtpyTerminal()
        self.terminal.term.setFont(QFont("Monospace", 14))
        self.terminal.term.setMinimumWidth(200)
        self.terminal.setMinimumWidth(200)


        layout = QVBoxLayout()
        layout.addWidget(self.terminal)
        self.setLayout(layout)
        self.terminal.start()


    def execute(self, code, clear=True):
        with open("output.pas", "w") as f:
            f.write(code)
        self.terminal.push("fpc output.pas && ./output\n")

    def clear(self):
        self.terminal.push("clear\n")