import os
import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from spiceditor.jupyter_console import JupyterConsole
from spiceditor.main_window import MainWindow, parse_args


def main():
    args = parse_args()  # before Qt: -h and errors exit cleanly
    app = QApplication(sys.argv)
    font = QFont("Monospace")
    font.setStyleHint(QFont.TypeWriter)
    window = MainWindow(JupyterConsole, args)
    window.show()

    ret = app.exec_()
    # Leave without Python's interpreter teardown. Closing the window has
    # already done Spice's cleanup (config saved, collaboration left) and the
    # Jupyter kernel stops when it sees us exit. A normal exit lets Python
    # destroy the Qt objects in random order, after the QApplication is gone,
    # which floods "QGuiApplication::font(): no QGuiApplication instance"
    # and often ends in a segmentation fault.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(ret)


if __name__ == "__main__":
    main()