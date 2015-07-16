#####################################################################
# Name: Yash Patel                                                  #
# File: SensitivitySimulation.py                                    #
# Description: Performs the overall simulations again for SE over   #
# time, but does not display outputs for each simulation. Instead,  #
# looks at and plots sensitivity of exercise levels/SE results vs.  #
# variables, particularly focusing on the impacts of the updates    #
#####################################################################

import sys
import os
import csv
import random,itertools
from copy import deepcopy
import numpy as np

from SexMinDepressionSimulation import *
import matplotlib.pyplot as plt
from operator import itemgetter 

import unittest

try:
    import networkx as nx
except ImportError:
    raise ImportError("You must install NetworkX:\
    (http://networkx.lanl.gov/) for SE simulation")

#####################################################################
# Performs tests to ensure the values that were calculated are in   #
# the ranges specified in the literature                            #
#####################################################################
class OddRatiosTest(unittest.TestCase):
    def __init__(self, valuesArr):
        self.discriminateTestVal = valuesArr[0]
        self.minTestVal = valuesArr[1]
        self.supportTestVal = valuesArr[2]
        self.depressTestVal = valuesArr[3]

    def test_results_in_range(self):
       # Defines ranges (from literature) of values to test against
        discriminateTestRange = [.175, .259]
        minTestRange = [1.55, 2.65]
        supportTestRange = [1.5, 4.7]
        depressTestRange = [0.4, 1.2]

        errorStr = "{} not in range"

        self.assertTrue(discriminateTestRange[0] < self.discriminateTestVal \
            < discriminateTestRange[1], errorStr.format("Discrimination OR"))
        self.assertTrue(minTestRange[0] < self.minTestVal \
            < minTestRange[1], errorStr.format("Minority OR"))
        self.assertTrue(supportTestRange[0] < self.supportTestVal \
            < supportTestRange[1], errorStr.format("Support OR"))
        self.assertTrue(depressTestRange[0] < self.depressTestVal \
            < depressTestRange[1], errorStr.format("Depression OR"))

#####################################################################
# Given the parameters needed for running simulation, executes the  #
# simulation and returns an array of the final (population) mean    #
# exercise and SE levels                                            #
#####################################################################
def Sensitivity_runSimulation(simulationModel, percentMinority, 
    supportDepressionImpact, concealDiscriminateImpact, discriminateConcealImpact, 
    discriminateDepressionImpact, concealDepressionImpact):

    if percentMinority > 1.0:
        percentMinority = 1.0

    simulationModel.percentMinority = percentMinority
    simulationModel.supportDepressionImpact = supportDepressionImpact
    simulationModel.concealDiscriminateImpact = concealDiscriminateImpact
    simulationModel.discriminateConcealImpact = discriminateConcealImpact
    simulationModel.discriminateDepressionImpact = discriminateDepressionImpact
    simulationModel.concealDepressionImpact = concealDepressionImpact

    simulationModel.SMDModel_runStreamlineSimulation()

    curTrial = []

    curTrial.append(simulationModel.network.networkBase.\
        NetworkBase_findPercentAttr("depression"))
    curTrial.append(simulationModel.network.networkBase.\
        NetworkBase_findPercentAttr("concealed"))

    return curTrial

#####################################################################
# Given an array formatted as [[ExerciseResults, SEResults]...],    #
# as is the case for the results for each of the sensitivity trials #
# reformats the results to be of the form:                          #
# [[Independent Variable Levels], [ExerciseResult1, 2 ...],         # 
# [SEResult1, 2, ...], [Label (text for plotting)]].                #
#####################################################################
def Sensitivity_splitResults(indVarScales, mixedArr, label):
    depressArr = []
    concealArr = []

    for resultsPair in mixedArr:
        depressArr.append(resultsPair[0])
        concealArr.append(resultsPair[1]) 

    finalArr = []
    finalArr.append(indVarScales)
    finalArr.append(depressArr)
    finalArr.append(concealArr)
    finalArr.append(label)

    return finalArr

#####################################################################
# Produces graphical display for the sensitivity results of all     #
# other variables aside from network type: plots line plot for each #
#####################################################################
def Sensitivity_plotGraphs(xArray, yArray, xLabel, yLabel):
    minX = min(xArray)
    maxX = max(xArray)
    
    minY = min(yArray)
    maxY = max(yArray)

    plt.plot(xArray, yArray)
    plt.axis([minX, maxX, .9 * minY, 1.25 * maxY])
    plt.xlabel(xLabel)
    plt.ylabel(yLabel)
    plt.title('{} Vs. {}'.format(xLabel, yLabel))

    plt.savefig("Results\\Sensitivity\\{}\\{}vs{}.png"\
    	.format(xLabel, xLabel, yLabel))
    plt.close()

