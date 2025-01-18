import os
import random
import sys
import time

import yaml
from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter, QTextEdit, QPushButton, QVBoxLayout, QWidget, \
    QToolBar, QComboBox, QTabWidget, QMenu, QMenuBar, QFileDialog, QShortcut, QTabBar, QStatusBar
from PyQt5.QtCore import Qt, QRegExp, pyqtSignal, QTimer, QEvent
from PyQt5.QtGui import QTextCharFormat, QColor, QFont, QSyntaxHighlighter, QPixmap, QPainter, QCursor, QIcon
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.manager import QtKernelManager

from textract import Slides
import autopep8

from utils import create_cursor_image


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


        print(set(keywords))

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

    #jupyter_widget._set_font()
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

    def complete_line(self, sleep=True):
        print("hhhhh")
        self.info.emit(self.get_next_line(), 0)
        while self.count < len(self.code):
            QApplication.processEvents()
            #self.setText(self.toPlainText() + self.code[self.count])
            self.insertPlainText(self.code[self.count])
            self.moveCursor(QtGui.QTextCursor.End)
            self.count += 1
            if self.code[self.count-1] == "\n":
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
            text+= self.code[count]
            count += 1
            if self.code[count-1] == "\n":
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

        if e.key() == Qt.Key_Escape:
            self.set_mode(1 if self.mode == 0 else 0)

            return

        if self.mode == 1:

            if e.key() == Qt.Key_Control:
                return
            if e.key() == Qt.Key_End:
                while self.complete_line(False):
                    pass
                self.set_mode(0)

            #elif e.key() == Qt.Key_Return:
                #super().keyPressEvent(e)
                #self.set_mode(0)
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
                self.setText(self.toPlainText() +"\n")
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
                    print(self.textCursor().positionInBlock(), len(current_line))
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
        print(remaining)
        if remaining:
            return remaining[0]

class DynamicComboBox(QComboBox):
    def __init__(self, dir,  parent=None):
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
        prev = self.toolbar.addAction("✕", lambda : self.move_to(False))
        prev.setIcon(self.style().standardIcon(QApplication.style().SP_ArrowBack))

        pointer = self.toolbar.addAction("Pointer", self.set_pointer)
        pointer.setIcon(QIcon(create_cursor_image(25)))

        self.action_touchable = self.toolbar.addAction("Pointer", self.set_touchable)
        self.action_touchable.setCheckable(True)
        self.action_touchable.setIcon(self.style().standardIcon(QApplication.style().SP_BrowserStop))



        next1 = self.toolbar.addAction("⬇", lambda : self.move_to(True))
        next1.setIcon(self.style().standardIcon(QApplication.style().SP_ArrowForward))

        self.toolbar.show()


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
        self.text_edit.installEventFilter(self)

        self.highlighter = PythonHighlighter(self.text_edit.document())

        bar = QToolBar()
        bar.addAction("▶", self.execute_code)
        bar.addAction("✕", self.clear_all)
        bar.addAction("⬇", self.text_edit.show_all_code)

        self.keep_banner = bar.addAction("#")
        self.keep_banner.setCheckable(True)
        self.keep_banner.setChecked(False)

        left_layout.addWidget(bar)
        left_layout.addWidget(self.prog_cb)
        left_layout.addWidget(self.text_edit)

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
        q.activated.connect(lambda: self.tabs.setCurrentIndex((self.tabs.currentIndex() + 1)% self.tabs.count()))

        q = QShortcut("F1", self)
        q.activated.connect(lambda: self.text_edit.setFocus())

        q = QShortcut("F2", self)
        q.activated.connect(lambda: self.jupyter_widget._control.setFocus())

        def resize():
            splitter.setSizes([int(self.width() * 0.5), int(self.width() * 0.5)])
        QTimer.singleShot(100, resize)

        for elem in self.config.get("last", []):
            self.open_slides(elem.get("filename"), elem.get("page", 0))

        if self.config.get("fullscreen", False):
            self.toggle_fullscreen()

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

    def set_pointer(self):
        self.tabs.currentWidget().toggle_cursor()

    def move_to(self, forward):
        self.tabs.currentWidget().move_to(forward)

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        self.toolbar.setGeometry(self.tabs.width() - self.toolbar_pose, self.tabs.height() - 35, 150, 40)

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
            self.tabs.currentWidget().image_label.setFocus()
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
            filename, ok = QFileDialog.getOpenFileName(self, "Open PDF file", filter="PDF files (*.pdf)", directory="slides")

        if filename:
            name = filename.split("/")[-1]
            slides = Slides(filename, page)
            slides.play_code.connect(self.code_from_slide)
            self.tabs.addTab(slides, name.replace(".pdf", ""))
            self.tabs.setCurrentWidget(slides)
            slides.image_label.setFocus()


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
        m2 = menu.addMenu("Slides")
        def fill():
            pwd = os.getcwd()
            for filename in os.listdir("slides"):
                m2.addAction(filename, lambda x=filename, y=filename: self.open_slides(pwd + "/slides/" + y))

        m2.aboutToShow.connect(fill)
        menu.addAction("Open", self.open_slides)
        menu.addSeparator()
        menu.addAction("Exit", self.close)

        menu.exec_(event.globalPos())

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.menuBar().show()
        else:
            self.showFullScreen()
            self.menuBar().hide()


    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress:  # Check if the event is a key press
            if event.text() == "ñ":
                print(f"Key pressed2: {event.text()}")
                return True
            else:
                print(f"Key pressed: {event.text()}")
        return super().eventFilter(source, event)


    def code_from_slide(self, code):
        self.text_edit.setText(autopep8.fix_code(code))
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
        self.jupyter_widget._control.setText("")
        self.jupyter_widget._control.setFocus()
        QApplication.processEvents()

        def run():
            code = self.text_edit.toPlainText()
            if code.strip():
                self.jupyter_widget.execute(code, interactive=True)
                if not self.keep_banner.isChecked():
                    self.jupyter_widget._control.clear()


        QTimer.singleShot(100, run)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
