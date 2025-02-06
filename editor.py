import random
import re
import time

import autopep8
from PyQt5 import QtGui
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor, QFont, QSyntaxHighlighter, QPainter, QFontMetrics
from PyQt5.QtWidgets import QTextEdit, QApplication, QWidget, QHBoxLayout, QScrollBar


class HighlightableTextEdit(QTextEdit):
    def __init__(self):
        super().__init__()
        self.line_highlighter_color = QColor(255, 255, 255, 100)

    def highlight_line(self, line_number):
        cursor = self.textCursor()
        position = cursor.position()
        cursor.movePosition(QTextCursor.Start)

        # Select all text and reset formatting
        cursor.select(QTextCursor.Document)
        default_format = QTextCharFormat()  # Default format (no highlights)
        cursor.setCharFormat(default_format)

        cursor.movePosition(QTextCursor.Start)
        for _ in range(line_number):
            cursor.movePosition(QTextCursor.Down)

        cursor.select(QTextCursor.LineUnderCursor)

        highlight_format = QTextCharFormat()
        highlight_format.setBackground(self.line_highlighter_color)
        cursor.setCharFormat(highlight_format)
        cursor.setPosition(position)

    def set_line_highlighter_color(self, color):
        self.line_highlighter_color = color
        self.update()

class MagicEditor(QTextEdit):
    ctrl_enter = pyqtSignal()
    info = pyqtSignal(str, int)

    def __init__(self, highlighter=None, font_size=18):
        super().__init__()
        self.highlighter = highlighter
        self.highlighter.setDocument(self.document())
        self.choosing = None
        self.candidates = []
        self.mode = 0
        self.code = ""
        self.count = 0

    def set_dark_mode(self, dark):
        self.highlighter.set_dark_mode(dark)
        self.highlighter.setDocument(self.document())

    def set_code(self, code):
        self.code = code
        self.set_mode(1)

    def set_mode(self, mode):
        self.mode = mode
        self.setCursorWidth(3 if self.mode == 1 else 1)
        # self.setReadOnly(self.mode == 1)
        self.update()

    def format_code(self):
        pass

    def on_return_key(self, e):
        return False

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
            self.setText(self.code)
            self.set_mode(0)
        self.moveCursor(QtGui.QTextCursor.End)

    def get_current_line_text(self):
        # Get the QTextCursor
        cursor = self.textCursor()

        # Move the cursor to the start and end of the current line
        cursor.select(cursor.LineUnderCursor)

        # Get the selected text
        return cursor.selectedText()

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
                self.autocomplete()
                # self.setText(self.toPlainText() + "    ")
                # self.moveCursor(QtGui.QTextCursor.End)

            elif e.key() == Qt.Key_Return:
                self.choosing = None
                if e.modifiers() == Qt.ControlModifier:
                    self.ctrl_enter.emit()
                elif self.on_return_key(e):
                    pass
                else:
                    super().keyPressEvent(e)
            else:
                self.choosing = None
                self.candidates.clear()
                super().keyPressEvent(e)
        self.cursorPositionChanged.emit()

    def autocomplete(self):

        current_line = self.get_current_line_text()
        print("current line*" + current_line + "*", len(current_line))

        if len(current_line) == 0 or current_line.endswith("    "):
            #self.setText(self.toPlainText() + "    ")
            self.insertPlainText("    ")
            self.choosing = None
            #self.moveCursor(QtGui.QTextCursor.End)
            return

        if len(current_line) > 0 and current_line[-1] in " (:)":
            self.choosing = None
            return

        if self.choosing is not None:
            self.candidates.append(self.candidates.pop(0))
            self.setText(self.toPlainText()[:-len(self.choosing)] + self.candidates[0])
            self.moveCursor(QtGui.QTextCursor.End)
            self.choosing = self.candidates[0]
            return

        words = re.split(r'\W+', self.toPlainText())

        if len(words) == 0:
            return

        last_word = words.pop(-1)

        if last_word == "":
            return

        keywords = list(set(self.highlighter.get_keywords() + words))
        # I want the last word to be the last one
        # because otherwise could pop up at the
        # beginning, and it would be annoying

        keywords.append(last_word)
        if "" in keywords:
            keywords.remove("")

        print(keywords)

        self.candidates.clear()
        for keyword in keywords:
            if keyword.startswith(last_word):
                self.candidates.append(keyword)
        if len(self.candidates) == 1:
            self.setText(self.toPlainText()[:-len(last_word)] + self.candidates[0])
            self.moveCursor(QtGui.QTextCursor.End)
        elif len(self.candidates) > 1:
            self.choosing = self.candidates[0]
            self.setText(self.toPlainText()[:-len(last_word)] + self.candidates[0])
            self.moveCursor(QtGui.QTextCursor.End)

    def get_next_line(self):
        count = self.count
        remaining = self.code[count:]
        remaining = remaining.split("\n")
        remaining = remaining[1:]
        remaining = [x for x in remaining if x.strip()]
        # print(remaining)
        if remaining:
            return remaining[0]

class PascalEditor(MagicEditor):
    pass

