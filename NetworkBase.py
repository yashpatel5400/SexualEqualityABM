#####################################################################
# Name: Yash Patel                                                  #
# File: NetworkBase.py                                              #
# Description: Contains all the methods pertinent to the network    #
# base model, used to produce the other graphs desired to simulate  #
#####################################################################

import sys
import os
import random
from numpy import array, zeros, std, mean, sqrt

from Verification import *
from Policy import Policy
from Switch import switch

import matplotlib.pyplot as plt
from operator import itemgetter 

try:
    import networkx as nx
except ImportError:
    raise ImportError("You must install NetworkX:\
    (http://networkx.lanl.gov/) for SE simulation")

class NetworkBase:
    #################################################################
    # Initializes the base of the network with the type it is to be #
    # i.e. SW, ER, etc... and number of coaches                     #
    #################################################################
    def __init__(self, networkType, timeSpan):
        if not self.NetworkBase_verifyBase(networkType):
            return None
        self.networkType = networkType

        # Potential score keeps track of the maximum possible score
        # (once all the incomplete policies have matured)
        self.potentialScore = 0
        self.policyScore = 0

        # Denotes those policies whose effects have and haven't been
        # fully realized
        self.completePolicies = []        
        self.incompletePolicies = []
        
        # Used for "caching": stores results after first calculation
        # since remain constant throughout simulation
        self.networkSES = 0
        self.localSES = {}

        # Parameters to be set later: default to 0 (False) -> not set
        # used to determine the mean/std values for density in network
        self.densityMean = 0 
        self.densityStd = 0

        # Parameters to be set later: default to 0 (False) -> not set
        # used to determine the mean/std values for support in network
        self.supportMean = 0 
        self.supportStd = 0

        # Marks the "max points" that can be achieved in the network
        # for the policy score
        self.policyCap = 10 * timeSpan

    #################################################################
    # Given parameters for initializing the network base, ensures   #
    # it is legal                                                   #  
    #################################################################
    def NetworkBase_verifyBase(self, networkType):
        if not Verification_verifyStr(networkType, "Network type"):
            return False
        return True

    #################################################################
    # Given a graph G, assigns it to be the graph for this network  #
    #################################################################
    def NetworkBase_setGraph(self, G):
        self.G = G

    #################################################################
    # Given dictionary of agents, assigns them for this network     #
    #################################################################
    def NetworkBase_setAgents(self, agents):
        self.Agents = agents

    #################################################################
    # Simulates updating all agents in network over a single time   #
    # step: uses each of the impacts to update the agents. Also, if #
    # desired (for hypothetical testing/sensitivity analyses), pass #
    # non-null values for all defaulted-null variables, i.e. support#
    # concealment, discrimination, etc... Forces values for such    #
    # parameters and defaults the others to standard time evolution.#
    # Score for the policy may also be supplied (defaulted to not   #
    # the case) in which case a policy with that score will be given#
    # The biasPass allows for selective production of bills, with   #
    # 0 specifying all bills are possibly, 2 being only             #
    # discriminatory, and 1 being only non-discriminatory           #
    #################################################################
    def NetworkBase_timeStep(self, time, supportDepressionImpact, 
        concealDiscriminateImpact, discriminateConcealImpact, 
        discriminateDepressionImpact, concealDepressionImpact,
        support=None, conceal=None, discrimination=None, 
        attitude=None, depression=None, policyScore=None, bias=0): 
        ONLY_NON_DISCRIMINATORY = 1
        ONLY_DISCRIMINATORY = 2

        # "Natural gap" between passing of enforced policies
        TIME_GAP = 5

        # Considers the cases where the type of policy is externally
        # enforced (not proposed at random in simulation)
        if (policyScore or bias) and time % TIME_GAP == 0:
            newPolicy = Policy(time, score=policyScore, biasPass=bias)

            # Converst from the numerical bias to a boolean for if
            # the scores are bias towards discriminatory or support
            if bias == ONLY_NON_DISCRIMINATORY: onlyDisc = False
            else: onlyDisc = True

            self.NetworkBase_enforcePolicy(time, score=policyScore, 
                onlyDisc=onlyDisc)

        else:
            newPolicy = Policy(time)
            newPolicy.Policy_considerPolicy(self, time, self.policyCap)
        
        self.NetworkBase_updatePolicyScore(time)
        for agentID in self.Agents:
            self.Agents[agentID].Agent_updateAgent(time, supportDepressionImpact,
                concealDiscriminateImpact, discriminateConcealImpact, 
                discriminateDepressionImpact, concealDepressionImpact,
                support, conceal, discrimination, attitude, depression)

    #################################################################
    # Given a list of nodes, adds edges between all of them         #
    #################################################################
    def NetworkBase_addEdges(self, nodeList):
        self.G.add_edges_from(nodeList)

    #################################################################
    # Given two agents in the graph, respectively with IDs agentID1 #
    # and agentID2, removes the edge between them                   #
    #################################################################
    def NetworkBase_removeEdge(self, agentID1, agentID2):
        self.G.remove_edge(agentID1, agentID2)

    #################################################################
    # Returns all the edges present in the graph associated with the#
    # network base                                                  #
    #################################################################
    def NetworkBase_getEdges(self):
        return self.G.edges()

    #################################################################
    # Returns the agent associated with the agentID specified       #
    #################################################################
    def NetworkBase_getAgent(self, agentID):
        return self.Agents[agentID]

    #################################################################
    # Returns the total number of agents in the graph associated w/ #
    # the network base                                              #
    #################################################################
    def NetworkBase_getNumAgents(self):
        return len(self.Agents)

    #################################################################
    # Returns an array of the neighbors of a given agent in graph   #
    #################################################################
    def NetworkBase_getFirstNeighbors(self, agent):
        agentID = agent.agentID
        return nx.neighbors(self.G, agentID)

    #################################################################
    # Returns an array of those in the "social network" of a given  #
    # agent, defined as being those separated by, at most, two      #
    # degrees in the graph (two connections away)                   #
    #################################################################
    def NetworkBase_getNeighbors(self, agent):
        agentID = agent.agentID
        neighbors = self.NetworkBase_getFirstNeighbors(agent)
        '''
        for neighbor in neighbors:
            curNeighbor = self.NetworkBase_getAgent(neighbor)
            secondDegree = self.\
                NetworkBase_getFirstNeighbors(curNeighbor)
            for nextNeighbor in secondDegree:
                if nextNeighbor not in neighbors:
                    neighbors.append(nextNeighbor)
        '''
        return neighbors

    #################################################################
    # Helper function converting the dictionary of agentID and agent#
    # to array of agent objects                                     #
    #################################################################
    def NetworkBase_getAgentArray(self):
        curAgents = []
        for agent in self.Agents:
            curAgents.append(self.Agents[agent])
        return curAgents

    #################################################################
    # Determines which of the agents has a tendency to decrease his #
    # attitude as there are more minority surrounding him (only in  #
    # population of lower SES)                                      #
    #################################################################
    def NetworkBase_chooseDiscriminate(self):
        PROB_DISCRIMINATORY = .25

        maxSES = self.NetworkBase_getMaxSES()
        topCap = maxSES/2
        agents = self.NetworkBase_getAgentArray()

        for agent in agents:
            if agent.currentSES < topCap:
                rand = random.random()
                if rand < PROB_DISCRIMINATORY:
                    agent.isDiscriminatory = True
                else:
                    agent.isDiscriminatory = False
            else:
                agent.isDiscriminatory = False

    #################################################################
    # Returns the maximum SES present amongst the agents in the sim #
    #################################################################
    def NetworkBase_getMaxSES(self):
        SESarr = []
        agents = self.NetworkBase_getAgentArray()
        for agent in agents:
            SESarr.append(agent.currentSES)
        return max(SESarr)

    #################################################################
    # Enforces a certain policy on the network in question. If a    #
    # particular strength for the policy is desired, it can be given#
    # Similarly, onlyDisc can be used to determine whether or not   #
    # the policy is defaulted to only discriminatory or only non-   #
    # discriminatory. The option for neither is excluded since this #
    # behavior would then be equivalent to standard policy passing  #
    # Only discriminatory policies is given by True and only non-   #
    # discriminatory by False                                       #
    #################################################################
    def NetworkBase_enforcePolicy(self, time, score=None, onlyDisc=False):
        ONLY_NON_DISCRIMINATORY = 1
        ONLY_DISCRIMINATORY = 2 

        if self.policyScore + score > self.policyCap:
            return

        if score:
            enforcedPolicy = Policy(time=time, score=score)
        else:
            # Maps from boolean value to the ints specified above
            biasType = int(onlyDisc) + 1
            enforcedPolicy = Policy(time=time, biasPass=biasType)
            
        self.NetworkBase_addToPolicies(enforcedPolicy, time)

    #################################################################
    # Given a policy, adds it to the policies present in the network#
    # and updates corresponding network score                       #
    #################################################################
    def NetworkBase_addToPolicies(self, policy, time):
        self.potentialScore += policy.score
        self.incompletePolicies.append(policy)

    #################################################################
    # Goes through each of the policies that are incomplete (whose  #
    # effects have not been fully realized) and updates them to     #
    # reflect the current time                                      #
    #################################################################
    def NetworkBase_updatePolicyScore(self, time):
        for incompletePolicy in self.incompletePolicies:
            incompletePolicy.Policy_updateTimeEffect(time, self.policyCap)

            self.policyScore -= incompletePolicy.prevEffect

            if (not incompletePolicy.isDiscriminatory and \
                incompletePolicy.curEffect >= incompletePolicy.score) or\
                (incompletePolicy.isDiscriminatory and \
                incompletePolicy.curEffect <= incompletePolicy.score):

                self.policyScore += incompletePolicy.score

                self.incompletePolicies.remove(incompletePolicy)
                self.completePolicies.append(incompletePolicy)
            else:
                self.policyScore += incompletePolicy.curEffect

    #################################################################
    # Determines all the nodes in the overall network/graph that are#
    # or are not of sexual minority: distinguishes based on value of#
    # wantMinority. If specified as true, returns minority nodes    #
    # in an array; otherwise, returns those nodes not minority      #
    #################################################################
    def NetworkBase_getMinorityNodes(self, wantMinority=True):
        collectNodes = []
        agents = self.NetworkBase_getAgentArray()
        for agent in agents:
            if (wantMinority and agent.isMinority) or \
                (not wantMinority and not agent.isMinority):
                collectNodes.append(agent)
        return collectNodes

    #################################################################
    # Determines the average depression level amongst those agents  #
    # in the network who are in sexual minority                     #
    #################################################################
    def NetworkBase_getMinorityDepressionAvg(self):
        minAvg = []

        minorityAgents = self.NetworkBase_getMinorityNodes()
        for minAgent in minorityAgents:
            minAvg.append(minAgent.currentDepression)
        return mean(minAvg)

    #################################################################
    # Finds the percentage of locally connected nodes (to some given#
    # agent) marked as of sexual minority. firstDegree determines   #
    # whether you wish to only find the percent in 1st degree or 2nd#
    # allSupport can be used to determine the percentage of people  #
    # connected who are in support of minorities (support > .5)     #
    #################################################################
    def NetworkBase_findPercentConnectedMinority(self, agent, 
        firstDegree=False, allSupport=False):
        SUPPORT_ATTITUDE = .25

        if firstDegree: 
            neighbors = self.NetworkBase_getFirstNeighbors(agent)
        else: 
            neighbors = self.NetworkBase_getNeighbors(agent)

        totalCount = 0
        minorityCount = 0

        for neighbor in neighbors:
            neighborAgent = self.Agents[neighbor]
            if neighborAgent.isMinority and \
                not self.Agents[neighbor].isConcealed:
                minorityCount += neighborAgent.probConceal ** 2
            elif allSupport and neighborAgent.attitude > SUPPORT_ATTITUDE:
                minorityCount += 1
            totalCount += 1

        return minorityCount/totalCount

    #################################################################
    # Finds the percentage of locally connected nodes (to some given#
    # agent) that has a low tolerance for those of LGB status       #
    #################################################################
    def NetworkBase_findPercentNonAccepting(self, agent):
        neighbors = self.NetworkBase_getNeighbors(agent)
        totalCount = 0
        nonAcceptingCount = 0

        for neighbor in neighbors:
            if self.Agents[neighbor].attitude < .5:
                nonAcceptingCount += 1
            totalCount += 1

        return nonAcceptingCount/totalCount

    #################################################################
    # Determines the average value of an attribute for the entire   #
    # network. If getPercentage is specified, determines the current# 
    #level of an attribute out of the maximal total, rather than the#
    # average (such as the %depressed or %concealed from minority)  #
    #################################################################
    def NetworkBase_findPercentAttr(self, attr, getPercentage=True):
        # Denotes the maximum "scaled" values for each parameter
        MAX_DEPRESS = .25
        MAX_CONCEALMENT = .125
        MAX_DISCRIMINATE = .25

        # Used as the denominator when calculating "average" (changes
        # if want the percentage rather than the mean)
        MAX_CONST = 1.00

        agents = self.NetworkBase_getMinorityNodes()
        minCount = len(agents)
        
        whichAttr = {
            # Lambdas are used to obtain the current agent's parameters
            # while iterating through entire list of agents. For depress/
            # concealment, another lambda made for seeing depressed/concealed
            "depression": [MAX_DEPRESS, lambda agent: \
                agent.currentDepression, lambda agent: agent.isDepressed],
            "concealed": [MAX_CONCEALMENT, lambda agent: \
                agent.probConceal, lambda agent: agent.isConcealed],
            "discrimination": [MAX_DISCRIMINATE, \
                lambda agent: agent.discrimination]
        }

        attrCapVal = whichAttr[attr]
        if getPercentage:
            MAX_CONST = attrCapVal[0]
            getAttrVal = attrCapVal[1]
            attrArr = list(map(getAttrVal, agents))

            if minCount:
                maxTotal = minCount * MAX_CONST
                return sum(attrArr)/maxTotal
            return 0.0

        filterAttrVal = attrCapVal[2]
        filteredAgents = list(filter(filterAttrVal, agents))

        if minCount: return len(filteredAgents)/minCount
        return 0.0
        
    #################################################################
    # Determines the local average value of an attribute for a given#
    # agent (in his locally connected network)                      #
    #################################################################
    def NetworkBase_getLocalAvg(self, agent, attribute):
        neighbors = self.NetworkBase_getNeighbors(agent)
        totalCount = len(neighbors)
        total = 0

        for neighbor in neighbors:
            if attribute == "SES":
                total += self.Agents[neighbor].currentSES
            elif attribute == "attitude":
                total += self.Agents[neighbor].attitude

        localAvg = total/totalCount
        return localAvg

    #################################################################
    # Given an agent in the network, returns an array formatted as  #
    # [positive average, negative average], where the averages are  #
    # of the attitudes in the local network                         #
    #################################################################
    def NetworkBase_getAttitudes(self, agent):
        posAttitude = []
        negAttitude = []

        neighbors = self.NetworkBase_getNeighbors(agent)
        for neighbor in neighbors:
            curAttitude = self.Agents[neighbor].attitude
            if curAttitude > 0:
                posAttitude.append(curAttitude)
            else:
                negAttitude.append(curAttitude)

        posAvg = self.NetworkBase_arrMean(posAttitude)
        negAvg = self.NetworkBase_arrMean(negAttitude)
        return [posAvg, negAvg]

    #################################################################
    # Sets the network properties of mean density and std deviation #
    # of density to the corresponding values of the network         #
    #################################################################
    def NetworkBase_setMeanStdDensity(self):
        agents = self.NetworkBase_getAgentArray()
        densityArr = []
        for agent in agents:
            densityArr.append(
                self.NetworkBase_findPercentConnectedMinority(agent, 
                    firstDegree=True))

        self.densityMean = mean(densityArr)
        self.densityStd = std(densityArr)

    #################################################################
    # Sets the network properties of mean density and std deviation #
    # of support to the corresponding values of the network. Can    #
    # also specify whether want the mean/std for just minority/not  #
    #################################################################
    def NetworkBase_setMeanStdSupport(self, onlyMinority=True):
        if not onlyMinority:
            agents = self.NetworkBase_getAgentArray()
        else: agents = self.NetworkBase_getMinorityNodes()
        
        supportArr = []
        for agent in agents:
            supportArr.append(agent.support)

        if not onlyMinority:
            return [mean(supportArr), std(supportArr)]

        # Only sets the minority mean/std to the network properties
        self.supportMean = mean(supportArr)
        self.supportStd = std(supportArr)

    #################################################################
    # Given an agent, determines his corresponding z-score for the  #
    # density of LGBs in his network                                #
    #################################################################
    def NetworkBase_getDensityZScore(self, agent):
        # Sets the densities only if not already determined
        if not (self.densityMean and self.densityStd):
            self.NetworkBase_setMeanStdDensity()

        curVal = self.NetworkBase_findPercentConnectedMinority(agent)
        mean = self.densityMean
        std = self.densityStd

        return self.NetworkBase_getZScore(curVal, mean, std)

    #################################################################
    # Given an agent, determines his corresponding z-score for the  #
    # support of LGBs in his network                                #
    #################################################################
    def NetworkBase_getSupportZScore(self, agent): 
        # Sets the densities only if not already determined
        if not (self.supportMean and self.supportStd):
            self.NetworkBase_setMeanStdSupport()

        curVal = agent.support
        mean = self.supportMean
        std = self.supportStd

        return self.NetworkBase_getZScore(curVal, mean, std)

    #################################################################
    # Given a value, the mean corresponding to that value in the    #
    # network, and the std deviation of such in network, determines #
    # the corresponding z-value                                     #
    #################################################################
    def NetworkBase_getZScore(self, val, mean, std):
        return (val - mean)/std

    #################################################################
    # Determines the odds of having a particular depression in      #
    # the entire population (default), only non-minority (1),or only# 
    # minority (2), from the value of onlyMinority. withSupport     #
    # determines whether the attribute is only being checked against#
    # the supported agents (2), only non-supported (1), or any (0)  #
    #################################################################
    def NetworkBase_getDepressOdds(self, onlyMinority=0, withSupport=0,
            checkDensity=False):
        # Everyone with < 0.10 support will be considered "NOT supported"
        NO_SUPPORT = .75

        # Used to calculate when the z-score is ".75" (never exact: 
        # use a bounded set to compensate)
        cutoffRange = [.90, 1.10]

        # Used for checking the parameters passed in: whether check
        # for the nodes with a property, without, or without regard
        ONLY_WANT_WITH = 2
        ONLY_WANT_WITHOUT = 1
        IRRELEVANT = 0
        
        # Determines which agents to check based on parameter
        for case in switch(onlyMinority):
            if case(ONLY_WANT_WITH):
                agents = self.NetworkBase_getMinorityNodes()
                break
            if case(ONLY_WANT_WITHOUT):
                agents = self.NetworkBase_getMinorityNodes(
                    wantMinority=False)
                break
            if case(IRRELEVANT):
                agents = self.NetworkBase_getAgentArray()
                break
            if case():
                sys.stderr.write("Minority bool must be 0, 1, 2")
                return False

        # Agent count: defaulted to number of agents being analyzed
        count = len(agents)
        totalDepression = 0
        for case in switch(withSupport):
            # Gets total depression of those with support
            if case(ONLY_WANT_WITH):
                for agent in agents:
                    z = self.NetworkBase_getSupportZScore(agent)
                    if z > NO_SUPPORT:
                        totalDepression += agent.currentDepression
                break

            # Gets depression of those without support
            if case(ONLY_WANT_WITHOUT): 
                for agent in agents:
                    z = self.NetworkBase_getSupportZScore(agent)
                    if z <= NO_SUPPORT:
                        totalDepression += agent.currentDepression
                break

            # Gets depression for all the agents in check
            if case(IRRELEVANT):
                # If calculating odds for specific level of density
                if checkDensity:
                    # Have to redo count for only agents in cutoff
                    count = 0
                    for agent in agents:
                        z = self.NetworkBase_getDensityZScore(agent)
                        if cutoffRange[0] < z:
                            totalDepression += agent.currentDepression
                            count += 1

                else:
                    for agent in agents:
                        totalDepression += agent.currentDepression
                break

            if case():
                sys.stderr.write("Support bool must be 0, 1, 2")
                return False

        if not count:
            return 0.0
        
        prob = totalDepression/count
        return prob/(1 - prob)

    #################################################################
    # Gets the average of a given array                             #
    #################################################################
    def NetworkBase_arrMean(self, array):
        if len(array) == 0:
            return 0
        return mean(array)

    #################################################################
    # Determines the network average for socio-economic status and  #
    # storeS as property of network (since const)                   #
    #################################################################
    def NetworkBase_getNetworkSES(self):
        SEStotal = 0
        for agent in self.Agents:
            SEStotal += self.Agents[agent].currentSES

        self.networkSES = SEStotal/len(self.Agents)
        return self.networkSES

    #################################################################
    # Determines the network average for sexual minority attitude   #
    #################################################################
    def NetworkBase_getNetworkAttitude(self):
        SEStotal = 0
        for agent in self.Agents:
            SEStotal += self.Agents[agent].attitude

        self.networkSES = SEStotal/len(self.Agents)
        return self.networkSES

    #################################################################
    # Determines the cumulative influence, as defined by the model, #
    # namely Attitude x (SES/Ranking)^2                             #
    #################################################################
    def NetworkBase_getTotalInfluence(self, billRank):
        totalInfluence = 0
        agents = self.NetworkBase_getAgentArray()
        for agent in agents:
            totalInfluence += agent.Agent_getBillInfluence(billRank)
            # Accounts for support involvement in bill (only for minority)
            if agent.isMinority:
                totalInfluence += (agent.support - agent.discrimination)
                if totalInfluence > 0.0:
                    totalInfluence *= (1 - agent.probConceal) ** 2
                else: totalInfluence *= agent.probConceal ** 2
        return totalInfluence

    #################################################################
    # Determines max cumulative influence, as defined by the model, #
    # namely (SES/Ranking)^2                                        #
    #################################################################
    def NetworkBase_getMaxTotalInfluence(self):
        maxInfluence = 0
        agents = self.NetworkBase_getAgentArray()
        for agent in agents:
            maxInfluence += agent.currentSES ** 2
        return maxInfluence

    #################################################################
    # Assigns to each nodes the appropriate visual attributes, with #
    # those nodes with wellness coaches given a color of red and    #
    # those without blue along with an opacity corresponding to SE  #
    #################################################################
    def NetworkBase_addVisualAttributes(self):
        # Iterate through each of the nodes present in the graph and
        # finds respective agent
        for agentID in self.G.nodes():
            curAgent = self.Agents[agentID]

            # Marks depressed agents as red nodes and blue otherwise
            self.G.node[agentID]['color'] = 'red'
            if not curAgent.isDepressed:
                self.G.node[agentID]['color'] = 'blue'

            # Displays sexual minority as different shape than others
            self.G.node[agentID]['shape'] = 'o'
            if curAgent.isMinority:
                self.G.node[agentID]['shape'] = 's'

            # Makes concealed agents less "visible" in display 
            self.G.node[agentID]['opacity'] = 1.0
            if curAgent.isConcealed:
                self.G.node[agentID]['opacity'] = .5

    #################################################################
    # Provides graphical display of the population, color coded to  #
    # illustrate who does and doesn't have the wellness coaches and #
    # sized proportional to the level of exercise. Pass in True for #
    # toShow to display directly and False to save for later view   #
    # with the fileName indicating the current timestep simulated.  #
    # pos provides the initial layout for the visual display        #
    #################################################################
    def NetworkBase_visualizeNetwork(self, toShow, time, pos):
        self.NetworkBase_addVisualAttributes()

        plt.figure(figsize=(12,12))
        for node in self.G.nodes():
            nx.draw_networkx_nodes(self.G,pos, nodelist=[node], 
                node_color=self.G.node[node]['color'],
                node_size=500, node_shape=self.G.node[node]['shape'], 
                alpha=self.G.node[node]['opacity'])
        nx.draw_networkx_edges(self.G,pos,width=1.0,alpha=.5)

        plt.title("Sexual Minority vs Depression at Time {}".format(time))
        plt.savefig("Results\\TimeResults\\timestep{}.png".format(time))
        if toShow: 
            plt.show()
        plt.close()