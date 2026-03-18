import sys

from PyQt5.QtWidgets import QApplication

from spiceditor.jupyter_console import JupyterConsole
from spiceditor.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow(JupyterConsole)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()