import os
import sys
import time

from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter, QTextEdit, QPushButton, QVBoxLayout, QWidget, QToolBar
from PyQt5.QtCore import Qt, QRegExp, pyqtSignal, QTimer
from PyQt5.QtGui import QTextCharFormat, QColor, QFont, QSyntaxHighlighter
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.manager import QtKernelManager


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("blue"))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            "def", "class", "if", "else", "elif", "while", "for", "import", "from", "as", "return",
            "try", "except", "finally", "with", "lambda", "yield", "pass", "break", "continue", "global", "nonlocal"
        ]
        self.highlighting_rules += [(f"\\b{k}\\b", keyword_format) for k in keywords]

        string_format = QTextCharFormat()
        string_format.setForeground(QColor("magenta"))
        self.highlighting_rules.append((r'".*?"', string_format))
        self.highlighting_rules.append((r"'.*?'", string_format))

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


def create_jupyter_widget():
    kernel_manager = QtKernelManager(kernel_name='python3')
    kernel_manager.start_kernel()
    kernel_client = kernel_manager.client()
    kernel_client.start_channels()

    jupyter_widget = RichJupyterWidget()
    font = QFont("Monospace")
    font.setStyleHint(QFont.TypeWriter)
    font.setPixelSize(18)
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

    def set_code(self, code):
        self.code = code
        self.set_mode(1)

    def set_mode(self, mode):
        self.mode = mode
        self.setCursorWidth(3 if self.mode == 1 else 1)
        self.update()

    def __init__(self):
        super().__init__()
        # self.setTabStopWidth()
        # set mono font

        self.mode = 0
        font = QFont("Monospace")
        font.setStyleHint(QFont.TypeWriter)
        font.setPixelSize(18)

        self.setFont(font)
        self.code = ""
        self.count = 0

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        print(e.key())

        if e.key() == Qt.Key_Escape:
            self.set_mode(1 if self.mode == 0 else 0)
            return

        if self.mode == 1:
            if e.key() == Qt.Key_Return:
                super().keyPressEvent(e)
                self.set_mode(0)
            elif e.key() == Qt.Key_Tab:
                while self.count < len(self.code):
                    self.setText(self.toPlainText() + self.code[self.count])
                    self.moveCursor(QtGui.QTextCursor.End)
                    self.count += 1
                    if self.code[self.count - 1] == "\n":
                        break

            elif self.count < len(self.code):
                self.setText(self.toPlainText() + self.code[self.count])
                self.moveCursor(QtGui.QTextCursor.End)
                self.count += 1

            return

        def get_prev_line():
            cursor = self.textCursor()
            cursor.movePosition(QtGui.QTextCursor.StartOfLine)
            cursor.movePosition(QtGui.QTextCursor.StartOfLine)
            cursor.movePosition(QtGui.QTextCursor.PreviousBlock)
            cursor.movePosition(QtGui.QTextCursor.EndOfBlock, QtGui.QTextCursor.KeepAnchor)
            previous_line = cursor.selectedText().strip()

            return previous_line

        def get_spaces(line):
            spaces = 0
            for c in line:
                if c == " ":
                    spaces += 1
                else:
                    break
            return spaces

        def get_current_line():
            cursor = self.textCursor()
            cursor.movePosition(QtGui.QTextCursor.StartOfLine)
            cursor.movePosition(QtGui.QTextCursor.EndOfLine, QtGui.QTextCursor.KeepAnchor)
            current_line = cursor.selectedText()
            return current_line

        if e.key() == Qt.Key_Tab:
            self.insertPlainText("    ")
        elif e.key() == Qt.Key_Return:
            current_line = get_current_line()
            spaces = get_spaces(current_line)
            print(current_line, spaces)
            # check if CTrl is pressed
            if e.modifiers() == Qt.ControlModifier:
                self.ctrl_enter.emit()
            if current_line.endswith(":"):
                self.insertPlainText("\n" + " " * (spaces + 4))
            elif current_line.startswith(" "):
                if current_line.strip():
                    self.insertPlainText("\n" + " " * spaces)
                else:
                    self.insertPlainText("\n" + " " * (max(spaces - 4, 0)))
                # self.insertPlainText("\n" + " " * spaces)
            else:
                super().keyPressEvent(e)





        else:
            super().keyPressEvent(e)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PyQt App with Splitter and Code Execution")
        self.resize(1000, 600)

        splitter = QSplitter(Qt.Horizontal)

        def show_programs(menu):
            # get files in progs
            menu.clear()
            files = os.listdir("progs")
            for file in files:
                action = menu.addAction(file)
                action.triggered.connect(lambda x=file, y=file: self.load_program(y))

        m = self.menuBar()
        file = m.addMenu("File")
        progs = file.addMenu("Programs")
        file.aboutToShow.connect(lambda x=progs, y=progs: show_programs(y))

        # Left side layout
        left_widget = QWidget()
        left_layout = QVBoxLayout()

        self.text_edit = PythonEditor()
        self.text_edit.ctrl_enter.connect(self.execute_code)
        self.text_edit.setPlaceholderText("Write Python code here...")
        self.highlighter = PythonHighlighter(self.text_edit.document())

        self.run_button = QPushButton("Run Code")
        self.run_button.clicked.connect(self.execute_code)
        bar = QToolBar()
        bar.addAction("▶", self.execute_code)
        bar.addAction("+")
        bar.addAction("←")
        left_layout.addWidget(bar)
        left_layout.addWidget(self.text_edit)
        # left_layout.addWidget(self.run_button)
        left_widget.setLayout(left_layout)

        splitter.addWidget(left_widget)

        # Right side: RichJupyterWidget
        self.jupyter_widget = create_jupyter_widget()
        splitter.addWidget(self.jupyter_widget)

        splitter.setStretchFactor(0, 80)
        splitter.setStretchFactor(1, 50)

        self.setCentralWidget(splitter)
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        return False

    def load_program(self, filename):
        with open(f"progs/{filename}") as f:
        #    self.text_edit.setPlainText(f.read())
            self.text_edit.set_code(f.read())


    def execute_code(self):
        self.jupyter_widget.execute("%clear")
        QApplication.processEvents()

        def run():
            code = self.text_edit.toPlainText()
            if code.strip():
                self.jupyter_widget.execute(code, interactive=True)
        QTimer.singleShot(100, run)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
