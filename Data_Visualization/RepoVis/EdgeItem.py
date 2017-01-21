__author__ = 'matthew.lueder'

from PyQt5.QtCore import Qt, QRectF, pyqtSlot, QPointF
from PyQt5.QtWidgets import QGraphicsLineItem
from PyQt5.QtGui import QColor, QPen

class EdgeItem(QGraphicsLineItem):
    def __init__(self, x1, y1, x2, y2):
        super(EdgeItem, self).__init__()
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.highlighted = False

    def paint(self, painter, option, widget):
        if self.highlighted:
            painter.setPen( QPen(Qt.red, 3) )
        else:
            painter.setPen( QPen(Qt.black, 1) )


        painter.drawLine(self.x1, self.y1, self.x2, self.y2)


    def boundingRect(self):
        return QRectF(self.x1, self.y1, self.x2, self.y2)


    def shape(self):
        path = QPainterPath( QPointF(self.x1, self.y1) )
        path.lineTo(self.x2, self.y2)
        return path


    def setHighlighted(self, highlight):
        self.highlighted = highlight
        self.update()