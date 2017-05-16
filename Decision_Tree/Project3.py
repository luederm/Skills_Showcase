# Author: Matthew Lueder
# Description: Project 3 - Decision tree classification via the ID3 algorithm

import math
import pandas as pd
import numpy as np
import pydot
import uuid

'''
    This class encapsulates the training data and provides functions to easily access it.
'''
class Data:
    def __init__(self, dataFrame):
        self.dataFrame = dataFrame

    def oracle(self):
        return self.dataFrame.iloc[:, -1]

    def numClasses(self):
        return len(set(self.oracle()))

    def numRows(self):
        return self.dataFrame.shape[0]

    def numAttr(self):
        return self.dataFrame.shape[1]

    def attrNames(self):
        return self.dataFrame.columns.values

    def attrLevels(self, attribute):
        return set(self.dataFrame.loc[:,attribute])

    def mostCommonLevel(self, attribute):
        attrValues = self.dataFrame.loc[:,attribute]
        (attrs,counts) = np.unique((attrValues),return_counts=True)
        ind=np.argmax(counts)
        return attrs[ind]

    '''
        Calculate the frequency of examples in the data which are classified as class 'classLabel'
    '''
    def classFreq(self, classLabel):
        return np.sum(self.oracle() == classLabel) / self.numRows()

    '''
        Return a view of this data object, filtering out:
            - All examples (rows) in which attribute 'attribute' is different than 'level'
            - The 'attribute' column
    '''
    def filter(self, attribute, level):
        rowsWithLevel = self.dataFrame.loc[:,attribute] == level
        keepRows = np.where(rowsWithLevel)[0]
        ind = list(self.attrNames()).index(attribute)
        keepCols = list(range(0, self.numAttr()))
        del keepCols[ind]
        return Data(self.dataFrame.iloc[keepRows, keepCols])

    '''
        Calculate the entropy of an attribute's level.
        Can give Oracle as attribute without a level to get entropy based on class prior probability
    '''
    def entropy(self, attribute, level = None):
        if (attribute not in self.attrNames()):
            raise ValueError('Data does not contain attribute ' + attribute)

        # Use class prior probabilities to calculate entropy when attribute = 'Oracle'
        if (attribute == 'Oracle'):
            probs = [] # Class prior prob
            for classLabel in self.attrLevels(attribute):
                if (self.numRows() != 0):
                    probs.append(np.sum(self.oracle() == classLabel) / self.numRows())
                else:
                    probs.append(0)

            entropy = 0
            for prob in probs:
                if (prob != 0):
                    entropy += prob * math.log2(prob)

            return(-entropy)

        elif (level == None):
            raise ValueError('No level specified')

        elif (level not in self.attrLevels(attribute)):
            raise ValueError('Attribute ' + attribute + ' does not have level ' + level)

        else:
            tf_attr = self.dataFrame.loc[:, attribute] == level

            probs = [] # P(Class | Attribute = level)
            for classLabel in self.attrLevels('Oracle'):
                tf_oracle = self.oracle() == classLabel

                # Count the number of times this attribute's level occurs with 'classLabel'
                trueCount = 0
                for i in range(0, self.numRows()):
                    if ((tf_attr.iloc[i] == True) and (tf_oracle.iloc[i] == True)):
                        trueCount += 1

                numAttrOfLevel = np.sum(tf_attr)
                if (numAttrOfLevel != 0):
                    probs.append(trueCount / np.sum(tf_attr))
                else:
                    probs.append(0)

            entropy = 0
            for prob in probs:
                if (prob != 0):
                    entropy += prob * math.log2(prob)

            return(-entropy)

    '''
        Calculate the information gained by adding a node representing an attribute
        Gain(S,a) = prior entropy - sum( (|S_v| / |S|) * Value Entropy)
    '''
    def infoGain(self, attribute):
        priorEntropy = self.entropy("Oracle")

        (levels, counts) = np.unique((self.dataFrame.loc[:, attribute]), return_counts=True)
        summation = 0 # sum( (|S_v| / |S|) * Value Entropy)

        for i in range(0, len(levels)):
            summation += (counts[i]/self.numRows()) * (self.entropy(attribute, levels[i]))

        return priorEntropy - summation


'''
    This class represents a node in the decision tree
'''
class Node:
    def __init__(self, attrName, parent = None, isAnswer = False, freq = None, numExamples = None):
        self.attrName = attrName
        self.parent = parent
        self.isAnswer = isAnswer
        self.children = {}
        self.examples = numExamples
        self.freq = -1
        if isAnswer and freq != None:
            self.freq = freq

    '''
        If we followed the decision tree from the root down to this node, what attributes would we encounter?
        This information can be used to subset the data.
    '''
    def parentAttributes(self):
        attributes = []

        parent = self.parent
        while parent != None:
            attributes.append(parent.attrName)
            parent = parent.parent

        return(attributes)

    '''
        Construct and add a child to this node.
        level = the level of this nodes attribute which leads to the child
        attrName = the attribute of the child node
    '''
    def addChild(self, level, attrName, isAnswer = False, freq = None, numExamples = None):
        self.children[level] = Node(attrName, self, isAnswer, freq, numExamples)
        return self.children[level]


