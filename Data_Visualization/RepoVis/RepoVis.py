__author__ = 'matthew.lueder'

import sys
import copy
from datetime import datetime
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
from OverviewWindow import OverviewWindow

# This class holds a specific revision
class Revision():
    def __init__(self, projectName, userName, timeStamp):
        self.projectName = projectName
        self.userName = userName
        self.timeStamp = timeStamp

    def __str__(self):
        return "[Project Name: " + self.projectName + ", User Name: " + self.userName + \
               ", Time Stamp: " + self.timeStamp.strftime("%Y-%m-%d %H:%M:%S") + "]"

    def __repr__(self):
        return "Revision('" + self.projectName + "', '" + self.userName + \
               "', " + repr(self.timeStamp) + ")"


# Takes a list of Revision and groups the revisions by project name
def groupByProject(revisionList):
    projectGroups = {}

    for rev in revisionList:
        # See if we already made a group for this cluster
        if rev.projectName not in projectGroups:
            projectGroups[rev.projectName] = []

        projectGroups[rev.projectName].append(rev)

    return projectGroups


def createProjContributorDict(projectGroups):
    # ProjectName : Set of contributors
    contributors = {}

    for project in projectGroups.keys():
        revList = projectGroups[project]
        projContributors = set()

        for revision in revList:
            projContributors.add( revision.userName )

        contributors[project] = projContributors
        #print(projContributors)

    return contributors

# Creates clusters of projects based on who made changes to the project
# A cluster will contain projects that have been worked on by the same users
# Compares sets stored in a dictionary and returns a new dictionary where similar sets are merged
def createProjectClusters(contributorDict, projClusters = []):
    keys = list(contributorDict.keys())

    keyToCompare = keys[0]
    setToCompare = contributorDict[keyToCompare]

    del contributorDict[keyToCompare]
    del keys[0]

    cluster = []
    cluster.append(keyToCompare)

    for key in keys:
        if contributorDict[key] == setToCompare:
            cluster.append(key)
            del contributorDict[key]

    projClusters.append(cluster)

    if len(contributorDict) > 0:
        return createProjectClusters(contributorDict, projClusters)

    else:
        return projClusters

def createUserLatestRevDict(projGroups):
    userLatestRevDict = {}
    dictKeys = projGroups.keys()

    for key in dictKeys:
        revList = projGroups[key]
        intermediateDict = {}

        for rev in revList:
            if rev.userName in intermediateDict:
                # Compare timestamps
                if (rev.timeStamp > intermediateDict[rev.userName].timeStamp):
                    intermediateDict[rev.userName] = rev
            else:
                intermediateDict[rev.userName] = rev

        iUsers = intermediateDict.keys()
        for user in iUsers:
            if not user in userLatestRevDict:
                userLatestRevDict[user] = []

            userLatestRevDict[user].append(intermediateDict[user])

    return userLatestRevDict


def getUniqueUsers(revList):
    userSet = set()

    for rev in revList:
        userSet.add(rev.userName)

    return userSet


def createCommitNumDict(projGroups):
    commitNumDict = {}
    dictKeys = projGroups.keys()

    for key in dictKeys:
        if not key in commitNumDict:
            commitNumDict[key] = {}

        for rev in projGroups[key]:
            if not rev.userName in commitNumDict[key]:
                commitNumDict[key][rev.userName] = 0

            commitNumDict[key][rev.userName] +=1

    return commitNumDict


# This function reads the CSV containing the revision log
# and gives back a list of revision objects
def readInCSV(filepath):
    revisionList = []
    csvFile = open(filepath, 'r')
    firstLine = True

    for line in csvFile:

        if not firstLine:
            lineData = line.split(',')
            timeStamp = datetime.strptime( lineData[2].rstrip('\n'), "%Y-%m-%d %H:%M:%S" )
            rev = Revision(lineData[0], lineData[1], timeStamp )
            revisionList.append( rev )

        if firstLine:
            firstLine = False

    return revisionList



revList = readInCSV("C:\\Users\\Matthew\\Documents\\GVSU\\Data Vis\\Project\\revision_history.csv")
#printUniqueUsers(revList)
#sys.exit()

projGroups = groupByProject(revList)

userLastRevPerProj = createUserLatestRevDict(projGroups)
contributorDict = createProjContributorDict(projGroups)
commitNumDict = createCommitNumDict(projGroups)
contributorDictCopy = copy.deepcopy(contributorDict)

projClusters = createProjectClusters(contributorDictCopy)

users = getUniqueUsers(revList)

app = QApplication(sys.argv)

mainWindow = OverviewWindow(projClusters, users, contributorDict, userLastRevPerProj, commitNumDict)
mainWindow.populateScene()
mainWindow.showMinimized()
mainWindow.showMaximized()


sys.exit(app.exec_())


