'''
	@author: Mathew Lueder
	@descrption: Project 5, a Spark-based MapReduce application 
				 that collects metrics on weather data
'''

import sys
import time
from pyspark import SparkContext


def reducer(x,y):
		if (x[0] > y[0]):
			return x
		else:
			return y

if __name__ == "__main__":

	# Create spark context
	sc = SparkContext(appName="PySparkHighestTemp")
	
	start = time.time()
	
	# Load NOAA weather data from 2008-2012
	filePaths = list()
	for year in range(2008, 2013):
		filePaths.append("/home/NOAA_DATA/" + str(year) + "/*")
	
	data = sc.textFile(','.join(filePaths))
	
	# Reduce amount of information in each dataset
	# Year : (temperature, temperature quality, latitude, longitude)
	data = data.map( lambda line: (line[15:19], (int(line[87:92]), line[92], line[28:34], line[34:41])) )
	
	# Remove suspect/erroneous data 
	data = data.filter(lambda data: data[1][1] not in ['2','3','6','7','9'])
	
	# Find largest temperatures for each year
	data = data.reduceByKey(reducer)
	
	output = data.collect()
	
	print("Elapsed Time: %f" % (time.time() - start))
	
	for (year, data) in output:
		print("%s:" % year)
		print("\tHighest Temperature = %i" % data[0])
		print("\tLatitude = %s" % data[2])
		print("\tLongitude = %s" % data[3])

	sc.stop()