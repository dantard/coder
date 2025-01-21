import os
import platform
import subprocess

import fitz  # PyMuPDF
import sys

import fitz  # PyMuPDF
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QLine, QLineF, QRectF, QPointF
from PyQt5.QtGui import QPixmap, QImage, QFont, QPainter, QColor, QCursor, QIcon, QTransform, QPen
from PyQt5.QtWidgets import QMainWindow, QLabel, QSizePolicy, QApplication, QVBoxLayout, QWidget, QPushButton, \
    QShortcut, QInputDialog, QTabBar, QToolBar, QHBoxLayout, QComboBox, QGraphicsView, QGraphicsScene, \
    QGraphicsPixmapItem, QGraphicsItem, QGraphicsEllipseItem, \
    QGraphicsRectItem, QGraphicsProxyWidget, QGraphicsLineItem
from pymupdf import Rect
from scipy.signal import savgol_filter

from utils import create_cursor_image


class Eraser(QGraphicsEllipseItem):
    pass


def smooth_with_savgol(points, window_size=5, poly_order=2):
    if len(points) < window_size < 2 * poly_order + 1:
        return points
    x = [p[0] for p in points]
    y = [p[1] for p in points]
    smoothed_x = savgol_filter(x, window_size, poly_order)
    smoothed_y = savgol_filter(y, window_size, poly_order)
    return list(zip(smoothed_x, smoothed_y))


class GraphicsScene(QGraphicsScene):
    NONE = 0
    POINTER = 1
    WRITING = 2
    ERASING = 3
    RECTANGLES = 4
    ELLIPSES = 5

    navigate = pyqtSignal(int)

    def keyPressEvent(self, event):
        print("key", event.key())
        super().keyPressEvent(event)
        if event.key() == Qt.Key_E:
            self.status = GraphicsScene.ERASING
        elif event.key() == Qt.Key_W:
            self.status = GraphicsScene.WRITING
        elif event.key() in [Qt.Key_Right, Qt.Key_Down]:
            self.navigate.emit(1)
        elif event.key() in [Qt.Key_Left, Qt.Key_Up]:
            self.navigate.emit(-1)

    def __init__(self):
        super().__init__()
        self.pixmap = QGraphicsPixmapItem()
        self.pixmap.setTransformationMode(Qt.SmoothTransformation)  # Enable smooth transformation for the pixmap item

        self.addItem(self.pixmap)
        self.image = None
        self.start = None
        self.page = 0
        self.status = GraphicsScene.NONE

        self.gum = Eraser(0, 0, 100, 100, self.pixmap)
        self.gum.setBrush(QColor(255, 255, 255))
        self.gum.setPen(QPen(QColor(0, 0, 0), 2))
        self.gum.setVisible(False)
        self.drawings = {}
        self.rectangle = None
        self.color = QPen(Qt.black, 2)
        # make the ellipse movable
        # self.gum.setFlag(QGraphicsItem.ItemIsMovable)

    def set_image(self, image, page):
        current = self.drawings.get(self.page, [])
        for item in current:
            self.removeItem(item)

        self.image = image
        self.page = page
        # self.resize_image(size)
        self.pixmap.setPixmap(self.image)

        for item in self.drawings.get(self.page, []):
            self.addItem(item)

    def mousePressEvent(self, event):
        event.accept()
        super().mousePressEvent(event)
        if event.button() == Qt.RightButton:
            return

        self.start = event.scenePos()

        # get objects at the click position
        items = self.items(self.start)
        for item in items:
            if type(item) not in [QGraphicsPixmapItem, Eraser]:
                self.start = None
                return

        if self.status == GraphicsScene.WRITING:
            self.handwriting = []

        if self.status == GraphicsScene.RECTANGLES:
            self.rectangle = self.addRect(QRectF(self.start, self.start), self.color)

        if self.status == GraphicsScene.ELLIPSES:
            self.rectangle = self.addEllipse(QRectF(self.start, self.start), self.color)

        if self.rectangle is not None:
            self.rectangle.setFlag(QGraphicsItem.ItemIsMovable)
            if self.drawings.get(self.page) is None:
                self.drawings[self.page] = []
            self.drawings[self.page].append(self.rectangle)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.start = None
        if self.status == GraphicsScene.WRITING:
            self.smooth_handwriting()

    def smooth_handwriting(self):
        points = []
        for p in self.handwriting:  # type: QGraphicsLineItem
            points.append((p.line().x1(), p.line().y1()))

        smoothed = smooth_with_savgol(points, 20, 4)

        for line in self.handwriting:
            self.removeItem(line)

        if len(smoothed) > 0:
            p1 = smoothed[0]
            for p2 in smoothed:
                self.addLine(QLineF(QPointF(*p1), QPointF(*p2)), self.color)
                p1 = p2

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.status == GraphicsScene.WRITING:
            if self.start is None:
                return

            line = self.addLine(QLineF(self.start, event.scenePos()), self.color)
            # if self.drawings.get(self.page) is None:
            #    self.drawings[self.page] = []
            # self.drawings[self.page].append(line)
            self.handwriting.append(line)
            self.start = event.scenePos()

        elif self.status == GraphicsScene.ERASING:
            if self.start is not None:
                self.gum.setPos(event.scenePos() - QLine(50, 50, 50, 50).p2())
                for item in self.gum.collidingItems():
                    if type(item) in [QGraphicsPixmapItem, QGraphicsProxyWidget]:
                        continue
                    if item in self.drawings.get(self.page, []):
                        self.drawings[self.page].remove(item)
                    self.removeItem(item)

        elif self.status in [GraphicsScene.RECTANGLES, GraphicsScene.ELLIPSES]:
            if self.start is None:
                return
            self.rectangle.setRect(QRectF(self.start, event.scenePos()))

    def erase_all(self):
        for item in self.drawings.get(self.page, []):
            self.removeItem(item)
        self.drawings[self.page] = []


