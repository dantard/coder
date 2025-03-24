import sys

from PyQt5.QtWidgets import QApplication

from spiceditor.main_window import MainWindow
from spiceditor.spice_console import JupyterConsole


def main():
    app = QApplication(sys.argv)
    window = MainWindow(JupyterConsole)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()