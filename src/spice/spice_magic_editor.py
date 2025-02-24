import random
import re

import autopep8
from PyQt5 import QtGui
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont, QFontMetrics, QColor, QPainter
from PyQt5.QtWidgets import QTextEdit, QHBoxLayout, QScrollBar, QApplication

from spice.line_number_text_edit import LineNumberTextEdit
from spice.magic_scrollbar import MagicScrollBar


class SpiceMagicEditor(QTextEdit):
    ctrl_enter = pyqtSignal()
    info = pyqtSignal(str, int, int)

    def __init__(self, highlighter=None, font_size=18):
        super().__init__()
        self.highlighter = highlighter
        self.suggestion = None
        self.candidates = []
        self.count = 0
        self.mode = 0
        self.code = ""
        self.delay = 0.01
        self.autocomplete_words = []

        self.line_number_area = LineNumberTextEdit(self)
        self.line_number_area.verticalScrollBar().valueChanged.connect(self.verticalScrollBar().setValue)
        self.line_number_area.document().setDocumentMargin(0)

        self.setContentsMargins(0, 0, 0, 0)
        self.document().setDocumentMargin(0)
        self.setViewportMargins(60, 0, 0, 0)
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.setPlaceholderText("Write Python code here...")

        self.setHorizontalScrollBar(MagicScrollBar())
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.textChanged.connect(self.text_changed)
        self.verticalScrollBar().valueChanged.connect(self.line_number_area.verticalScrollBar().setValue)
        self.horizontalScrollBar().rangeChanged.connect(self.text_changed)

        self.cursorPositionChanged.connect(
            lambda: self.line_number_area.highlight_line(self.textCursor().blockNumber()))

        if self.highlighter:
            self.highlighter.setDocument(self.document())

        self.set_font_size(font_size)

    def set_font_size(self, font_size):
        font = QFont("Monospace")
        font.setStyleHint(QFont.TypeWriter)
        font.setPixelSize(font_size)
        self.setFont(font)
        self.line_number_area.setFont(font)
        three_numbers_width = QFontMetrics(font).width("000")
        self.line_number_area.setFixedWidth(int(three_numbers_width + 12))
        self.setViewportMargins(three_numbers_width + 15, 0, 0, 0)

    def show_code(self):
        self.show_all_code()

    def set_dark_mode(self, dark):
        self.line_number_area.set_dark_mode(dark)
        self.highlighter.set_dark_mode(dark)
        self.highlighter.setDocument(self.document())

    def set_text(self, text):
        self.setPlainText(text)
        self.text_changed()

    def text_changed(self):
        text = self.toPlainText()
        lines = text.split("\n")
        v1 = self.line_number_area.verticalScrollBar().value()
        self.line_number_area.blockSignals(True)
        self.line_number_area.clear()
        text = str()
        for i in range(len(lines)):
            text += "{:3d}\n".format(i + 1)

        self.line_number_area.setPlainText(text)
        self.line_number_area.setFixedHeight(self.height())
        self.line_number_area.verticalScrollBar().setMaximum(self.verticalScrollBar().maximum())
        self.line_number_area.verticalScrollBar().setValue(v1)
        self.line_number_area.blockSignals(False)

    def resizeEvent(self, a0) -> None:
        self.text_changed()
        self.blockSignals(True)
        super().resizeEvent(a0)
        self.blockSignals(False)

    def format_code(self):
        self.format_code()

    def get_text(self):
        return self.toPlainText()

    def clear(self):
        self.set_code("")
        self.setPlainText("")
        self.count = 0
        self.set_mode(0)

    def get_code(self):
        return self.code

    def get_remaining_chars(self):
        diff = len(self.get_code()) - self.count
        return diff

    def set_delay(self, delay):
        self.delay = delay

    def append_autocomplete(self, words, clear=False):
        if clear:
            self.autocomplete_words.clear()
        self.autocomplete_words += words if words else ""

    def set_code(self, code):
        self.setText("")
        self.count = 0
        self.code = code
        self.set_mode(1)
        self.setFocus()

    def set_mode(self, mode):
        self.mode = mode
        self.setCursorWidth(3 if self.mode == 1 else 1)
        # self.setReadOnly(self.mode == 1)
        self.update()

    def on_return_key(self, e):
        return False

    def complete_line(self, sleep=True):
        self.info.emit(self.get_next_line(), self.get_remaining_chars(), 20)
        if self.count < len(self.code):
            # self.setText(self.toPlainText() + self.code[self.count])
            self.insertPlainText(self.code[self.count])
            self.moveCursor(QtGui.QTextCursor.End)
            self.count += 1

            if self.code[self.count - 1] == "\n":
                # if next line is empty continue
                # and show that line too
                if len(self.get_rest_of_line()) > 0:
                    return True

            QApplication.processEvents()
            delay = int(self.delay) + random.randint(0, int(self.delay))
            QTimer.singleShot(delay, self.complete_line)

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
        self.count += 1
        self.setText(self.code[:self.count])
        self.moveCursor(QtGui.QTextCursor.End)

    def show_all_code(self):
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
            self.set_mode(0 if self.mode == 1 else 0)

        if self.mode == 1:
            print("mode1")
            if e.key() == Qt.Key_Down:
                self.show_all_code()
            elif e.key() == Qt.Key_Control:
                return
            elif e.key() == Qt.Key_End:
                while self.complete_line(False):
                    pass
                self.set_mode(0)
            elif e.key() == Qt.Key_Tab:
                if e.modifiers() == Qt.ControlModifier:
                    while self.complete_line():
                        pass
                    self.set_mode(0)
                else:
                    self.complete_line()
            elif self.count < len(self.code):
                self.info.emit(self.get_rest_of_line(), self.get_remaining_chars(), 1000)
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
                self.tab_pressed()
            elif e.key() == Qt.Key_Backspace:
                self.suggestion = None
                if self.get_current_line_text().endswith("    "):
                    for i in range(4):
                        self.textCursor().deletePreviousChar()
                else:
                    super().keyPressEvent(e)
            elif e.key() == Qt.Key_Return:
                self.suggestion = None
                if e.modifiers() == Qt.ControlModifier:
                    self.ctrl_enter.emit()
                elif self.on_return_key(e):
                    pass
                else:
                    super().keyPressEvent(e)
            else:
                self.suggestion = None
                super().keyPressEvent(e)
        self.cursorPositionChanged.emit()

    def tab_pressed(self):

        current_line = self.get_current_line_text()
        current_words = re.split(r'\W+', self.toPlainText())

        # it was just a tab
        if len(current_line) == 0 or current_line.endswith("    "):
            self.insertPlainText("    ")
            self.moveCursor(QtGui.QTextCursor.End)
            self.suggestion = None
            return
        # it was just a tab
        if len(current_line) > 0 and current_line[-1] in " (:)":
            self.suggestion = None
            return

        if self.suggestion is None:
            unfinished_word = re.split(r"[+\-*/= ]", current_line)
            if len(unfinished_word) == 0 or len(unfinished_word[-1]) == 0:
                return
            unfinished_word = unfinished_word[-1]
            word_set = list(set(current_words + self.highlighter.get_keywords() + self.autocomplete_words))

            # We want unfinished_word to be the last one
            if unfinished_word in word_set:
                word_set.remove(unfinished_word)

            self.candidates = [word for word in word_set if word.startswith(unfinished_word)]
            if len(self.candidates) == 0:
                self.insertPlainText("    ")
                return
            elif len(self.candidates) == 1:
                self.insertPlainText(self.candidates[0][len(unfinished_word):])
                self.moveCursor(QtGui.QTextCursor.End)
                return
            else:
                self.suggestion = unfinished_word

        for _ in range(len(self.suggestion)):
            self.textCursor().deletePreviousChar()
        self.candidates.append(self.suggestion)
        self.suggestion = self.candidates.pop(0)
        self.insertPlainText(self.suggestion)

    def get_next_line(self):
        count = self.count
        remaining = self.code[count:]
        remaining = remaining.split("\n")
        remaining = remaining[1:]
        remaining = [x for x in remaining if x.strip()]
        if remaining:
            return remaining[0]


class PascalEditor(SpiceMagicEditor):
    pass


class PythonEditor(SpiceMagicEditor):
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
            if self.textCursor().positionInBlock() == len(current_line):
                self.insertPlainText("\n" + " " * (spaces + 4))
                return True
            return False

        elif current_line.startswith(" "):
            if current_line.strip():
                self.insertPlainText("\n" + " " * spaces)
            else:
                self.insertPlainText("\n" + " " * (max(spaces - 4, 0)))
            return True
        return False
