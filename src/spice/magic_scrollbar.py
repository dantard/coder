from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QScrollBar


class MagicScrollBar(QScrollBar):
    def paintEvent(self, a0) -> None:
        super().paintEvent(a0)
        if self.maximum() == 0:
            p = QPainter(self)
            p.fillRect(self.rect(), self.parent().palette().base().color())

