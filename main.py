import os
import random
import re
import sys
import time
import typing

import resources  # noqa
import yaml
from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter, QTextEdit, QPushButton, QVBoxLayout, QWidget, \
    QToolBar, QComboBox, QTabWidget, QMenu, QMenuBar, QFileDialog, QShortcut, QTabBar, QStatusBar, QHBoxLayout, \
    QPlainTextEdit, QDialog
from PyQt5.QtCore import Qt, QRegExp, pyqtSignal, QTimer, QEvent
from PyQt5.QtGui import QTextCharFormat, QColor, QFont, QSyntaxHighlighter, QPixmap, QPainter, QCursor, QIcon, \
    QTextCursor, QImage
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.manager import QtKernelManager

from editor import PythonEditor, LanguageEditor, PascalEditor
from highlighter import PythonHighlighter, PascalHighlighter
from terminal import Jupyter, Console
from textract import Slides

from utils import create_cursor_image


class CustomTabBar(QTabBar):
    def __init__(self):
        super().__init__()
        # Customize the tab bar as needed
        self.setStyleSheet("QTabBar::tab { background: lightblue; }")
        self.a = QPushButton(self)


class DynamicComboBox(QComboBox):
    def __init__(self, dir, parent=None):
        super().__init__(parent)
        self.dir = dir
        self.addItem("Select program")

    def showPopup(self):
        self.populate()
        super().showPopup()

    def populate(self):
        self.blockSignals(True)
        self.clear()  # Clear the current items
        self.addItem("Select program")
        files = list(os.listdir("progs"))
        files.sort()
        self.addItems(files)
        self.blockSignals(False)


class Author(QDialog):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())
        self.setMinimumSize(400, 350)
        self.setWindowTitle("About")
        textEdit = QTextEdit()
        textEdit.setReadOnly(True)
        textEdit.setHtml("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SPICE - About</title>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            background-color: #f4f4f9;
            color: #333;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            text-align: center;
        }

        .container {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            width: 80%;
            max-width: 600px;
        }

        h1 {
            font-size: 3em;
            color: #2c3e50;
            margin-bottom: 20px;
        }

        p {
            font-size: 1.2em;
            line-height: 1.6;
        }

        ul {
            list-style: none;
            padding: 0;
        }

        ul li {
            font-size: 1.1em;
            margin: 5px 0;
        }

        .footer {
            font-size: 1em;
            color: #7f8c8d;
            margin-top: 20px;
        }

        .footer p {
            margin: 0;
        }

    </style>
</head>
<body>

    <div class="container">
        <h1>Spice</h1>
        <h2><strong>Slides and Python for Interactive and Creative Education</strong></h2>
        
        <h4><strong>Developed by:</strong></h4>
            <h2>Danilo Tardioli</h2>
            <h3>Email: <a href="mailto:dantard@unizar.es">dantard@unizar.es</a></h3>
        
        <p><strong>Year:</strong> 2024</p>

        <div class="footer">
            <p><strong>Learn more at:</strong> <a href="https://github.com/dantard/coder">https://github.com/dantard/coder</a></p>
        </div>
    </div>

