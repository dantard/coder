import os
import platform
import subprocess

import fitz  # PyMuPDF
import sys

import fitz  # PyMuPDF
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QFont, QPainter, QColor, QCursor, QIcon
from PyQt5.QtWidgets import QMainWindow, QLabel, QSizePolicy, QApplication, QVBoxLayout, QWidget, QPushButton, \
    QShortcut, QInputDialog, QTabBar, QToolBar, QHBoxLayout, QComboBox

from utils import create_cursor_image


class Slides(QWidget):

    play_code = pyqtSignal(str)


    def __init__(self, pdf_path, page):
        super().__init__()

        self.touchable = True
        self.cursor_image = create_cursor_image()
        self.program = ""
        self.code_pos = None
        self.code_line_height = 0
        self.resized_pixmap = None
        self.doc = fitz.open(pdf_path)
        self.filename = pdf_path

        self.page = page

        self.setWindowTitle("Resizable Image")

        # Create a QLabel to display the image
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        # Load the initial pixmap

        self.pixmap = None

        self.play_button = QPushButton(self.image_label)
        self.play_button.setIcon(self.style().standardIcon(QApplication.style().SP_MediaPlay))
        self.play_button.setVisible(False)
        #self.play_button.setFlat(True)
        #self.play_button.setStyleSheet("font-size: 16px; background-color: white; border: 1px solid black;")
        self.play_button.clicked.connect(self.play_program)

        self.cmd_bar = QWidget()
        self.cmd_bar.setLayout(QVBoxLayout())
        self.cmd_bar.setMaximumWidth(40)

        a2 = QPushButton()
        a2.setIcon(self.style().standardIcon(QApplication.style().SP_ArrowBack))
        a2.setFixedSize(40,40)
        a2.setFlat(True)
        a2.clicked.connect(lambda: self.move_to(False))

        a1 = QPushButton()
        a1.setIcon(self.style().standardIcon(QApplication.style().SP_ArrowForward))
        a1.setFixedSize(40,40)
        a1.setFlat(True)
        a1.clicked.connect(lambda: self.move_to(True))

        a3 = QPushButton()
        a3.setIcon(QIcon(self.cursor_image))
        a3.setFixedSize(40, 40)
        a3.setFlat(True)
        a3.clicked.connect(lambda: self.toggle_cursor())

        a0 = QWidget()
        a0.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        a9 = QWidget()
        a9.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.cmd_bar.layout().addWidget(a0)
        self.cmd_bar.layout().addWidget(a2)
        self.cmd_bar.layout().addWidget(a3)
        self.cmd_bar.layout().addWidget(a1)
        #self.cmd_bar.layout().addWidget(a9)



        # add shortcut ctrl+n to number of page
        def get_number_of_page():
            a, b = QInputDialog.getInt(self, "Number of page", "Enter the number of page", self.page+1, 1, len(self.doc), 1, Qt.WindowFlags())
            self.page = a-1
            self.update_image()

        q = QShortcut("Ctrl+N", self)
        q.activated.connect(get_number_of_page)

        # Set up a layout
        layout = QHBoxLayout()
        layout.addWidget(self.image_label)
        #layout.addWidget(self.cmd_bar)



        # Create a central widget
        #container = QWidget()
        #container.setLayout(layout)
        #self.setCentralWidget(container)

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

    def play_program(self):
        print(self.program)
        self.setFocus()

        self.play_code.emit(self.program)
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



    def set_custom_cursor(self, what):
        cursor = QCursor(self.cursor_image, 30 // 2, 30 // 2)  # Set the hotspot in the center

        # Set the custom cursor for the entire application
        what.setCursor(cursor)

    def set_touchable(self, touchable):
        self.touchable = touchable

    def mousePressEvent(self, a0):
        super().mousePressEvent(a0)
        if a0.button() == Qt.RightButton:
            return

        if self.touchable:
            right_side = a0.x() > self.image_label.width() // 2
            self.move_to(right_side)


    def move_to(self, right_side):
        if right_side:
            self.page = (self.page + 1) % len(self.doc)
        else:
            self.page = (self.page - 1) % len(self.doc)

        self.update_image()

    def toggle_cursor(self):
        if self.image_label.cursor().shape() == Qt.ArrowCursor:
            self.set_custom_cursor(self.image_label)
        else:
            self.image_label.setCursor(Qt.ArrowCursor)
        self.image_label.update()



    def update_image(self):
        page = self.doc[self.page]
        print("DDDDDDDDDDDDDDDDDDD", page.get_drawings())
        for d in page.get_drawings():
            fill = d.get("fill")
            type = d.get("type")
            if type != 'f':
                rect = d.get("rect")
                print(rect)
                page.draw_rect(rect, color=(0, 0, 0), width=5)

        print(f"\nPage {self.page + 1}")

        pix = self.doc[self.page].get_pixmap(matrix=fitz.Matrix(4, 4), alpha=False, annots=True)
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        self.pixmap = QPixmap(image)  # QPixmap("/home/danilo/Pictures/aaa.png")
        self.image_label.setPixmap(self.pixmap)
        self.resize_image()
        self.extract_text_and_fonts()


    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_image()
        self.cmd_bar.setGeometry(self.image_label.width() - 200, self.image_label.height()-50, 100, 50)

    def resize_image(self):
        # Resize the pixmap to fit the QLabel while maintaining aspect ratio
        if not self.pixmap is None and not self.pixmap.isNull():
            self.resized_pixmap = self.pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            self.image_label.setPixmap(self.resized_pixmap)
            self.update_button_pos()


    def keyPressEvent(self, a0):
        super().keyPressEvent(a0)
        print("what?")
        if a0.key() == Qt.Key_Right or a0.key() == Qt.Key_Up:
            self.page = (self.page + 1) % len(self.doc)
            self.update_image()
        elif a0.key() == Qt.Key_Left or a0.key() == Qt.Key_Down:
            self.page = (self.page - 1) % len(self.doc)
            self.update_image()

    def get_image_pos(self):
        pix = self.image_label.pixmap()
        label_width, label_height = self.image_label.width(), self.image_label.height()
        pixmap_width, pixmap_height = pix.width(), pix.height()

        # If image is centered, the position of the image would be the difference
        x_pos = (label_width - pixmap_width) // 2
        y_pos = (label_height - pixmap_height) // 2

        return x_pos, y_pos

    def extract_text_and_fonts(self):
        lines = []
        try:
            page = self.doc[self.page]

            # Extract blocks of text
            blocks = page.get_text("dict")['blocks']
            for block in blocks:
                if 'lines' in block:  # Ensure the block contains text
                    #print("\nBlock:")
                    block_bbox = block['bbox']  # Get block position
                    #print(f"Block Position: {block_bbox}")
                    block_text = ""
                    for line in block['lines']:
                        for span in line['spans']:
                            text = span['text']
                            font = span['font']
                            position = span['bbox']  # Get position of the span
                            if "Courier" in font:
                                #print(f"Text: {text}", f"Position: {position}")
                                block_text += text
                    if block_text != "":
                        lines.append((block_text, block_bbox))

        except Exception as e:
            print(f"An error occurred: {e}")

        if len(lines) != 0:
            text, pos = lines[-1]
            self.code_pos = (pos[0], pos[1], pos[2] - pos[0], pos[3] - pos[1])

            self.play_button.setVisible(True)
            self.update_button_pos()
        else:
            self.play_button.setVisible(False)

        xs = set()
        for text, pos in lines:
            x1,y1,x2,y2 = pos
            x1 = int(x1)
            xs.add(x1)
        xs = list(xs)
        xs.sort()
        print(xs)

        self.program = str()
        for text, pos in lines:
            x1,y1,x2,y2 = pos
            x1 = int(x1)
            i = xs.index(x1)*4
            self.program += " "*i + text + "\n"
            self.play_button.setToolTip(self.program)

    def update_button_pos(self):
        image_x, image_y = self.get_image_pos()
        p = 0.8
        zoom = self.resized_pixmap.width() / self.pixmap.width() *4

        if self.code_pos is not None:
            code_x, code_y, code_w, code_h = self.code_pos

            self.play_button.setGeometry(int(image_x + (code_x + code_w)*zoom),
                                         int(image_y + (code_y + code_h/2)*zoom-10),
                                         26, 26)


# app = QApplication(sys.argv)
# window = Slides("/home/danilo/Downloads/aaa.pdf")
# window.setMinimumSize(800, 600)
# window.show()
# sys.exit(app.exec_())
#
#
#
# # Path to the PDF file
# pdf_path = sys.argv[1]  # Replace with your PDF file path
#
# # Call the function
# extract_text_and_fonts(pdf_path)

