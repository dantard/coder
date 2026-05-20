import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from spiceditor.jupyter_console import JupyterConsole
from spiceditor.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    font = QFont("Monospace")
    font.setStyleHint(QFont.TypeWriter)
    window = MainWindow(JupyterConsole)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()