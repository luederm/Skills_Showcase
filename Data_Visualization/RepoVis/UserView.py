
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel

class UserView(QDialog):
    def __init__(self, singleUserLastRevPerProj):
        super(UserView, self).__init__()

        self.setWindowTitle("Developer View")
        self.setMinimumHeight(400)
        self.setMinimumWidth(400)

        mainLayout = QVBoxLayout()

        # Label showing the user
        labelStr = "<span style=\" font-size:20pt; font-weight:600; color:#aa0000;\">" + \
                   singleUserLastRevPerProj[0].userName + "</span>"
        self.label = QLabel(labelStr)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setTextFormat(Qt.RichText)

        # The table showing projects and commits
        projectTable = QTableWidget(len(singleUserLastRevPerProj), 2)
        projectTable.setHorizontalHeaderLabels(["Project Name", "Last Commit Time"])
        projectTable.horizontalHeader().setStretchLastSection(True)

        # Sort list by time stamps
        singleUserLastRevPerProj.sort(key=lambda x: x.timeStamp, reverse=True)

        row = 0
        for rev in singleUserLastRevPerProj:
            print(rev)
            proj = QTableWidgetItem(rev.projectName)
            time = QTableWidgetItem(rev.timeStamp.strftime("%Y-%m-%d %H:%M:%S"))
            projectTable.setItem(row, 0, proj)
            projectTable.setItem(row, 1, time)
            row += 1

        # Add to layout
        mainLayout.addWidget(self.label)
        mainLayout.addWidget(projectTable)
        self.setLayout(mainLayout)






