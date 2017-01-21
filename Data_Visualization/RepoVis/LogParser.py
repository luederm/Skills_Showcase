__author__ = 'matthew.lueder'

import os
import re
from datetime import datetime

# path containing log files
basePath = "C:\\Users\\matthew.lueder\\Desktop\\DataVisProj\\Log_Files"

# List of all text files
listOfFiles = os.listdir(basePath)

# path to output csv
outputPath = "C:\\Users\\matthew.lueder\\Desktop\\DataVisProj\\revision_history.csv"

# The CSV which is the output of this script
csvFile = open(outputPath, 'w')
csvFile.write("Project Name,Employee Username,Time Stamp\n")

for filename in listOfFiles:
    # Create a path to the text file and open the file
    filePath = basePath + "\\" + filename
    logFile = open(filePath, 'r')

    # remove '.txt' from file name to get project name
    projectName = filename[:-4]

    # Read file line by line
    for line in logFile:
        # Take first four characters in the line
        first4 = line[:4]
        # see if line lists revision info
        if re.match("r[0-9]{3}", first4) is not None:
            # split into fields
            lineFields = line.split('|')
            # remove leading and trailing whitespace and get username
            username = lineFields[1].strip()
            # parse out time stamp
            timeStr = lineFields[2].strip()[:19]
            timeStamp = datetime.strptime( timeStr, "%Y-%m-%d %H:%M:%S" )

            # Output to csv
            newCsvLine = projectName + "," + username + "," + timeStr + '\n'
            csvFile.write(newCsvLine)