class PythonEditor(MagicEditor):
    def format_code(self):
        code = self.toPlainText()
        if not code.endswith("\n"):
            code += "\n"
        self.setPlainText(autopep8.fix_code(code))
        self.moveCursor(QtGui.QTextCursor.End)

    def on_return_key(self, e):
        current_line = self.get_current_line()
        spaces = self.get_spaces(current_line)
        if current_line.endswith(":"):
            # is the cursor at the end of the line?
            # print(self.textCursor().positionInBlock(), len(current_line))
            if self.textCursor().positionInBlock() == len(current_line):
                self.insertPlainText("\n" + " " * (spaces + 4))
            else:
                super().keyPressEvent(e)
            return True
        elif current_line.startswith(" "):
            if current_line.strip():
                self.insertPlainText("\n" + " " * spaces)
            else:
                self.insertPlainText("\n" + " " * (max(spaces - 4, 0)))
            return True
        return False

class KK(QScrollBar):
    def paintEvent(self, a0) -> None:
        super().paintEvent(a0)
        if self.maximum() == 0:
            p = QPainter(self)
            p.fillRect(self.rect(), self.parent().palette().base().color())


class LanguageEditor(QWidget):
    ctrl_enter = pyqtSignal()
    info = pyqtSignal(str, int)

    def __init__(self, editor, font_size=18):
        super().__init__()
        self.text_edit = editor
        self.line_number_area = HighlightableTextEdit()
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.line_number_area)
        self.layout().addWidget(self.text_edit)
        self.layout().setSpacing(0)
        self.line_number_area.setReadOnly(True)
        self.text_edit.setLineWrapMode(QTextEdit.NoWrap)
        self.line_number_area.setLineWrapMode(QTextEdit.NoWrap)

        self.text_edit: QTextEdit
        self.text_edit.setHorizontalScrollBar(KK())
        self.line_number_area.setHorizontalScrollBar(KK())

        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.line_number_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.line_number_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.text_edit.textChanged.connect(self.text_changed)
        self.text_edit.verticalScrollBar().valueChanged.connect(self.line_number_area.verticalScrollBar().setValue)
        self.text_edit.horizontalScrollBar().rangeChanged.connect(self.text_changed)
        self.line_number_area.verticalScrollBar().valueChanged.connect(self.text_edit.verticalScrollBar().setValue)

        self.text_edit.ctrl_enter.connect(self.ctrl_enter.emit)
        self.text_edit.info.connect(self.info.emit)
        # self.text_edit.info.connect(self.update_status_bar)
        self.text_edit.setPlaceholderText("Write Python code here...")
        # self.line_number_area.setStyleSheet("QTextEdit { color: #a0a0a0;}")
        self.line_number_area.setContentsMargins(0, 0, 0, 0)
        self.text_edit.setContentsMargins(0, 0, 0, 0)
        self.text_edit.document().setDocumentMargin(5)
        self.line_number_area.document().setDocumentMargin(5)

        self.text_edit.cursorPositionChanged.connect(
            lambda: self.line_number_area.highlight_line(self.text_edit.textCursor().blockNumber()))

        self.set_font_size(font_size)

    def set_font_size(self, font_size):
        font = QFont("Monospace")
        font.setStyleHint(QFont.TypeWriter)
        font.setPixelSize(font_size)
        self.text_edit.setFont(font)
        self.line_number_area.setFont(font)
        three_numbers_width = QFontMetrics(font).width("000")
        self.line_number_area.setMaximumWidth(int(three_numbers_width+12))

    def show_code(self):
        self.text_edit.show_all_code()
    def set_dark_mode(self, dark):
        self.text_edit.set_dark_mode(dark)
        self.line_number_area.set_line_highlighter_color(QColor(0,0,0,50) if not dark else QColor(255,255,255,100))

    def set_text(self, text):
        self.text_edit.setPlainText(text)
        self.text_changed()

    def text_changed(self):
        text = self.text_edit.toPlainText()
        lines = text.split("\n")
        cursor_pos = self.text_edit.textCursor().position()
        v1 = self.line_number_area.verticalScrollBar().value()
        self.line_number_area.blockSignals(True)
        self.line_number_area.clear()
        text = ""

        for i in range(len(lines)):  # TODO: was +`11 (maybe for when the editor is full)
            # self.line_number_area.append("{:3d}".format(i + 1))
            text += "{:3d}\n".format(i + 1)
        self.line_number_area.setPlainText(text)

        # self.text_edit.setTextCursor(self.text_edit.textCursor())
        self.line_number_area.verticalScrollBar().setValue(v1)
        self.line_number_area.blockSignals(False)

        print(self.text_edit.horizontalScrollBar().maximum(), self.text_edit.horizontalScrollBar().value())

    def format_code(self):
        self.text_edit.format_code()

    def get_text(self):
        return self.text_edit.toPlainText()

    def set_code(self, code):
        self.text_edit.set_code(code)
        self.text_edit.count = 0
        self.text_edit.clear()
        self.text_edit.setFocus()

    def clear(self):
        self.text_edit.set_code("")
        self.text_edit.setPlainText("")
        self.text_edit.count = 0
        self.text_edit.set_mode(0)

    def set_mode(self, mode):
        self.text_edit.set_mode(mode)

    def get_remaining_chars(self):
        diff = len(self.get_text()) - self.text_edit.count
        return diff