import random
import re

import autopep8
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import pyqtSignal, Qt, QTimer, QMimeData, QSize, QRect
from PyQt5.QtGui import QFont, QColor, QPainter, QTextCursor, QTextFormat
from PyQt5.QtWidgets import QTextEdit, QApplication, QWidget

from spiceditor.magic_scrollbar import MagicScrollBar
from ColabTextEditors import CollabTextEdit


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class SpiceMagicEditor(CollabTextEdit):
    ctrl_enter = pyqtSignal()
    ctrl_shift_enter = pyqtSignal()
    info = pyqtSignal(str, int, int)

    def __init__(self, highlighter=None, font_size=18):
        super().__init__()
        self.line_number_area_text_color = QColor(120, 120, 120)
        self.line_number_area_color = QColor(240, 240, 240)
        self.line_color = QColor(Qt.blue).lighter(190)

        self.highlighter = highlighter
        self.suggestion = None
        self.candidates = []
        self.count = 0
        self.mode = 0
        self.code = ""
        self.delay = 0.01
        self.autocomplete_words = []

        self.line_number_area2 = LineNumberArea(self)

        self.document().blockCountChanged.connect(self.update_line_number_area_width)
        self.document().contentsChanged.connect(self.line_number_area2.update)
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

        self.setContentsMargins(0, 0, 0, 0)
        self.document().setDocumentMargin(0)
        self.setViewportMargins(60, 0, 0, 0)
        self.setPlaceholderText("Write Python code here...")

        self.setHorizontalScrollBar(MagicScrollBar())
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        if self.highlighter:
            self.highlighter.setDocument(self.document())

        self.set_font_size(font_size)

    # ------------------------------------------------------------------
    # Line number area
    # ------------------------------------------------------------------

    def line_number_area_width(self):
        digits = len(str(max(1, self.document().blockCount())))
        space = 3 + self.fontMetrics().width('9') * digits + 20
        return space

    def update_line_number_area_width(self, _=0):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _on_scroll(self, _=0):
        self.line_number_area2.update()

    def showEvent(self, event):
        super().showEvent(event)
        # Force the document layout to compute block geometry immediately,
        # so line numbers are visible before any scrollbar appears.
        self.document().setTextWidth(self.viewport().width())
        self.line_number_area2.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep text width in sync so block rects stay valid after resize.
        self.document().setTextWidth(self.viewport().width())
        cr = self.contentsRect()
        self.line_number_area2.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area2)
        painter.fillRect(event.rect(), self.line_number_area_color)
        painter.setPen(self.line_number_area_text_color)
        painter.setFont(self.font())

        doc = self.document()
        doc_layout = doc.documentLayout()
        scroll_y = self.verticalScrollBar().value()
        line_height = self.fontMetrics().height()
        area_width = self.line_number_area2.width() - 8
        event_top = event.rect().top()
        event_bottom = event.rect().bottom()

        block = doc.begin()
        block_number = 0

        while block.isValid():
            # blockBoundingRect returns coordinates in document space;
            # subtract scroll offset to convert to viewport/widget space.
            block_rect = doc_layout.blockBoundingRect(block)
            top = int(block_rect.top()) - scroll_y
            bottom = int(block_rect.bottom()) - scroll_y

            if top > event_bottom:
                break

            if bottom >= event_top and block.isVisible():
                painter.drawText(
                    0,
                    top,
                    area_width,
                    line_height,
                    Qt.AlignRight,
                    str(block_number + 1),
                )

            block = block.next()
            block_number += 1

    # ------------------------------------------------------------------
    # Current line highlight
    # ------------------------------------------------------------------

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(self.line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_font_size(self, font_size):
        font = QFont("Courier New")
        font.setPixelSize(font_size)
        self.setFont(font)

    def set_dark_mode(self, dark):
        if dark:
            self.line_number_area_color = QColor(30, 30, 30)
            self.line_number_area_text_color = QColor(200, 200, 200)
            self.line_color = QColor(50, 50, 100)
        else:
            self.line_number_area_color = QColor(240, 240, 240)
            self.line_number_area_text_color = QColor(120, 120, 120)
            self.line_color = QColor(Qt.blue).lighter(190)

        self.highlighter.set_dark_mode(dark)
        self.highlighter.setDocument(self.document())

    def set_text(self, text):
        self.setPlainText(text)

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
        return len(self.get_code()) - self.count

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
        self.update()

    def show_code(self):
        self.show_all_code()

    def show_all_code(self):
        self._set_text_silent(self.code)
        self.set_mode(0)
        self.moveCursor(QtGui.QTextCursor.End)

    def format_code(self):
        pass  # overridden in subclasses

    # ------------------------------------------------------------------
    # Internal text helpers
    # ------------------------------------------------------------------

    def _set_text_silent(self, text):
        """Set plain text without triggering signals."""
        self.blockSignals(True)
        self.setPlainText(text)
        self.blockSignals(False)

    def setText(self, text):
        self._set_text_silent(text)

    def insertFromMimeData(self, source: QMimeData):
        if source.hasText():
            self.insertPlainText(source.text())

    # ------------------------------------------------------------------
    # Cursor / line helpers
    # ------------------------------------------------------------------

    def get_current_line(self):
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.StartOfLine)
        cursor.movePosition(QtGui.QTextCursor.EndOfLine, QtGui.QTextCursor.KeepAnchor)
        return cursor.selectedText()

    def get_current_line_text(self):
        cursor = self.textCursor()
        cursor.select(cursor.LineUnderCursor)
        return cursor.selectedText()

    def get_text_before_cursor(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        return cursor.selectedText()

    def get_spaces(self, line):
        spaces = 0
        for c in line:
            if c == " ":
                spaces += 1
            else:
                break
        return spaces

    # ------------------------------------------------------------------
    # Typing animation helpers
    # ------------------------------------------------------------------

    def complete_line(self, sleep=True):
        self.info.emit(self.get_next_line(), self.get_remaining_chars(), 20)
        if self.count < len(self.code):
            self.insertPlainText(self.code[self.count])
            self.moveCursor(QtGui.QTextCursor.End)
            self.count += 1

            if self.code[self.count - 1] == "\n":
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

    def get_next_line(self):
        remaining = self.code[self.count:]
        lines = remaining.split("\n")[1:]
        lines = [x for x in lines if x.strip()]
        if lines:
            return lines[0]
        return ""

    def append_next_char(self):
        self.count += 1
        self._set_text_silent(self.code[:self.count])
        self.moveCursor(QtGui.QTextCursor.End)

    # ------------------------------------------------------------------
    # Indentation
    # ------------------------------------------------------------------

    def indent_selected(self):
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return
        selected_text = cursor.selection().toPlainText()
        indented_text = "\n".join("    " + line for line in selected_text.splitlines())
        cursor.beginEditBlock()
        cursor.insertText(indented_text)
        cursor.endEditBlock()

    # ------------------------------------------------------------------
    # Tab / autocomplete
    # ------------------------------------------------------------------

    def tab_pressed(self):
        if self.textCursor().hasSelection():
            self.indent_selected()
            return

        if self.suggestion is None:
            current_words = re.split(r'\W+', self.toPlainText())
            text_before_cursor = self.get_text_before_cursor()
            words_before_cursor = re.split(r"[+\-*/= ]", text_before_cursor)
            self.candidates = []
            if words_before_cursor[-1] != "":
                keyword_list = self.highlighter.get_keywords() if self.highlighter else []
                word_set = list(set(current_words + keyword_list + self.autocomplete_words))
                self.candidates = [w for w in word_set if w.startswith(words_before_cursor[-1])]
                if words_before_cursor[-1] in self.candidates:
                    self.candidates.remove(words_before_cursor[-1])
                    self.candidates.append(words_before_cursor[-1])
                self.suggestion = words_before_cursor[-1]

        print("CANDIDATES:", self.candidates)
        if len(self.candidates) > 1:
            for _ in range(len(self.suggestion)):
                self.textCursor().deletePreviousChar()
            self.suggestion = self.candidates.pop(0)
            self.candidates.append(self.suggestion)
            print("Suggestion:", self.suggestion)
            self.insertPlainText(self.suggestion)
        else:
            self.insertPlainText("    ")

    # ------------------------------------------------------------------
    # Key handling
    # ------------------------------------------------------------------

    def on_return_key(self, e):
        return False

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        self.setFocusPolicy(Qt.StrongFocus)

        if e.key() == Qt.Key_Escape:
            self.set_mode(0)

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
                self._set_text_silent(self.toPlainText() + "\n")
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
                elif e.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier):
                    self.ctrl_shift_enter.emit()
                elif self.on_return_key(e):
                    pass
                else:
                    super().keyPressEvent(e)
            else:
                self.suggestion = None
                super().keyPressEvent(e)

        self.cursorPositionChanged.emit()


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
