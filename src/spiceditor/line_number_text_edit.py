from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor, QTextBlockFormat
from PyQt5.QtWidgets import QTextEdit

from spiceditor.magic_scrollbar import MagicScrollBar


class LineNumberTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_highlighter_color = QColor(255, 255, 255, 100)
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.setHorizontalScrollBar(MagicScrollBar())
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)


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

        # blockFmt = QTextBlockFormat()
        # blockFmt.setLineHeight(40, QTextBlockFormat.FixedHeight)
        #
        # theCursor = self.textCursor()
        # theCursor.clearSelection()
        # theCursor.select(QTextCursor.Document)
        # theCursor.mergeBlockFormat(blockFmt)

    def set_line_highlighter_color(self, color):
        self.line_highlighter_color = color
        self.update()

    def set_dark_mode(self, dark):
        self.set_line_highlighter_color(
            QColor(0, 0, 0, 50) if not dark else QColor(255, 255, 255, 100))
