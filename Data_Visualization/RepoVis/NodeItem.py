__author__ = 'matthew.lueder'

from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsObject
from PyQt5.QtGui import QColor, QPen, QBrush, QPainterPath
from UserView import UserView
import copy

class NodeItem(QGraphicsObject):
    nodeDoubleClicked = pyqtSignal(str)

    def __init__(self, xPos, yPos, diameter, text, isUserNode):
        super(NodeItem, self).__init__()

        self.setFlags(QGraphicsItem.ItemIsSelectable)

        self.pressed = False
        self.x = xPos - (diameter / 2)
        self.y = yPos - (diameter / 2)
        self.width = diameter
        self.height = diameter
        text = text.replace("_", "\n")
        self.text = text
        self.connectedEdges = []
        self.isUserNode = isUserNode


    def paint(self, painter, option, widget):
        painter.setPen( QPen(Qt.black, 5) )

        if not self.pressed:
            painter.setBrush( Qt.lightGray )
        else:
            painter.setBrush( Qt.blue )

        rect = QRectF(self.x, self.y, self.width, self.height)

        painter.drawEllipse(rect)
        painter.drawText( rect, Qt.AlignCenter, self.text )


    def shape(self):
        path = QPainterPath()
        path.addEllipse(self.x, self.y, self.width, self.height)
        return path


    def boundingRect(self):
        return QRectF(self.x, self.y, self.width, self.height)


    def mouseDoubleClickEvent(self, event):
        self.changeSelected() # TODO: Use timer instead
        message = ""

        if (self.isUserNode):
            message = self.text
        else:
            message = self.projListStr

        self.nodeDoubleClicked.emit(message)
        super(NodeItem, self).mouseDoubleClickEvent(event)


    def mouseReleaseEvent(self, event): # CANT USE WITH MOUSE PRESS EVENT
        self.changeSelected()
        super(NodeItem, self).mouseReleaseEvent(event)

    def setRepresentativeProjectName(self, name):
        self.representativeProjectName = name

    def getRepresentativeProjectName(self):
        return self.representativeProjectName

    def setProjectList(self, projList):
        self.projListStr = ','.join(projList)

    def addEdgeItem(self, edge):
        self.connectedEdges.append(edge)

    def changeSelected(self):
        if not self.pressed:
            self.pressed = True

            for edge in self.connectedEdges:
                edge.setPen( QPen(Qt.red, 3) )

        else:
            self.pressed = False

            for edge in self.connectedEdges:
                edge.setPen( QPen(Qt.black, 1) )

        self.update()
