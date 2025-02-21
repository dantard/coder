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

def color(icon_path, color):
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