#####################################################################
# Performs all the tests for odds ratios to check if results match  #
# empirically verified/identified values from literature            #
#####################################################################
def Sensitivity_oddRatioTests(original):
    network = original.network.networkBase

    ONLY_WANT_WITH = 2
    ONLY_WANT_WITHOUT = 1
    IRRELEVANT = 0

    labels = ["Minority_Depress", "Support_Depress", "Density_Depress"]
    minTest = [ONLY_WANT_WITH, ONLY_WANT_WITHOUT]
    supportTest = [ONLY_WANT_WITHOUT, ONLY_WANT_WITH]
    depressTest = [True, False]
    ORTests = [minTest, supportTest, depressTest]

    ORresults = []
    values = []

    discriminateTestRange = network.\
        NetworkBase_findPercentAttr(attr="discrimination")
    ORresults.append(["Minority_Discrimination_Prevalence", \
            discriminateTestRange])
    values.append(discriminateTestRange)

    # Iterates through each of the odds ratio tests and performs
    # from the above testing values
    args = [IRRELEVANT, IRRELEVANT, False]
    copy = list(args)
    for i in range (0, len(ORTests)):
        print("Performing {} odds ratio test".format(labels[i]))
        test = ORTests[i]
        originalSet = False
        for trial in test:
            args[i] = trial
            trialResult = network.NetworkBase_getDepressOdds(
                onlyMinority=args[0], withSupport=args[1], 
                checkDensity=args[2])
            if not originalSet:
                currentOR = trialResult
                originalSet = True
            else:
                currentOR /= trialResult
        ORresults.append([labels[i], currentOR])
        values.append(currentOR)
        args = list(copy)

    # ORTest = OddRatiosTest(values)
    # ORTest.test_results_in_range()

    # Performs numerical analysis on sensitivity trials
    resultsFile = "Results\\Sensitivity\\Sensitivity_OR.txt"
    with open(resultsFile, 'w') as f:
        writer = csv.writer(f, delimiter = ' ', quoting=csv.QUOTE_NONE, 
            quotechar='', escapechar='\\')
        for OR in ORresults:
            writer.writerow(OR)

#####################################################################
# Similarly performs correlation tests to identify value of r btween#
# the parameters and the final result (depression/concealment)      #
#####################################################################
def Sensitivity_correlationTests(original, percentMinority, 
    supportDepressionImpact,  concealDiscriminateImpact, 
    discriminateConcealImpact, discriminateDepressionImpact, 
    concealDepressionImpact):
    finalResults = []
    params = [percentMinority, supportDepressionImpact,   \
    concealDiscriminateImpact, discriminateConcealImpact, \
    discriminateDepressionImpact, concealDepressionImpact]
    toVary = list(params)

    # Used to produce labels of the graphs
    labels = ["Minority_Percentage", "SupportDepression_Impact", \
        "ConcealDiscrimination_Impact", "DiscriminateConceal_Impact", \
        "DiscriminationDepression_Impact", "ConcealDepression_Impact"]

    varyTrials = [.50, 1.0, 2.0, 3.0, 4.0, 5.0]
    for i in range(0, len(params)):
        print("Performing {} sensitivity analysis".format(labels[i]))
        trials = []
        changeParams = []
        
        for trial in varyTrials: 
            toVary[i] *= trial
            changeParams.append(toVary[i])

            # Ensures that, when sensitivity analysis is conducted, the network
            # is equivalent to the one that was originally used (keeps constant)
            curTrial = deepcopy(original)
            trialResult = Sensitivity_runSimulation(curTrial, toVary[0], 
                toVary[1], toVary[2], toVary[3], toVary[4], toVary[5])

            trials.append(trialResult)
            toVary[i] = params[i]
        splitTrial = Sensitivity_splitResults(changeParams, 
            trials, labels[i])
        finalResults.append(splitTrial)
    Sensitivity_printCorrelationResults(finalResults)

#####################################################################
# Prints the results of correlation analysis to separate csv file   #
#####################################################################
def Sensitivity_printCorrelationResults(finalResults):
    # Performs numerical analysis on sensitivity trials
    resultsFile = "Results\\Sensitivity\\Sensitivity_Correlation.txt"
    with open(resultsFile, 'w') as f:
        writer = csv.writer(f, delimiter = '\n', quoting=csv.QUOTE_NONE, 
            quotechar='', escapechar='\\')
        for subResult in finalResults:
            xArr = subResult[0]
            yArr_1 = subResult[1]
            yArr_2 = subResult[2]

            yArrCorrelation_1 = np.corrcoef(xArr, yArr_1)[0][1]
            yArrCorrelation_2 = np.corrcoef(xArr, yArr_2)[0][1]

            depressCorrelate = "{} vs. Depression Correlation: {}".\
                format(subResult[3], yArrCorrelation_1)
            concealCorrelate = "{} vs. Concealment Correlation: {}".\
                format(subResult[3], yArrCorrelation_2)

            row = [depressCorrelate, concealCorrelate]
            writer.writerow(row)

            Sensitivity_plotGraphs(xArr, yArr_1, subResult[3], "Depression")
            Sensitivity_plotGraphs(xArr, yArr_2, subResult[3], "Concealment")

#####################################################################
# Conducts sensitivity tests for each of the paramaters of interest #
# and produces graphical displays for each (appropriately named).   #
# Can also use showOdd and showRegression to respectively choose    #
# to specifically perform odd ratio/regression sensitivity tests    #
#####################################################################
def Sensitivity_sensitivitySimulation(percentMinority, supportDepressionImpact, 
    concealDiscriminateImpact, discriminateConcealImpact, 
    concealDepressionImpact, discriminateDepressionImpact, original, 
    final, showOdd=True, showRegression=True):

    if showOdd:
        Sensitivity_oddRatioTests(final)

    if showRegression:
        Sensitivity_correlationTests(original, percentMinority, 
            supportDepressionImpact, concealDiscriminateImpact, 
            discriminateConcealImpact, discriminateDepressionImpact, 
            concealDepressionImpact)