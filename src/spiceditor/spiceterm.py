import os
import sys

from PyQt5.QtWidgets import QApplication

from spiceditor.main_window import MainWindow, parse_args
from spiceditor.spice_console import TermQtConsole


def main():
    args = parse_args()  # before Qt: -h and errors exit cleanly
    app = QApplication(sys.argv)
    window = MainWindow(TermQtConsole, args)
    window.show()

    ret = app.exec_()
    # Leave without Python's interpreter teardown. Closing the window has
    # already done Spice's cleanup (config saved, collaboration left) and the
    # terminal's shell gets a hangup when we exit. A normal exit lets Python
    # destroy the Qt objects in random order, after the QApplication is gone,
    # which floods "QGuiApplication::font(): no QGuiApplication instance"
    # and often ends in a segmentation fault.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(ret)


if __name__ == "__main__":
    main()