</body>
</html>

        """)
        self.layout().addWidget(textEdit)
        close_button = QPushButton("Close")
        close_button.setMaximumWidth(100)
        # center the button
        self.layout().addWidget(close_button)
        self.layout().setAlignment(close_button, Qt.AlignRight)
        close_button.clicked.connect(self.close)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        try:
            with open("config.yaml") as f:
                self.config = yaml.full_load(f)
        except:
            self.config = {}

        self.font_size = self.config.get("font_size", 18)
        self.toolbar_pose = self.config.get("toolbar_pose", 140)

        self.setWindowTitle("Spice")
        # SPICE – Slides, Python, Interactive Creation, and Education
        # slides and python for interactive and creative education

        # self.resize(1000, 600)

        self.tabs = QTabWidget()

        # put tabs bottom
        self.tabs.setTabPosition(QTabWidget.South)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab_requested)
        self.tabs.currentChanged.connect(self.tab_changed)
        tab_bar = self.tabs.tabBar()

        splitter = QSplitter(Qt.Horizontal)

        self.prog_cb = DynamicComboBox("progs")
        self.prog_cb.currentTextChanged.connect(self.load_program)
        font = QFont("Monospace")
        font.setStyleHint(QFont.TypeWriter)
        font.setPixelSize(16)
        self.prog_cb.setFont(font)

        # Left side layout
        left_widget = QWidget()
        left_layout = QVBoxLayout()

        #self.text_edit = LanguageEditor(PythonEditor(PythonHighlighter()))
        self.text_edit = LanguageEditor(PascalEditor(PascalHighlighter()))
        self.text_edit.ctrl_enter.connect(self.execute_code)
        self.text_edit.info.connect(self.update_status_bar)

        bar = QToolBar()
        a1 = bar.addAction("Play", self.execute_code)
        a2 = bar.addAction("Clear", self.clear_all)
        a3 = bar.addAction("Show")#kk, self.text_edit.show_all_code)

        self.keep_banner = bar.addAction("#")
        self.keep_banner.setCheckable(True)
        self.keep_banner.setChecked(False)

        self.text_edit_group = [a1, a2, a3, self.keep_banner]

        left_layout.addWidget(bar)
        left_layout.addWidget(self.prog_cb)

        # lay = QHBoxLayout()
        #
        # self.line_number_area.setReadOnly(True)
        # self.line_number_area.setMaximumWidth(50)
        # lay.addWidget(self.line_number_area)
        # lay.addWidget(self.text_edit)
        # self.text_edit.setLineWrapMode(QTextEdit.NoWrap)

        # self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # self.line_number_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # self.line_number_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # def text_changed():
        #     text = self.text_edit.toPlainText()
        #     lines = text.split("\n")
        #     cursor_pos = self.text_edit.textCursor().position()
        #     v1 = self.line_number_area.verticalScrollBar().value()
        #     self.line_number_area.blockSignals(True)
        #     self.line_number_area.clear()
        #     text = ""
        #
        #     for i in range(len(lines)):  # TODO: was +`11 (maybe for when the editor is full)
        #         # self.line_number_area.append("{:3d}".format(i + 1))
        #         text += "{:3d}\n".format(i + 1)
        #     self.line_number_area.setPlainText(text)
        #
        #     # self.text_edit.setTextCursor(self.text_edit.textCursor())
        #     self.line_number_area.verticalScrollBar().setValue(v1)
        #     self.line_number_area.blockSignals(False)
        #
        # self.text_edit.textChanged.connect(text_changed)
        # self.text_edit.verticalScrollBar().valueChanged.connect(self.line_number_area.verticalScrollBar().setValue)
        # self.text_edit.horizontalScrollBar().rangeChanged.connect(text_changed)
        # self.line_number_area.verticalScrollBar().valueChanged.connect(self.text_edit.verticalScrollBar().setValue)

        left_layout.addWidget(self.text_edit)

        self.sb = QStatusBar()
        if self.config.get("show_status_bar", False):
            left_layout.addWidget(self.sb)

        # left_layout.addWidget(self.run_button)
        left_widget.setLayout(left_layout)

#        lay.setSpacing(0)
#        lay.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        left_layout.setContentsMargins(0, 0, 0, 0)

        splitter.addWidget(left_widget)

        # Right side: RichJupyterWidget
        self.jupyter_widget = Console()
        splitter.addWidget(self.jupyter_widget)

        self.tabs.addTab(splitter, "Code Execution")
        tab_bar.setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        helper = QWidget()
        helper.setContentsMargins(0, 0, 0, 0)
        helper.setLayout(QVBoxLayout())
        helper.layout().setContentsMargins(0, 0, 0, 0)
        helper.layout().setSpacing(0)
        helper.layout().addWidget(self.tabs)
        # helper.layout().addWidget(QStatusBar())
        self.setCentralWidget(helper)

        menu = self.menuBar()
        file = menu.addMenu("File")
        file.addAction("Open", self.open_slides)
        m1 = file.addMenu("Slides")
        file.addSeparator()
        file.addAction("Save As", self.save_as)
        file.addSeparator()
        file.addAction("Exit", self.close)

        m2 = menu.addMenu("Help")
        m2.addAction("About", lambda: Author().exec_())

        def fill():
            m1.clear()
            pwd = os.getcwd()
            path = self.config.get("slides_path", str(pwd) + os.sep + "slides")
            if not os.path.exists(path):
                os.makedirs(path)
            for filename in os.listdir(path):
                m1.addAction(filename, lambda x=filename, y=filename: self.open_slides(pwd + "/slides/" + y))

        m1.aboutToShow.connect(fill)

        q = QShortcut("Ctrl+M", self)
        q.activated.connect(self.toggle_color_scheme)

        q = QShortcut("Ctrl+S", self)
        q.activated.connect(self.save_as)

        q = QShortcut("Ctrl+L", self)
        q.activated.connect(self.toggle_fullscreen)

        q = QShortcut("Ctrl+O", self)
        q.activated.connect(self.open_slides)

        q = QShortcut("Ctrl+Tab", self)
        q.activated.connect(self.toggle_focus)

        q = QShortcut("Ctrl+F", self)
#        q.activated.connect(self.text_edit.format_code)

        def resize():
            splitter.setSizes([int(self.width() * 0.5), int(self.width() * 0.5)])

        QTimer.singleShot(100, resize)

        self.tab_changed(0)

        for elem in self.config.get("last", []):
            self.open_slides(elem.get("filename"), elem.get("page", 0))

        if self.config.get("fullscreen", False):
            self.toggle_fullscreen()

        QTimer.singleShot(100, self.update_toolbar_position)

    def toggle_color_scheme(self):
        self.config["dark"] = not self.config.get("dark", True)
        self.apply_color_scheme(self.config["dark"])

    def apply_color_scheme(self, dark):
        if dark:
            #self.setStyleSheet("background-color: #000000; color: white")
            #self.text_edit.setStyleSheet("background-color: #000000; color: white")
#kk            self.line_number_area.setStyleSheet("background-color: #000000; color: white")
#kk            self.line_number_area.line_highlighter_color = QColor(255, 255, 255, 80)
            color = "white"
        else:
            #self.setStyleSheet("")
            #self.jupyter_widget.set_default_style()
#            self.text_edit.setStyleSheet("")
#            self.line_number_area.setStyleSheet("")
#            self.line_number_area.line_highlighter_color = QColor(0, 0, 0, 30)
            color = "black"

#kk        self.highlighter = PythonHighlighter(self.text_edit.document(), dark=dark)

        a1, a2, a3, a4 = self.text_edit_group
        a1.setIcon(QIcon(self.color(":/icons/play.svg", color)))
        a2.setIcon(QIcon(self.color(":/icons/refresh.svg", color)))
        a3.setIcon(QIcon(self.color(":/icons/download.svg", color)))
        a4.setIcon(QIcon(self.color(":/icons/hash.svg", color)))

    def color(self, icon_path, color):
        # Load the pixmap from the icon path
        pixmap = QPixmap(icon_path)

        # Create an empty QPixmap with the same size
        colored_pixmap = QPixmap(pixmap.size())
        colored_pixmap.fill(Qt.transparent)

        # Paint the new color onto the QPixmap
        painter = QPainter(colored_pixmap)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(colored_pixmap.rect(), QColor(color))
        painter.end()
        return colored_pixmap

    def color2(self, icon_path, target_color="white"):
        # Load the icon as a QImage
        image = QImage(icon_path)

        # Iterate through each pixel to recolor black pixels
        for y in range(image.height()):
            for x in range(image.width()):
                color = QColor(image.pixel(x, y))
                if color.red() == 0 and color.green() == 0 and color.blue() == 0:  # Black pixel
                    image.setPixelColor(x, y, QColor(target_color))

        # Convert back to QPixmap
        pixmap = QPixmap.fromImage(image)
        return pixmap

    def set_color(self, color):
        for i, elem in enumerate(self.color_group):
            elem.blockSignals(True)
            elem.setChecked(i == color)
            elem.blockSignals(False)
        self.tabs.currentWidget().set_color(color)

    def toggle_focus(self):
        if self.text_edit.hasFocus():
            self.jupyter_widget._control.setFocus()
        else:
            self.text_edit.setFocus()

    def set_writing_mode(self, mode):
        for i, elem in enumerate(self.group):
            elem.blockSignals(True)
            elem.setChecked(i == mode)
            elem.blockSignals(False)

        self.tabs.currentWidget().set_writing_mode(mode)

    def keyPressEvent(self, a0):
        if a0.key() == Qt.Key_F11:
            self.toggle_fullscreen()
        elif Qt.Key_F1 <= a0.key() <= Qt.Key_F10:
            idx = a0.key() - Qt.Key_F1

            if idx < self.tabs.count():
                self.tabs.setCurrentIndex(idx)

        super().keyPressEvent(a0)

    def save_as(self):
        pwd = os.getcwd()
        path = self.config.get("progs_path", str(pwd) + os.sep + "progs")
        filename, ok = QFileDialog.getSaveFileName(self, "Save code", filter="Python files (*.py)", directory=path)
        if ok:
            filename = filename.replace(".py", "") + ".py"
            with open(filename, "w") as f:
                f.write(self.text_edit.get_text())

    def update_status_bar(self, x, timeout):
        if self.config.get("show_status_bar", True):
            x = x.replace("\n", "")
            diff = self.text_edit.get_remaining_chars()
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

    def move_to(self, forward):
        self.tabs.currentWidget().move_to(forward)

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        self.update_toolbar_position()

    def update_toolbar_position(self):
        if self.tabs.currentIndex() == 0:
            return
        toolbar = self.tabs.currentWidget().get_toolbar()
        if toolbar is not None:
            toolbar.setParent(self.tabs)
            toolbar.show()

            if self.isFullScreen():
                toolbar.setGeometry(self.width() - toolbar.sizeHint().width() - 20, self.height() - 34,
                                    toolbar.sizeHint().width(),
                                    40)
            else:
                toolbar.setGeometry(self.width() - toolbar.sizeHint().width() - 20, self.height() - 56,
                                    toolbar.sizeHint().width(),
                                    40)

    def clear_all(self):
        self.jupyter_widget.clear()
        self.text_edit.clear()
        self.prog_cb.setCurrentIndex(0)

    def tab_changed(self, index):
        for i in range(1, self.tabs.count()):
            toolbar = self.tabs.widget(i).get_toolbar()
            if toolbar is not None:
                toolbar.hide()

        if index == 0:
            self.apply_color_scheme(self.config.get("dark", False))
        else:
            self.update_toolbar_position()
            self.setStyleSheet("")

    def set_touchable(self):
        self.tabs.currentWidget().set_touchable(not self.action_touchable.isChecked())

    def close_tab_requested(self, index):
        if index > 0:
            self.tabs.removeTab(index)

    def open_slides(self, filename=None, page=0):
        # open pdf file
        pwd = os.getcwd()
        path = self.config.get("slides_path", str(pwd) + os.sep + "slides")
        if filename is None:
            filename, ok = QFileDialog.getOpenFileName(self, "Open PDF file", filter="PDF files (*.pdf)",
                                                       directory=path, options=QFileDialog.Options())

        if filename:
            name = filename.split("/")[-1].replace(".pdf", "")
            if os.path.exists(filename):
                slides = Slides(self.config, filename, page)
                slides.play_code.connect(self.code_from_slide)
                self.tabs.addTab(slides, name)
                self.tabs.setCurrentWidget(slides)
                slides.view.setFocus()

    def closeEvent(self, a0):
        self.config["last"] = []
        for i in range(1, self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, Slides):
                self.config["last"].append({"filename": widget.filename, "page": widget.page})

        with open("config.yaml", "w") as f:
            yaml.dump(self.config, f)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        m1 = menu.addAction("Fullscreen")
        menu.addSeparator()
        m1.setCheckable(True)
        m1.setChecked(self.isFullScreen())
        m1.triggered.connect(self.toggle_fullscreen)

        if os.path.exists("slides"):
            m2 = menu.addMenu("Slides")

            def fill():
                pwd = os.getcwd()
                for filename in os.listdir("slides"):
                    m2.addAction(filename, lambda x=filename, y=filename: self.open_slides(pwd + "/slides/" + y))

            m2.aboutToShow.connect(fill)

        menu.addAction("Open", self.open_slides)
        menu.addSeparator()
        m3 = menu.addMenu("Mode")

        # NONE = 0
        # POINTER = 1
        # WRITING = 2
        # ERASING = 3
        # RECTANGLES = 4
        # ELLIPSES = 5

        m3.addAction("None", lambda: self.set_writing_mode(0))
        m3.addAction("Pointer", lambda: self.set_writing_mode(1))
        m3.addAction("Write", lambda: self.set_writing_mode(2))
        m3.addAction("Erase", lambda: self.set_writing_mode(3))
        m3.addAction("Rectangles", lambda: self.set_writing_mode(4))
        m3.addAction("Ellipses", lambda: self.set_writing_mode(5))

        menu.addAction("Exit", self.close)

        menu.exec_(event.globalPos())

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.menuBar().show()
        else:
            self.showFullScreen()
            self.menuBar().hide()

    def code_from_slide(self, code):
        self.text_edit.setText("")
        self.text_edit.set_code(code)
        self.text_edit.set_mode(1)
        self.tabs.setCurrentIndex(0)
        self.text_edit.setFocus()

    def load_program(self, filename):
        if filename == "Select program":
            self.clear_all()
            return

        with open(f"progs/{filename}") as f:
            #    self.text_edit.setPlainText(f.read())
            self.text_edit.set_code(f.read())
            self.jupyter_widget.clear()

    def execute_code(self):
        self.text_edit.format_code()
        self.jupyter_widget.execute(self.text_edit.get_text(), not self.keep_banner.isChecked())



if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
