from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QColor, QPainter


def create_cursor_image(size=30):
    size = 30  # Size of the cursor
    cursor_image = QPixmap(size, size)
    cursor_image.fill(Qt.transparent)  # Fill the pixmap with transparency

    # Create a QPainter to draw the red dot
    painter = QPainter(cursor_image)
    painter.setBrush(QColor(255, 0, 0, 128))  # Red color
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(0, 0, size, size)
    painter.end()

    return cursor_image