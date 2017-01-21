__author__ = 'matthew.lueder'

from PyQt5.QtCore import QRectF, Qt, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QPen, QBrush, QColor
from PyQt5.QtWidgets import (QMainWindow, QGridLayout, QGraphicsView,
                             QGraphicsScene, QGraphicsLineItem, QDockWidget,
                             QVBoxLayout, QHBoxLayout, QPushButton, QWidget,
                             QLabel, QSpinBox, QCheckBox, QSizePolicy)
from NodeItem import NodeItem
from EdgeItem import EdgeItem
from UserView import UserView
import copy
import matplotlib.pyplot as plt

class OverviewWindow(QMainWindow):
    def __init__(self, projectClusters, users, contributorDict, userLastRevPerProj, commitNumDict):
        QMainWindow.__init__(self)

        self.projectClusters = projectClusters
        self.projectClustersFilt = copy.deepcopy(self.projectClusters)
        self.users = users
        self.usersFilt = copy.deepcopy(self.users)
        self.contributorDict = contributorDict
        self.contributorDictFilt = copy.deepcopy(self.contributorDict)
        self.userLastRevPerProj = userLastRevPerProj
        self.userLastRevPerProjFilt = copy.deepcopy(self.userLastRevPerProj)
        self.commitNumDict = commitNumDict
        self.commitNumDictFilt = copy.deepcopy(commitNumDict)

        self.setWindowTitle("RepoVis - Source Code Repository Viewer")
        self.showMaximized()

        self.nodeDiameter = 120

        # The top layout for this window
        self.mainLayout = QGridLayout()

        # The graphics scene containing the user-project cluster graph
        self.graphicsScene = QGraphicsScene()

        # The view which shows the graphics scene
        self.graphicsView = QGraphicsView(self.graphicsScene, self)

        # Add to main layout
        self.mainLayout.addWidget(self.graphicsView, 0, 0)

        # Set this window's layout
        self.setCentralWidget(self.graphicsView)

        self.createFilterWidget()

        # Connect signals and slots
        self.applyButton.clicked.connect(self.onApplyClicked)


    def populateScene(self):
        # Create nodes and add them to the scene
        projectClustNodes = self.createProjectClustNodes()
        self.usernodes = self.createUserNodes()

        # Create connections between the nodes
        for projClustNode in projectClustNodes:
            repProjName = projClustNode.getRepresentativeProjectName()
            usersToConnect = self.contributorDictFilt[repProjName]

            for user in usersToConnect:
                x1 = self.usernodes[user].x + (self.nodeDiameter/2)
                y1 = self.usernodes[user].y + self.nodeDiameter
                x2 = projClustNode.x + (self.nodeDiameter/2)
                y2 = projClustNode.y
                edge = QGraphicsLineItem(x1, y1, x2, y2)
                self.graphicsScene.addItem(edge)
                projClustNode.addEdgeItem(edge)
                self.usernodes[user].addEdgeItem(edge)


    def createUserNodes(self):
        userNodes = {}
        nodeSpread = 50
        yPos = -400
        nodeSpan = nodeSpread + 100
        width = (len(self.usersFilt) - 1) * nodeSpan
        xPos = 0 - (width / 2)

        for user in self.usersFilt:
            newItem = NodeItem(xPos, yPos, self.nodeDiameter, user, True)
            newItem.nodeDoubleClicked.connect(self.onUserNodeDoubleClicked)
            userNodes[user] = newItem
            self.graphicsScene.addItem(newItem)
            xPos += nodeSpan

        return userNodes


    def createProjectClustNodes(self):
        projectClustNodes = []
        # Distance between edges of two two adjacent nodes
        nodeSpread = 50
        yPos = 0
        # distance between the center points of two adjacent nodes
        nodeSpan = nodeSpread + self.nodeDiameter
        # distance between the first node's center point and the last node's center point
        width = (len(self.projectClustersFilt) - 1) * nodeSpan
        # Starting x pos of the first node
        xPos = 0 - (width / 2)

        clusterNum = 1

        for cluster in self.projectClustersFilt:
            text = ""
            repName = cluster[0]

            if len(cluster) == 1:
                text = cluster[0]

            else:
                text = "Cluster_Number " + str(clusterNum)
                clusterNum += 1

            newItem = NodeItem(xPos, yPos, self.nodeDiameter, text, False)
            newItem.setRepresentativeProjectName(repName)
            newItem.setProjectList(cluster)
            newItem.nodeDoubleClicked.connect(self.onProjectClusterNodeClicked)
            projectClustNodes.append(newItem)
            self.graphicsScene.addItem(newItem)
            xPos += nodeSpan

        return projectClustNodes


    def createFilterWidget(self):
        # The dock widget we are creating
        filterWidget = QDockWidget("Filters")
        filterWidget.setFeatures(QDockWidget.NoDockWidgetFeatures)

        w = QWidget()
        w.setSizePolicy( QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum) )
        filterWidget.setWidget(w)

        # The layout inside the dock widget
        #filterLayout = QVBoxLayout()
        filterLayout = QGridLayout()
        filterLayout.setVerticalSpacing(20)
        w.setLayout(filterLayout)

        # A spin box to allow the user to narrow users by the number of projects they have contributed to
        contribLbl = QLabel("Narrow users by number of projects contributed to:")
        self.contribSB = QSpinBox()
        self.contribSB.setRange(1, len(self.projectClusters))
        self.contribSB.setValue(1)

        # A checkbox to allow user to remove selected users
        rmSelUserLayout = QHBoxLayout()
        selUserLbl = QLabel("Remove selected users")
        self.rmSelUsersCB = QCheckBox()
        rmSelUserLayout.addWidget(self.rmSelUsersCB)
        rmSelUserLayout.addWidget(selUserLbl)

        # A button to allow the user to apply filters
        self.applyButton = QPushButton("Apply")

        # Add widgets to layout
        filterLayout.addWidget(contribLbl, 0, 0, Qt.AlignTop)
        filterLayout.addWidget(self.contribSB, 1, 0, Qt.AlignTop)
        filterLayout.addLayout(rmSelUserLayout, 2, 0)
        filterLayout.addWidget(self.applyButton, 3, 0)

        # Add dock widget to main window
        self.addDockWidget(Qt.RightDockWidgetArea, filterWidget)


    def onApplyClicked(self):
        # Reset filters
        self.usersFilt = copy.deepcopy(self.users)
        self.projectClustersFilt = copy.deepcopy(self.projectClusters)
        self.contributorDictFilt = copy.deepcopy(self.contributorDict)

        self.filterUsersByNumProjContrib(self.contribSB.value())

        # filter selected users
        if self.rmSelUsersCB.checkState() == Qt.Checked:
            self.filterOutSelectedUsers()

        # reset graphics scene
        self.graphicsScene.clear()
        self.populateScene()
        self.graphicsView.viewport().update()


    def filterOutSelectedUsers(self):
        usersToRemove = []

        for nodeItem in self.usernodes.keys():
            if self.usernodes[nodeItem].pressed:
                usersToRemove.append(nodeItem)

        self.removeUsers(usersToRemove)


    def filterUsersByNumProjContrib(self, numProj):
        projects = list(self.contributorDictFilt.keys())
        UNAndNumProjs = {}

        for projName in projects:
            for user in self.contributorDictFilt[projName]:
                if user in UNAndNumProjs.keys():
                    UNAndNumProjs[user] += 1
                else:
                    UNAndNumProjs[user] = 1

        usersToRemove = []
        for name in self.usersFilt:
            if name in UNAndNumProjs:
                if UNAndNumProjs[name] < numProj:
                    usersToRemove.append(name)

        self.removeUsers(usersToRemove)

    # Remove a list of users from the filter set
    def removeUsers(self, userList):
        for userToRemove in userList:
            # Remove from user list
            if userToRemove in self.usersFilt:
                self.usersFilt.remove(userToRemove)

            # Remove from contributor dictionary
            for projName in self.contributorDictFilt.keys():
                projSet = self.contributorDictFilt[projName]
                if userToRemove in projSet:
                    projSet.remove(userToRemove)

    @pyqtSlot(str)
    def onUserNodeDoubleClicked(self, text):
        self.userView = UserView(self.userLastRevPerProj[text])
        self.userView.show()

    @pyqtSlot(str)
    def onProjectClusterNodeClicked(self, projListStr):
        projLists = []
        user_names = []
        project_names = []

        fig = plt.figure()
        fig.canvas.set_window_title('Project Cluster View')

        for proj in projListStr.split(","):
            userNames = list(self.commitNumDict[proj].keys())
            userNames.sort()
            user_names = copy.deepcopy(userNames)
            project_names.append(proj)

            projectCommitList = []

            for name in userNames:
                projectCommitList.append(self.commitNumDict[proj][name])

            projLists.append(projectCommitList)

        x = list( range( 0, len(user_names) ) )
        if len(user_names) > 1:
            for ind in range(0, len(projLists)):
                plt.plot(x, projLists[ind], label=project_names[ind])

        else:
            center = 0
            barWidth = 0.005
            start = center - (len(projLists) / 2) * barWidth
            colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
            for ind in range(0, len(projLists)):
                plt.bar(start + (ind*barWidth), projLists[ind], width=barWidth, color=colors[ind], label=project_names[ind])

        plt.legend()
        plt.ylabel("Number of Commits")

        if len(projListStr.split(",")) == 1:
            plt.title(projListStr)
        else:
            plt.title("Project Cluster")

        plt.xticks(x, user_names, rotation='vertical')
        fig = plt.gcf()
        fig.subplots_adjust(bottom=0.28)

        plt.show()
