'''
	@author: Mathew Lueder
	@descrption: Project 1, Exploratory Data Analysis
				 The purpose of this program is to calculate the Flesch readability score 
				 for multiple text files. This is done in parallel on a cluster with the help of Spark.
'''
from pyspark import SparkContext
import sys
import time
import re
import os

'''
	Counts the number of syllables with good accuracy. 
	Original found @ http://eayd.in/?p=232
'''
def countSyllables(word):
	word = word.lower()
 
	# exception_add are words that need extra syllables
	# exception_del are words that need less syllables
	exception_add = ['serious','crucial']
	exception_del = ['fortunately','unfortunately', 'awesome']

	co_one = ['cool','coach','coat','coal','count','coin','coarse','coup','coif','cook','coign','coiffe','coof','court']
	co_two = ['coapt','coed','coinci']

	pre_one = ['preach']

	syls = 0 #added syllable number
	disc = 0 #discarded syllable number

	#1) if letters < 3 : return 1
	if len(word) <= 3 :
		syls = 1
		return syls

	#2) if doesn't end with "ted" or "tes" or "ses" or "ied" or "ies", discard "es" and "ed" at the end.
	# if it has only 1 vowel or 1 set of consecutive vowels, discard. (like "speed", "fled" etc.)
	if word[-2:] == "es" or word[-2:] == "ed" :
		doubleAndtripple_1 = len(re.findall(r'[eaoui][eaoui]',word))
		if doubleAndtripple_1 > 1 or len(re.findall(r'[eaoui][^eaoui]',word)) > 1 :
			if word[-3:] == "ted" or word[-3:] == "tes" or word[-3:] == "ses" or word[-3:] == "ied" or word[-3:] == "ies" :
				pass
			else :
				disc+=1

	#3) discard trailing "e", except where ending is "le"  
	le_except = ['whole','mobile','pole','male','female','hale','pale','tale','sale','aisle','whale','while']

	if word[-1:] == "e" :
		if word[-2:] == "le" and word not in le_except :
			pass

		else :
			disc+=1

	#4) check if consecutive vowels exists, triplets or pairs, count them as one.
	doubleAndtripple = len(re.findall(r'[eaoui][eaoui]',word))
	tripple = len(re.findall(r'[eaoui][eaoui][eaoui]',word))
	disc+=doubleAndtripple + tripple

	#5) count remaining vowels in word.
	numVowels = len(re.findall(r'[eaoui]',word))

	#6) add one if starts with "mc"
	if word[:2] == "mc" :
		syls+=1

	#7) add one if ends with "y" but is not surrouned by vowel
	if word[-1:] == "y" and word[-2] not in "aeoui" :
		syls +=1

	#8) add one if "y" is surrounded by non-vowels and is not in the last word.
	for i,j in enumerate(word) :
		if j == "y" :
			if (i != 0) and (i != len(word)-1) :
				if word[i-1] not in "aeoui" and word[i+1] not in "aeoui" :
					syls+=1

	#9) if starts with "tri-" or "bi-" and is followed by a vowel, add one.
	if word[:3] == "tri" and word[3] in "aeoui" :
		syls+=1

	if word[:2] == "bi" and word[2] in "aeoui" :
		syls+=1

	#10) if ends with "-ian", should be counted as two syllables, except for "-tian" and "-cian"
	if word[-3:] == "ian" : 
	#and (word[-4:] != "cian" or word[-4:] != "tian") :
		if word[-4:] == "cian" or word[-4:] == "tian" :
			pass
		else :
			syls+=1

	#11) if starts with "co-" and is followed by a vowel, check if exists in the double syllable dictionary, if not, check if in single dictionary and act accordingly.
	if word[:2] == "co" and word[2] in 'eaoui' :

		if word[:4] in co_two or word[:5] in co_two or word[:6] in co_two :
			syls+=1
		elif word[:4] in co_one or word[:5] in co_one or word[:6] in co_one :
			pass
		else :
			syls+=1
	
	#12) if starts with "pre-" and is followed by a vowel, check if exists in the double syllable dictionary, if not, check if in single dictionary and act accordingly.
	if word[:3] == "pre" and word[3] in 'eaoui' :
		if word[:6] in pre_one :
			pass
		else :
			syls+=1
	
	#13) check for "-n't" and cross match with dictionary to add syllable.
	negative = ["doesn't", "isn't", "shouldn't", "couldn't","wouldn't"]

	if word[-3:] == "n't" :
		if word in negative :
			syls+=1
		else :
			pass  

	#14) Handling the exceptional words.
	if word in exception_del :
		disc+=1

	if word in exception_add :
		syls+=1    

	# calculate the output
	return numVowels - disc + syls

'''
	If word ends with a period, question mark, or 
	exclamation point: increment accumulator
'''
def accuSentences(word, accu):
	p = re.compile("[!.?]$")
	m = p.search(word[1])
	if m:
		accu[word[0]].add(1)

'''
	If text starts with a letter, we say it is a word and return true
'''
def isWord(textChunk):
	p = re.compile("^[a-zA-Z]")
	m = p.match(textChunk[1])
	if m:
		return True
	else:
		return False
	
'''
	Convert filepath to text title
'''
def pathToTitle(path):
	path = path[path.rfind("/")+1:path.rfind(".txt")]
	title = ""
	for c in path:
		if (c.isupper()):
			title += " " + c
		else:
			title += c
	return title.strip()
	
'''
	To be applied to each word in order to count: number of words, syllables, and sentences
	Takes the word to be analyzed and 3 accumulators for each ot the three metrics
'''
def accumulateMetrics(word, sentenceAccu, syllableAccu, wordAccu):
	accuSentences(word, sentenceAccu)
	syllableAccu[word[0]].add(countSyllables(word[1]))
	wordAccu[word[0]].add(1)

if __name__ == "__main__":

	# Create spark context
	sc = SparkContext(appName="PySparkComplexity")
	
	start = time.time()
	
	# Load data files from texts directory -> (filename, content)
	data = sc.wholeTextFiles("/home/luederm/ML/Project1/Texts/")

	# Get a list of the filepaths
	filePaths = ["file:/home/luederm/ML/Project1/Texts/" + x for x in os.listdir("/home/luederm/ML/Project1/Texts")]

	# Split into words - keep file name
	data = data.flatMap( lambda file: [(file[0],x) for x in file[1].split()] )
	
	# Remove quotes
	data.map(lambda word: (word[0], word[1].replace('"', '')))

	# Split hyphenated words
	data = data.flatMap(lambda word:  [(word[0],x) for x in word[1].split("-")])

	# Remove non-words
	data = data.filter(isWord)

	# Make accumulator to count number of sentences in each file
	numSent = {}
	for path in filePaths:
		numSent[path] = sc.accumulator(0)
	
	# Make accumulator to count number of syllables in each file
	numSyllables = {}
	for path in filePaths:
		numSyllables[path] = sc.accumulator(0)
	
	# Make accumulator to count number of words in each file
	numWords = {}
	for path in filePaths:
		numWords[path] = sc.accumulator(0)
	
	# Accumulate metrics for all texts
	data.foreach( lambda word: accumulateMetrics(word, numSent, numSyllables, numWords) )
	
	# Print out results
	for path in filePaths:
		fleschScore = 206.835 - 1.015 * (float(numWords[path].value) / float(numSent[path].value)) \
			- 84.6 * (float(numSyllables[path].value) / float(numWords[path].value))
		print("%s = %f" % (pathToTitle(path), fleschScore))
		
	print("Elapsed Time: %f" % (time.time() - start))
	
	sc.stop()
	