import random
import re

import autopep8
from PyQt5 import QtGui
from PyQt5.QtCore import pyqtSignal, Qt, QTimer, QMimeData, QSize, QRect
from PyQt5.QtGui import QFont, QFontMetrics, QColor, QPainter, QTextCursor, QTextFormat
from PyQt5.QtWidgets import QTextEdit, QHBoxLayout, QScrollBar, QApplication, QWidget, QPlainTextEdit

from spiceditor.line_number_text_edit import LineNumberTextEdit
from spiceditor.magic_scrollbar import MagicScrollBar


# Claude
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class SpiceMagicEditor(QPlainTextEdit):
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

        # Claude
        self.line_number_area2 = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()
        ## Claude

        self.setContentsMargins(0, 0, 0, 0)
        self.document().setDocumentMargin(0)
        self.setViewportMargins(60, 0, 0, 0)
        #        self.setLineWrapMode(QTextEdit.NoWrap)
        self.setPlaceholderText("Write Python code here...")

        self.setHorizontalScrollBar(MagicScrollBar())
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        #        self.textChanged.connect(self.text_changed)
        #        self.horizontalScrollBar().rangeChanged.connect(self.text_changed)

        if self.highlighter:
            self.highlighter.setDocument(self.document())

        self.set_font_size(font_size)

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        space = 3 + self.fontMetrics().width('9') * digits + 20
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area2.scroll(0, dy)
        else:
            self.line_number_area2.update(0, rect.y(), self.line_number_area2.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def insertFromMimeData(self, source: QMimeData):
        """Override paste behavior to insert plain text only."""
        if source.hasText():
            self.insertPlainText(source.text())

    def set_font_size(self, font_size):
        font = QFont("Courier New")
        # font.setStyleHint(QFont.TypeWriter)
        font.setPixelSize(font_size)
        self.setFont(font)

    def show_code(self):
        self.show_all_code()

    def set_dark_mode(self, dark):
        # self.line_number_area.set_dark_mode(dark)
        self.highlighter.set_dark_mode(dark)
        self.highlighter.setDocument(self.document())

    def set_text(self, text):
        self.setPlainText(text)

    def resizeEvent(self, a0) -> None:
        # self.text_changed()
        # self.blockSignals(True)
        super().resizeEvent(a0)
        # self.blockSignals(False)
        cr = self.contentsRect()

        self.line_number_area2.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area2)
        painter.fillRect(event.rect(), QColor(240, 240, 240))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor(120, 120, 120))
                painter.setFont(self.font())
                painter.drawText(0, top, self.line_number_area2.width() - 8,
                                 self.fontMetrics().height(), Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self):
        extra_selections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(Qt.blue).lighter(190)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

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

    def setText(self, text):
        self.blockSignals(True)
        super().setPlainText(text)
        self.blockSignals(False)

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

    def indent_selected(self):
        cursor = self.textCursor()

        if not cursor.hasSelection():
            return  # No selection, do nothing

        # Get selected text (preserve newlines)
        selected_text = cursor.selection().toPlainText()

        # Add 4 spaces to each line
        indented_text = "\n".join("    " + line for line in selected_text.splitlines())

        # Replace selected text with indented version
        cursor.beginEditBlock()  # Start undo-able action
        cursor.insertText(indented_text)
        cursor.endEditBlock()  # End undo-able action

    def get_text_before_cursor(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)  # Selecciona desde el inicio de la línea
        return cursor.selectedText()

    def tab_pressed(self):

        if self.textCursor().hasSelection():
            self.indent_selected()
            return

        # Let see if we have some autocomplete candidates
        if self.suggestion is None:
            current_words = re.split(r'\W+', self.toPlainText())
            text_before_cursor = self.get_text_before_cursor()
            words_before_cursos = re.split(r"[+\-*/= ]", text_before_cursor)
            self.candidates = []
            if words_before_cursos[-1] != "":
                word_set = list(set(current_words + self.highlighter.get_keywords() + self.autocomplete_words))
                self.candidates = [word for word in word_set if word.startswith(words_before_cursos[-1])]
                if words_before_cursos[-1] in self.candidates:
                    self.candidates.remove(words_before_cursos[-1])
                    self.candidates.append(words_before_cursos[-1])
                self.suggestion = words_before_cursos[-1]

        if len(self.candidates) > 1:
            # Remove the current suggestion
            for _ in range(len(self.suggestion)):
                self.textCursor().deletePreviousChar()
            self.candidates.append(self.suggestion)
            self.suggestion = self.candidates.pop(0)
            self.insertPlainText(self.suggestion)
        else:
            self.insertPlainText("    ")

        # if len(self.candidates) > 0:

        # current_line = self.get_current_line_text()
        #
        # # it was just a tab
        # if len(current_line) == 0 or current_line.endswith("    "):
        #     self.insertPlainText("    ")
        #     self.moveCursor(QtGui.QTextCursor.End)
        #     self.suggestion = None
        #     return
        #
        # # it was just a tab
        # if len(current_line) > 0 and current_line[-1] in " (:)":
        #     self.suggestion = None
        #     return
        #
        # if self.suggestion is None:
        #
        #     if len(self.candidates) == 0:
        #         self.insertPlainText("    ")
        #         return
        #     elif len(self.candidates) == 1:
        #         self.insertPlainText(self.candidates[0][len(unfinished_word):])
        #         self.moveCursor(QtGui.QTextCursor.End)
        #         return
        #     else:
        #         self.suggestion = unfinished_word
        #
        # for _ in range(len(self.suggestion)):
        #     self.textCursor().deletePreviousChar()
        # self.candidates.append(self.suggestion)
        # self.suggestion = self.candidates.pop(0)
        # self.insertPlainText(self.suggestion)

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