'''
    The decision tree
'''
class DecisionTree:
    def __init__(self, data):
        self.root = Node("root")
        self.__construct(self.root, "root", data)

    '''
        Recursively build the decision tree.
        Node is the node we are adding a child to.
        Level is the level of the attribute we are building a child for.
        Data is the dataset at that point (should be filtered as it goes deeper into recursion)
    '''
    def __construct(self, node, level, data):
        if (data.numAttr() == 1 or data.numClasses() == 1):
            mcl = data.mostCommonLevel("Oracle")
            node.addChild(level, mcl, True, data.classFreq(mcl), data.numRows())
            return

        # choose the attribute a that maximizes the Information Gain of S
        gain = []
        attributes = data.attrNames()[0:data.numAttr()-1]
        for attr in attributes:
            gain.append(data.infoGain(attr))
        ind = np.argmax(gain)
        maxGain = gain[ind]
        selAttr = attributes[ind]

        if maxGain != 0:
            # Add a node representing the selected attribute to the tree
            newNode = node.addChild(level, selAttr)

            # Recursively call this function on each level of the selected attribute
            levels = data.attrLevels(selAttr)
            for selLevel in levels:
                self.__construct(newNode, selLevel, data.filter(selAttr, selLevel))
        # If no info gained by adding another node, add answer instead
        else:
            mcl = data.mostCommonLevel("Oracle")
            node.addChild(level, mcl, True, data.classFreq(mcl), data.numRows())


    def classify(self, attributeList):
        node = self.root.children["root"]
        while not node.isAnswer:
            if attributeList[node.attrName] in node.children:
                node = node.children[attributeList[node.attrName]]
            else:
                return "unclassified"

        return node.attrName

    '''
        Create a plot representing the decision tree and show it.
        Uses pydot.
    '''
    def createPlot(self, filename):
        graph = pydot.Dot(graph_type='digraph')
        self.__plotRecur(graph, self.root.children["root"])
        graph.write_png(filename)


    def __plotRecur(self, graph, node, edge = None, parent = None):
        label = node.attrName
        shape = 'ellipse'
        if node.isAnswer:
            shape = 'box'
            label += '\n' + str(node.freq) + " (" + str(node.examples) + ")"

        # Create pydot node
        pyd_node = pydot.Node(str(uuid.uuid1()), label = label,
                              shape = shape, root = (parent == None), splines = "line")
        graph.add_node(pyd_node)

        # Connect it to its parent
        if edge != None:
            graph.add_edge( pydot.Edge(parent, pyd_node, label = edge, fontsize="10.0") )

        # Now move to children
        children = node.children.items()
        for child in children:
            self.__plotRecur(graph, child[1], child[0], pyd_node)


'''
    Reads data into the Data class given a file path
'''
def readData(path):
    file = open(path, 'r')

    numClasses = int(file.readline().strip())
    classes = file.readline().strip().split(",")
    numAttributes = int(file.readline().strip())
    attrNames = []

    for i in range(0,numAttributes):
        line = file.readline().strip().split(",")
        attrNames.append(line[0])

    attrNames.append("Oracle")
    df = pd.read_csv(path, names = attrNames, skiprows = numAttributes + 4)

    return Data(df)


# -- MAIN --
data = readData("car_training.data")
dt = DecisionTree(data)
test = readData("car_test.data")

# Visualize tree
dt.createPlot("output.png")

# Create empty confusion matrix
confMatrix = {}
for cls in data.attrLevels("Oracle"):
    confMatrix[cls] = {}
    for cls2 in data.attrLevels("Oracle"):
        confMatrix[cls][cls2] = 0
    confMatrix[cls]["unclassified"] = 0

# Test each training example
for i in range(0, test.numRows()):
    predClass = dt.classify(test.dataFrame.iloc[i,0:test.numAttr()-1])
    confMatrix[test.oracle()[i]][predClass] += 1

# Print confusion matrix
f = open("results.csv", 'w')
f.truncate()
actual = sorted(data.attrLevels("Oracle"))
predicted = sorted(data.attrLevels("Oracle"))
predicted.append("unclassified")

f.write("Predicted\\actual")
for actClass in actual:
    f.write("," + actClass)
f.write('\n')

for predClass in predicted:
    f.write(predClass)
    for actClass in actual:
        f.write("," + str(confMatrix[actClass][predClass]))
    f.write('\n')