class GraphicsView(QGraphicsView):

    def __init__(self, a):
        super().__init__(a)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)
        self.setRenderHint(QPainter.HighQualityAntialiasing)
        # self.scence = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        transf = QTransform()
        ratio1 = self.viewport().size().width() / self.scene().image.width()
        ratio2 = self.viewport().size().height() / self.scene().image.height()
        ratio = min(ratio1, ratio2)
        transf.scale(ratio, ratio)
        self.setTransform(transf)
        self.scene().setSceneRect(0, 0, self.scene().image.width(), self.scene().image.height())

        # if self.scence is not None:
        #    self.scene().removeItem(self.scence)
        # self.scence = self.scene().addRect(self.sceneRect(), QColor(255, 0, 0))

    def set_image(self, image, page):
        self.scene().set_image(image, page)


class Slides(QWidget):
    play_code = pyqtSignal(str)

    def set_writing_mode(self, mode):
        self.scene.status = mode
        self.scene.gum.setVisible(mode == GraphicsScene.ERASING)
        if mode == GraphicsScene.POINTER:
            self.view.setCursor(QCursor(create_cursor_image()))
        else:
            self.view.setCursor(Qt.ArrowCursor)

    def set_color(self, color):
        colors = [Qt.black, Qt.red, Qt.green, Qt.blue, Qt.yellow, Qt.magenta, Qt.cyan, Qt.gray]
        self.scene.color = QPen(colors[color], 2)

    def erase_all(self):
        self.scene.erase_all()

    def __init__(self, pdf_path, page):
        super().__init__()

        self.touchable = True
        self.program = ""
        self.code_buttons = []
        self.code_line_height = 0
        self.resized_pixmap = None
        self.doc = fitz.open(pdf_path)
        self.filename = pdf_path
        self.page = page

        # Create a QLabel to display the image
        self.scene = GraphicsScene()
        self.scene.navigate.connect(self.navigate)
        self.view = GraphicsView(self.scene)
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        # add shortcut ctrl+n to number of page
        def get_number_of_page():
            a, b = QInputDialog.getInt(self, "Number of page", "Enter the number of page", self.page + 1, 1,
                                       len(self.doc), 1, Qt.WindowFlags())
            self.page = a - 1
            self.update_image()

        q = QShortcut("Ctrl+N", self)
        q.activated.connect(get_number_of_page)

        # Set up a layout
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.addWidget(self.view)

        self.setLayout(layout)
        self.update_image()
        QTimer.singleShot(0, self.resize_image)

        QApplication.instance().setStyleSheet("""
                    QToolTip {
                        font-family: 'Courier New', monospace;
                        font-size: 12pt;
                        color: #ffffff;
                        background-color: #333333;
                        border: 1px solid #ffffff;
                    }
                """)

    def navigate(self, delta):
        self.page = (self.page + delta) % len(self.doc)
        self.update_image()

    def play_program(self, program):
        # print(program)
        self.setFocus()
        self.play_code.emit(program)
        return

        # Command to open a new terminal and execute the Python code
        if platform.system() == "Linux":
            subprocess.run([
                "gnome-terminal",
                "--",
                "bash",
                "-c",
                f"python3 -c \"{self.program}\"; exec bash"
            ])
        else:
            # Command to open a new PowerShell window and execute Python code
            subprocess.run([
                "powershell",
                "-NoExit",
                "-Command",
                f"python -c \"{self.program}\""
            ])

    def set_touchable(self, touchable):
        self.touchable = touchable

    def mousePressEvent(self, a0):
        super().mousePressEvent(a0)
        if a0.button() == Qt.RightButton:
            return

        if self.scene.status != GraphicsScene.NONE:
            return

        if self.touchable:
            right_side = a0.x() > self.view.width() // 2
            self.move_to(right_side)

    def move_to(self, right_side):
        if right_side:
            self.page = (self.page + 1) % len(self.doc)
        else:
            self.page = (self.page - 1) % len(self.doc)

        self.update_image()

    def toggle_cursor(self):
        if self.view.cursor() == Qt.ArrowCursor:
            self.set_custom_cursor(self.view)
        else:
            self.view.setCursor(Qt.ArrowCursor)
        self.view.update()

    def update_image(self):
        page = self.doc[self.page]

        pix = self.doc[self.page].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False, annots=True)
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        self.pixmap = QPixmap(image)  # QPixmap("/home/danilo/Pictures/aaa.png")
        #        self.image_label.setPixmap(self.pixmap)
        self.resize_image()
        self.view.set_image(self.pixmap, self.page)

        for button, _ in self.code_buttons:
            self.scene.removeItem(button)
        self.code_buttons.clear()

        for d in page.get_drawings():
            fill = d.get("fill")
            type = d.get("type")
            color = d.get("color")

            if type != 'f' and color == (1.0, 0, 1.0):
                rect = d.get("rect")
                # print(d)
                # page.draw_rect(rect, color=(0, 0, 0), width=5)

                # print(f"\nPage {self.page + 1}")
                self.extract_text_and_fonts(rect)

        self.update_button_pos()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_image()

    def resize_image(self):
        # Resize the pixmap to fit the QLabel while maintaining aspect ratio
        if not self.pixmap is None and not self.pixmap.isNull():
            self.resized_pixmap = self.pixmap.scaled(
                self.view.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

    def extract_text_and_fonts(self, rect=None):
        lines = []
        try:
            page = self.doc[self.page]

            # Extract blocks of text
            blocks = page.get_text("dict", clip=rect)['blocks']
            for block in blocks:
                if 'lines' in block:  # Ensure the block contains text
                    # print("\nBlock:")
                    block_bbox = block['bbox']  # Get block position
                    for line in block['lines']:
                        line_text = ""
                        line_box = line["bbox"]
                        for span in line['spans']:
                            text = span['text']
                            font = span['font']
                            position = span['bbox']  # Get position of the span
                            line_text += text

                        lines.append((line_text, line_box))

        except Exception as e:
            print(f"An error occurred: {e}")

        # print("lines", lines)

        if len(lines) != 0:
            rect: Rect

            xs = set()
            for text, pos in lines:
                x1, y1, x2, y2 = pos
                x1 = int(x1)
                xs.add(x1)
            xs = list(xs)
            xs.sort()
            # print(xs)

            program = str()
            for text, pos in lines:
                x1, y1, x2, y2 = pos
                x1 = int(x1)
                i = xs.index(x1) * 4
                program += " " * i + text + "\n"

            code_pos = (rect.x0, rect.y0, rect.x1 - rect.x0, rect.y1 - rect.y0)

            play_button = QPushButton()
            play_button.setFixedSize(45, 45)
            play_button.setIcon(self.style().standardIcon(QApplication.style().SP_MediaPlay))
            play_button.clicked.connect(lambda x=program, y=program: self.play_program(y))

            proxy = QGraphicsProxyWidget(self.scene.pixmap)
            proxy.setWidget(play_button)

            # Add the proxy widget to the scene
            # self.scene.addItem(proxy)

            self.code_buttons.append((proxy, code_pos))
            play_button.setToolTip(self.program)

    def update_button_pos(self):

        for button, code_pos in self.code_buttons:
            code_x, code_y, code_w, code_h = code_pos
            button: QGraphicsRectItem
            button.setPos((code_x + code_w) * 2 - button.sceneBoundingRect().width(),
                          (code_y + code_h) * 2 - button.sceneBoundingRect().height())
