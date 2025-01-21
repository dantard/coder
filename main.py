import os
import random
import sys
import time
# import resources # noqa
import yaml
from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter, QTextEdit, QPushButton, QVBoxLayout, QWidget, \
    QToolBar, QComboBox, QTabWidget, QMenu, QMenuBar, QFileDialog, QShortcut, QTabBar, QStatusBar, QHBoxLayout, \
    QPlainTextEdit
from PyQt5.QtCore import Qt, QRegExp, pyqtSignal, QTimer, QEvent
from PyQt5.QtGui import QTextCharFormat, QColor, QFont, QSyntaxHighlighter, QPixmap, QPainter, QCursor, QIcon
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.manager import QtKernelManager

from textract import Slides
import autopep8

from utils import create_cursor_image


class CustomTabBar(QTabBar):
    def __init__(self):
        super().__init__()
        # Customize the tab bar as needed
        self.setStyleSheet("QTabBar::tab { background: lightblue; }")
        self.a = QPushButton(self)


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("blue"))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = ['return', 'nonlocal', 'elif', 'assert', 'or', 'yield', 'finally',
                    'from', 'global', 'del', 'print', 'None', 'pass', 'class', 'as',
                    'break', 'while', 'await', 'async', 'range', 'is', 'True', 'lambda',
                    'False', 'in', 'import', 'except', 'continue', 'and', 'raise', 'with',
                    'if', 'try', 'for', 'else', 'not', 'def', 'danilo'
                    ]

        # print(set(keywords))

        self.highlighting_rules += [(f"\\b{k}\\b", keyword_format) for k in keywords]

        string_format = QTextCharFormat()
        string_format.setForeground(Qt.magenta)
        self.highlighting_rules.append((r'".*"', string_format))
        self.highlighting_rules.append((r"'.*'", string_format))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("green"))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((r"#.*", comment_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, fmt)
                index = expression.indexIn(text, index + length)


def create_jupyter_widget(font_size):
    kernel_manager = QtKernelManager(kernel_name='python3')
    kernel_manager.start_kernel()
    kernel_client = kernel_manager.client()
    kernel_client.start_channels()

    jupyter_widget = RichJupyterWidget()
    jupyter_widget.include_other_output
    font = QFont("Monospace")
    font.setStyleHint(QFont.TypeWriter)
    font.setPixelSize(font_size)
    jupyter_widget.font = font

    # jupyter_widget._set_font()
    jupyter_widget.kernel_manager = kernel_manager
    jupyter_widget.kernel_client = kernel_client

    # Customize the prompt
    jupyter_widget.include_other_output = False
    jupyter_widget.banner = ""  # Remove banner
    jupyter_widget.input_prompt = ""  # Remove input prompt
    jupyter_widget.output_prompt = ""  # Remove output prompt

    return jupyter_widget


class PythonEditor(QTextEdit):
    ctrl_enter = pyqtSignal()
    info = pyqtSignal(str, int)

    def set_code(self, code):
        self.code = code
        self.set_mode(1)

    def set_mode(self, mode):
        self.mode = mode
        self.setCursorWidth(3 if self.mode == 1 else 1)
        # self.setReadOnly(self.mode == 1)
        self.update()

    def __init__(self, font_size=18):
        super().__init__()
        # self.setTabStopWidth()
        # set mono font

        self.mode = 0
        font = QFont("Monospace")
        font.setStyleHint(QFont.TypeWriter)
        font.setPixelSize(font_size)

        self.setFont(font)
        self.code = ""
        self.count = 0

    def format_code(self):
        self.setPlainText(autopep8.fix_code(self.toPlainText()))
        self.moveCursor(QtGui.QTextCursor.End)

    def complete_line(self, sleep=True):
        self.info.emit(self.get_next_line(), 0)
        while self.count < len(self.code):
            # self.setText(self.toPlainText() + self.code[self.count])
            self.insertPlainText(self.code[self.count])
            self.moveCursor(QtGui.QTextCursor.End)
            self.count += 1
            if self.code[self.count - 1] == "\n":
                # if next line is empty continue
                # and show that line too
                if len(self.get_rest_of_line()) > 0:
                    return True

            if sleep:
                QApplication.processEvents()
                time.sleep(0.01 + random.random() * 0.1)
        return False

    def get_rest_of_line(self):
        count = self.count
        text = ""
        while count < len(self.code):
            text += self.code[count]
            count += 1
            if self.code[count - 1] == "\n":
                return text[1:]
        return ""

    def get_spaces(self, line):
        spaces = 0
        for c in line:
            if c == " ":
                spaces += 1
            else:
                break
        return spaces

    def get_current_line(self):
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.StartOfLine)
        cursor.movePosition(QtGui.QTextCursor.EndOfLine, QtGui.QTextCursor.KeepAnchor)
        current_line = cursor.selectedText()
        return current_line

    def append_next_char(self):
        # self.insertPlainText(self.code[self.count])
        # TODO: once filtered ñ use insertPlainText
        self.setText(self.code[:self.count])
        self.moveCursor(QtGui.QTextCursor.End)
        self.count += 1

    def show_all_code(self):
        # is control pressed? check
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            while self.complete_line(False):
                pass
            self.set_mode(0)
        else:
            self.setText(autopep8.fix_code(self.code))
            self.set_mode(0)

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        self.setFocusPolicy(Qt.StrongFocus)

        if e.key() == Qt.Key_Escape:
            self.set_mode(1 if self.mode == 0 else 0)

            return

        if self.mode == 1:
            if e.key() == Qt.Key_Down:
                self.show_all_code()
            elif e.text() == "º":
                self.complete_line(True)
            elif e.key() == Qt.Key_Control:
                return
            elif e.key() == Qt.Key_End:
                while self.complete_line(False):
                    pass
                self.set_mode(0)

            # elif e.key() == Qt.Key_Return:
            # super().keyPressEvent(e)
            # self.set_mode(0)
            #    pass
            elif e.key() == Qt.Key_Tab:
                if e.modifiers() == Qt.ControlModifier:
                    while self.complete_line():
                        pass
                    self.set_mode(0)
                else:
                    self.complete_line()
            elif self.count < len(self.code):
                self.info.emit(self.get_rest_of_line(), 1000)
                self.append_next_char()
            elif e.key() == Qt.Key_Return:
                self.set_mode(0)
                super().keyPressEvent(e)
            elif e.key() == Qt.Key_Backspace:
                self.set_mode(0)
            else:
                self.setText(self.toPlainText() + "\n")
                self.moveCursor(QtGui.QTextCursor.End)

        elif self.mode == 0:

            if e.key() == Qt.Key_Tab:
                self.insertPlainText("    ")
            elif e.key() == Qt.Key_Return:
                current_line = self.get_current_line()
                spaces = self.get_spaces(current_line)
                if e.modifiers() == Qt.ControlModifier:
                    self.ctrl_enter.emit()
                elif current_line.endswith(":"):
                    # is the cursor at the end of the line?
                    # print(self.textCursor().positionInBlock(), len(current_line))
                    if self.textCursor().positionInBlock() == len(current_line):
                        self.insertPlainText("\n" + " " * (spaces + 4))
                    else:
                        super().keyPressEvent(e)
                elif current_line.startswith(" "):
                    if current_line.strip():
                        self.insertPlainText("\n" + " " * spaces)
                    else:
                        self.insertPlainText("\n" + " " * (max(spaces - 4, 0)))
                else:
                    super().keyPressEvent(e)
            else:
                super().keyPressEvent(e)

    def get_next_line(self):
        count = self.count
        remaining = self.code[count:]
        remaining = remaining.split("\n")
        remaining = remaining[1:]
        remaining = [x for x in remaining if x.strip()]
        # print(remaining)
        if remaining:
            return remaining[0]


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

        self.setWindowTitle("Fancy Slides")

        self.resize(1000, 600)

        self.tabs = QTabWidget()

        # put tabs bottom
        self.tabs.setTabPosition(QTabWidget.South)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab_requested)
        self.tabs.currentChanged.connect(self.tab_changed)
        tab_bar = self.tabs.tabBar()

        self.toolbar = QToolBar(self.tabs)
        self.toolbar.setMaximumHeight(35)
        self.toolbar.show()

        none = self.toolbar.addAction("", lambda: self.set_writing_mode(0))
        none.setIcon(QIcon(":/icons/cursor.svg"))
        none.setCheckable(True)
        none.setChecked(True)

        pointer = self.toolbar.addAction("Pointer", lambda: self.set_writing_mode(1))
        pointer.setIcon(QIcon(":/icons/origin.svg"))
        pointer.setCheckable(True)

        write = self.toolbar.addAction("", lambda: self.set_writing_mode(2))
        write.setIcon(QIcon(":/icons/edit.svg"))
        write.setCheckable(True)

        erase = self.toolbar.addAction("", lambda: self.set_writing_mode(3))
        erase.setIcon(QIcon(":/icons/delete.svg"))
        erase.setCheckable(True)

        erase_all = self.toolbar.addAction("", lambda: self.tabs.currentWidget().erase_all())
        erase_all.setIcon(QIcon("icons/bin.svg"))

        self.group = [none, pointer, write, erase]

        self.toolbar.addSeparator()
        black = self.toolbar.addAction("", lambda: self.set_color(0))
        black.setIcon(QIcon(":/icons/black.svg"))
        red = self.toolbar.addAction("", lambda: self.set_color(1))
        red.setIcon(QIcon(":/icons/red.svg"))
        green = self.toolbar.addAction("", lambda: self.set_color(2))
        green.setIcon(QIcon(":/icons/green.svg"))
        blue = self.toolbar.addAction("", lambda: self.set_color(3))
        blue.setIcon(QIcon(":/icons/blue.svg"))

        self.color_group = [black, red, green, blue]
        for elem in self.color_group:
            elem.setCheckable(True)
        black.setChecked(True)

        self.toolbar.addSeparator()

        prev = self.toolbar.addAction("✕", lambda: self.move_to(False))
        prev.setIcon(QIcon(":/icons/arrow-left.svg"))
        # set color black and alhpa 0.5
        # self.toolbar.setStyleSheet("background-color:  rgba(0, 0, 0, 0.1);")
        self.toolbar.setMovable(True)
        self.toolbar.setFloatable(True)
        self.tabs.setStyleSheet("QTabBar::tab { height: 35px; }");

        self.action_touchable = self.toolbar.addAction("Pointer", self.set_touchable)
        self.action_touchable.setCheckable(True)
        self.action_touchable.setIcon(QIcon(":/icons/pan.svg"))

        next1 = self.toolbar.addAction("⬇", lambda: self.move_to(True))
        next1.setIcon(QIcon(":/icons/arrow-right.svg"))

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

        self.text_edit = PythonEditor(self.font_size)
        self.text_edit.ctrl_enter.connect(self.execute_code)
        self.text_edit.info.connect(self.update_status_bar)
        self.text_edit.setPlaceholderText("Write Python code here...")

        self.line_number_area = PythonEditor(self.font_size)
        self.line_number_area.setStyleSheet("QTextEdit { color: #a0a0a0;}")
        self.line_number_area.setContentsMargins(0, 0, 0, 0)
        self.text_edit.setContentsMargins(0, 0, 0, 0)
        self.highlighter = PythonHighlighter(self.text_edit.document())

        bar = QToolBar()
        bar.addAction("▶", self.execute_code)
        bar.addAction("✕", self.clear_all)
        bar.addAction("⬇", self.text_edit.show_all_code)

        self.keep_banner = bar.addAction("")
        self.keep_banner.setCheckable(True)
        self.keep_banner.setChecked(False)

        left_layout.addWidget(bar)
        left_layout.addWidget(self.prog_cb)

        lay = QHBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # left_layout.addWidget(self.text_edit)
        self.line_number_area.setReadOnly(True)
        self.line_number_area.setMaximumWidth(50)
        lay.addWidget(self.line_number_area)
        lay.addWidget(self.text_edit)
        self.text_edit.setLineWrapMode(QTextEdit.NoWrap)

        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.line_number_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.line_number_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        def text_changed():
            text = self.text_edit.toPlainText()
            lines = text.split("\n")
            cursor_pos = self.text_edit.textCursor().position()
            v1 = self.line_number_area.verticalScrollBar().value()
            self.line_number_area.blockSignals(True)
            self.line_number_area.clear()
            text = ""

            for i in range(len(lines) + 1):
                # self.line_number_area.append("{:3d}".format(i + 1))
                text += "{:3d}\n".format(i + 1)
            self.line_number_area.setPlainText(text)

            # self.text_edit.setTextCursor(self.text_edit.textCursor())
            self.line_number_area.verticalScrollBar().setValue(v1)
            self.line_number_area.blockSignals(False)

        self.text_edit.textChanged.connect(text_changed)
        self.text_edit.verticalScrollBar().valueChanged.connect(self.line_number_area.verticalScrollBar().setValue)
        self.text_edit.horizontalScrollBar().rangeChanged.connect(text_changed)
        self.line_number_area.verticalScrollBar().valueChanged.connect(self.text_edit.verticalScrollBar().setValue)

        left_layout.addLayout(lay)

        self.sb = QStatusBar()
        left_layout.addWidget(self.sb)

        # left_layout.addWidget(self.run_button)
        left_widget.setLayout(left_layout)

        splitter.addWidget(left_widget)

        # Right side: RichJupyterWidget
        self.jupyter_widget = create_jupyter_widget(self.font_size)
        splitter.addWidget(self.jupyter_widget)

        self.tabs.addTab(splitter, "Code Execution")
        tab_bar.setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        self.setCentralWidget(self.tabs)

        file = self.menuBar()
        file = file.addMenu("File")
        file.addAction("Open", self.open_slides)
        m1 = file.addMenu("Slides")
        file.addSeparator()
        file.addAction("Save As", self.save_as)
        file.addAction("Exit", self.close)

        def fill():
            m1.clear()
            pwd = os.getcwd()
            for filename in os.listdir("slides"):
                m1.addAction(filename, lambda x=filename, y=filename: self.open_slides(pwd + "/slides/" + y))

        m1.aboutToShow.connect(fill)

        q = QShortcut("Ctrl+S", self)
        q.activated.connect(self.save_as)

        q = QShortcut("Ctrl+L", self)
        q.activated.connect(self.toggle_fullscreen)

        q = QShortcut("Ctrl+O", self)
        q.activated.connect(self.open_slides)

        q = QShortcut("Ctrl+Tab", self)
        q.activated.connect(self.toggle_focus)

        q = QShortcut("Ctrl+F", self)
        q.activated.connect(self.text_edit.format_code)

        def resize():
            splitter.setSizes([int(self.width() * 0.5), int(self.width() * 0.5)])

        QTimer.singleShot(100, resize)

        for elem in self.config.get("last", []):
            self.open_slides(elem.get("filename"), elem.get("page", 0))

        if self.config.get("fullscreen", False):
            self.toggle_fullscreen()

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
        filename, ok = QFileDialog.getSaveFileName(self, "Save code", filter="Python files (*.py)", directory="progs")
        if ok:
            filename = filename.replace(".py", "") + ".py"
            with open(filename, "w") as f:
                f.write(self.text_edit.toPlainText())

    def update_status_bar(self, x, timeout):
        if self.config.get("show_status_bar", True):
            x = x.replace("\n", "")
            diff = len(self.text_edit.code) - self.text_edit.count

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
        if self.isFullScreen():
            self.toolbar.setGeometry(self.width() - self.toolbar.width() - 20, self.height() - 34, self.toolbar.width(),
                                     40)
        else:
            self.toolbar.setGeometry(self.width() - self.toolbar.width() - 20, self.height() - 56, self.toolbar.width(),
                                     40)

    def clear_all(self):
        self.jupyter_widget.execute("%clear")
        self.text_edit.clear()
        self.prog_cb.setCurrentIndex(0)
        self.text_edit.set_code("")
        self.text_edit.count = 0
        self.text_edit.set_mode(0)

    def tab_changed(self, index):
        if index == 0:
            self.text_edit.setFocus()
            self.toolbar.hide()
        else:
            #            self.tabs.currentWidget().image_label.setFocus()
            self.toolbar.show()
            self.action_touchable.blockSignals(True)
            self.action_touchable.setChecked(not self.tabs.currentWidget().touchable)
            self.action_touchable.blockSignals(False)

    def set_touchable(self):
        self.tabs.currentWidget().set_touchable(not self.action_touchable.isChecked())

    def close_tab_requested(self, index):
        if index > 0:
            self.tabs.removeTab(index)

    def open_slides(self, filename=None, page=0):
        # open pdf file
        if filename is None:
            filename, ok = QFileDialog.getOpenFileName(self, "Open PDF file", filter="PDF files (*.pdf)",
                                                       directory="slides")

        if filename:
            name = filename.split("/")[-1].replace(".pdf", "")
            if os.path.exists(filename):
                slides = Slides(filename, page)
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
        m3.addAction("None", lambda: self.set_writing_mode(0))
        m3.addAction("Write", lambda: self.set_writing_mode(1))
        m3.addAction("Erase", lambda: self.set_writing_mode(2))
        m3.addAction("Rectangles", lambda: self.set_writing_mode(3))
        m3.addAction("Ellipses", lambda: self.set_writing_mode(4))

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
        self.text_edit.set_code(code)
        self.text_edit.set_mode(1)
        self.tabs.setCurrentIndex(0)

    def load_program(self, filename):
        if filename == "Select program":
            self.clear_all()
            return

        with open(f"progs/{filename}") as f:
            #    self.text_edit.setPlainText(f.read())
            self.text_edit.set_code(f.read())
            self.text_edit.count = 0
            self.text_edit.clear()
            self.text_edit.setFocus()
            self.jupyter_widget.execute("%clear")

    def execute_code(self):
        self.text_edit.format_code()
        self.jupyter_widget.execute("%clear")
        self.jupyter_widget.do_execute(self.text_edit.toPlainText(), True, False)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
