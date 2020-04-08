import numpy as np
import torch
from copy import deepcopy
import gym
from gym.utils import seeding
import gym_grid_driving
from gym_grid_driving.envs.grid_driving import LaneSpec, MaskSpec, Point
import math

random = None

def randomPolicy(state, env):
    '''
    Policy followed in MCTS simulation for playout
    '''
    global random
    reward = 0.
    while not state.isDone():
        action = random.choice(env.actions)
        state = state.simulateStep(action=action)
        reward += state.getReward()
    return reward

class DQNAgent():
    def act(self, model,device, state, epsilon=0.0):
        if not isinstance(state, torch.FloatTensor):
            state = torch.from_numpy(state).float().unsqueeze(0).to(device)
        '''
        FILL ME : This function should return epsilon-greedy action.

        Input:
            * `state` (`torch.tensor` [batch_size, channel, height, width])
            * `epsilon` (`float`): the probability for epsilon-greedy

        Output: action (`Action` or `int`): representing the action to be taken.
                if action is of type `int`, it should be less than `self.num_actions`
        '''
        #Get a random number and determine if agent should exploit or explore
        rand_num = np.random.random()
        if(rand_num < epsilon):#explore by choosing random action
            output_action = np.random.randint(model.num_actions)
        else:                   #exploit by choosing best action
            output_actions = model.forward(state)
            output_action = torch.argmax(output_actions).item()
        return output_action


class GridWorldState():
    def __init__(self, env, state, reward=0, is_done=False):
        '''
        Data structure to represent state of the environment
        self.env : Environment of gym_grid_environment simulator
        self.state : State of the gym_grid_environment
        self.is_done : Denotes whether the GridWorldState is terminal
        self.num_lanes : Number of lanes in gym_grid_environment
        self.width : Width of lanes in gym_grid_environment
        self.reward : Reward of the state
        '''
        self.env = deepcopy(env)
        self.state = deepcopy(state)
        self.is_done = is_done  # if is_done else False
        if self.state[1][0][0] > 0:
            self.is_done = True
        self.reward = reward

    def simulateStep(self, action):
        '''
        Simulates action at self.state and returns the next state
        '''
        state_desc = self.env.step(action=action)
        newState = GridWorldState(self.env, state=state_desc[0], reward=state_desc[1], is_done=state_desc[2])
        return newState

    def isDone(self):
        '''
        Returns whether the state is terminal
        '''
        return self.is_done

    def getReward(self):
        '''
        Returns reward of the state
        '''
        return self.reward


class Node:
    def __init__(self, state, parent=None):
        '''
        Data structure for a node of the MCTS tree
        self.state : GridWorld state represented by the node
        self.parent : Parent of the node in the MCTS tree
        self.numVisits : Number of times the node has been visited
        self.totalReward : Sum of all rewards backpropagated to the node
        self.isDone : Denotes whether the node represents a terminal state
        self.allChildrenAdded : Denotes whether all actions from the node have been explored
        self.children : Set of children of the node in the MCTS tree
        '''
        self.state = state
        self.parent = parent
        self.numVisits = 0
        self.totalReward = state.reward  # 0
        self.isDone = state.isDone()
        self.allChildrenAdded = state.isDone()
        self.children = {}



class MonteCarloTreeSearch:
    def __init__(self, env, numiters, explorationParam, playoutPolicy=randomPolicy, random_seed=None):
        '''
        self.numiters : Number of MCTS iterations
        self.explorationParam : exploration constant used in computing value of node
        self.playoutPolicy : Policy followed by agent to simulate rollout from leaf node
        self.root : root node of MCTS tree
        '''
        self.env = deepcopy(env)
        self.numiters = numiters
        self.explorationParam = explorationParam
        self.playoutPolicy = playoutPolicy
        self.root = None
        global random
        random, seed = seeding.np_random(random_seed)

    def buildTreeAndReturnBestAction(self, initialState):
        '''
        Function to build MCTS tree and return best action at initialState
        '''
        mtcs_state = GridWorldState(self.env, initialState, is_done=False)
        self.root = Node(state=mtcs_state, parent=None)
        for i in range(self.numiters):
            self.addNodeAndBackpropagate()
        bestChild = self.chooseBestActionNode(self.root, 0)
        for action, cur_node in self.root.children.items():
            if cur_node is bestChild:
                return action

    def addNodeAndBackpropagate(self):
        '''
        Function to run a single MCTS iteration
        '''
        node = self.addNode()

        reward = self.playoutPolicy(node.state, self.env)

        self.backpropagate(node, reward)

    def addNode(self):
        '''
        Function to add a node to the MCTS tree
        '''
        cur_node = self.root
        while not cur_node.isDone:
            if cur_node.allChildrenAdded:
                cur_node = self.chooseBestActionNode(cur_node, self.explorationParam)
            else:
                actions = self.env.actions
                for action in actions:
                    if action not in cur_node.children:
                        childnode = cur_node.state.simulateStep(action=action)
                        newNode = Node(state=childnode, parent=cur_node)
                        cur_node.children[action] = newNode
                        if len(actions) == len(cur_node.children):
                            cur_node.allChildrenAdded = True
                        return newNode
        return cur_node

    def backpropagate(self, node, reward):
        while node is not None:
            node.numVisits += 1
            node.totalReward += reward
            node = node.parent

        '''
        FILL ME : This function should implement the backpropation step of MCTS.
                  Update the values of relevant variables in Node Class to complete this function
        '''

    def chooseBestActionNode(self, node, explorationValue):
        '''
        FILL ME : Populate the list bestNodes with all children having maximum value

                   Value of all nodes should be computed as mentioned in question 3(b).
                   All the nodes that have the largest value should be included in the list bestNodes.
                   We will then choose one of the nodes in this list at random as the best action node.
        '''
        global random
        bestValue = float("-inf")
        bestNodes = []
        visitedBestChild = []
        isVisitedAll = True
        for child in node.children.values():
            r_child_reward = child.totalReward
            n_child_visit = child.numVisits
            n_parent_visit = node.numVisits
            if n_child_visit != 0:
                temp = r_child_reward / n_child_visit + explorationValue * math.sqrt(
                    math.log(n_parent_visit) / n_child_visit)
                if temp > bestValue:
                    visitedBestChild.clear()
                    visitedBestChild.append(child)
                    bestValue = temp
                elif temp == bestValue:
                    visitedBestChild.append(child)
            else:
                isVisitedAll = False
                bestNodes.append(child)

        if isVisitedAll:
            bestNodes = visitedBestChild

        return random.choice(bestNodes)

