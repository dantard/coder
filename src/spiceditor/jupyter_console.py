from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QToolBar
from qtconsole.manager import QtKernelManager

from spiceditor.silent_jupyter_widget import SilentRichJupyterWidget
from spiceditor.spice_console import SpiceConsole


# noinspection PyProtectedMember
class JupyterConsole(SpiceConsole):

    def __init__(self, config):
        super().__init__(config)
        self.path = None
        kernel_manager = QtKernelManager(kernel_name='python3')
        kernel_manager.start_kernel()
        kernel_client = kernel_manager.client()
        kernel_client.start_channels()

        self.jupyter_widget = SilentRichJupyterWidget()

        font = QFont("Monospace")
        font.setStyleHint(QFont.TypeWriter)
        font.setPixelSize(18)
        self.jupyter_widget.font = font

        # self.jupyter_widget._set_font()
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
        bar = QToolBar()
        bar.addAction(QIcon(":/icons/refresh.svg"), "Restart Kernel", self.restart_kernel)

        layout.addWidget(bar)
        layout.addWidget(self.jupyter_widget)
        self.setLayout(layout)
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.done.emit)

    def restart_kernel(self):
        self.jupyter_widget._control.setText("** Kernel Restarted **")
        self.jupyter_widget.kernel_manager.restart_kernel()
        self.jupyter_widget.execute("cd " + self.path, hidden=True)
        self.jupyter_widget.execute("", interactive=True)

    def set_editor_focus(self):
        self.jupyter_widget._control.setFocus()

    def config_read(self):
        pass

    def update_config(self, **kwargs):

        self.path = self.config.root().get_node("progs_path").get_value()
        if self.path:
            self.jupyter_widget.execute("cd " + self.path, hidden=True)

        size = self.config.root().get_node("font_size").get_value()

        if size >= 0:
            self.set_font_size(size + 10)

    def set_dark_mode(self, value):
        if value:
            self.jupyter_widget.set_default_style(colors='linux')
        else:
            self.jupyter_widget.set_default_style(colors='lightbg')

    def execute(self, code, clear=True):
        def run():
            if code.strip():
                self.jupyter_widget.set_echo(False)
                self.jupyter_widget.execute(code, interactive=True)
                self.jupyter_widget.set_echo(True)
                # if clear:
                #    self.jupyter_widget._control.clear()

        # check if kernel is busy, in that case interrupt it to avoid stuck state
        if self.jupyter_widget.kernel_client.is_alive() and self.jupyter_widget._executing:
            self.jupyter_widget.interrupt_kernel()

        clear_modules = '''
        %reset -f
        import os
        import sys
        cwd = os.getcwd()
        deleting = []
        for k,v in sys.modules.items():
            try:
                if cwd in v.__file__:
                    deleting.append(k)
            except:
                pass
        for k in deleting:
            del sys.modules[k]
        '''
        clear_modules2 = '''
        %reset -f
        import os
        import sys
        import time
        cwd = os.getcwd()
        deleting = []
        
        for k,v in sys.modules.items():
            try:
                if v.__file__:
                    mtime = os.path.getmtime(v.__file__)
                    if time.time() - mtime < 3600:
                        deleting.append(k)
            except:
                pass
        for k in deleting:
            del sys.modules[k] 
        '''

        # self.jupyter_widget.kernel_manager.restart_kernel()
        self.jupyter_widget.execute(clear_modules2, hidden=True)
        # QTimer.singleShot(100, run)
        run()

    def clear(self):
        pass  # self.jupyter_widget.execute("%clear")

    def set_font_size(self, font_size):
        font = QFont("Monospace")
        font.setStyleHint(QFont.TypeWriter)
        font.setPixelSize(font_size)
        self.jupyter_widget._control.setFont(font)
