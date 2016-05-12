#!/usr/bin/env python3
# kingandassassins.py
# Author: Sébastien Combéfis
# Version: April 29, 2016

import argparse
import json
import random
import socket
from nextto import *
import sys

from lib import game

BUFFER_SIZE = 2048

CARDS = (
    # (AP King, AP Knight, Fetter, AP Population/Assassins)
    (1, 6, True, 5),
    (1, 5, False, 4),
    (1, 6, True, 5),
    (1, 6, True, 5),
    (1, 5, True, 4),
    (1, 5, False, 4),
    (2, 7, False, 5),
    (2, 7, False, 4),
    (1, 6, True, 5),
    (1, 6, True, 5),
    (2, 7, False, 5),
    (2, 5, False, 4),
    (1, 5, True, 5),
    (1, 5, False, 4),
    (1, 5, False, 4)
)

POPULATION = {
    'monk', 'plumwoman', 'appleman', 'hooker', 'fishwoman', 'butcher',
    'blacksmith', 'shepherd', 'squire', 'carpenter', 'witchhunter', 'farmer'
}

BOARD = (
    ('R', 'R', 'R', 'R', 'R', 'G', 'G', 'R', 'R', 'R'),
    ('R', 'R', 'R', 'R', 'R', 'G', 'G', 'R', 'R', 'R'),
    ('R', 'G', 'G', 'G', 'G', 'G', 'G', 'G', 'G', 'R'),
    ('R', 'G', 'G', 'G', 'G', 'G', 'G', 'G', 'G', 'G'),
    ('R', 'G', 'G', 'G', 'G', 'R', 'R', 'G', 'G', 'G'),
    ('G', 'G', 'G', 'G', 'G', 'R', 'R', 'G', 'G', 'G'),
    ('R', 'R', 'G', 'G', 'G', 'R', 'R', 'G', 'G', 'G'),
    ('R', 'R', 'G', 'G', 'G', 'R', 'R', 'G', 'G', 'G'),
    ('R', 'R', 'G', 'G', 'G', 'G', 'G', 'G', 'G', 'G'),
    ('R', 'R', 'G', 'G', 'G', 'G', 'G', 'G', 'G', 'G')
)

# Coordinates of pawns on the board
KNIGHTS = {(1, 3), (3, 0), (7, 8), (8, 7), (8, 8), (8, 9), (9, 8)}
VILLAGERS = {
    (1, 7), (2, 1), (3, 4), (3, 6), (5, 2), (5, 5),
    (5, 7), (5, 9), (7, 1), (7, 5), (8, 3), (9, 5)
}

# Separate board containing the position of the pawns
PEOPLE = [[None for column in range(10)] for row in range(10)]

# Place the king in the right-bottom corner
PEOPLE[9][9] = 'king'

# Place the knights on the board
for coord in KNIGHTS:
    PEOPLE[coord[0]][coord[1]] = 'knight'

# Place the villagers on the board
# random.sample(A, len(A)) returns a list where the elements are shuffled
# this randomizes the position of the villagers
for villager, coord in zip(random.sample(POPULATION, len(POPULATION)), VILLAGERS):
    PEOPLE[coord[0]][coord[1]] = villager

KA_INITIAL_STATE = {
    'board': BOARD,
    'people': PEOPLE,
    'castle': [(3, 2, 'N'), (4, 1, 'W')],
    'card': None,
    'king': 'healthy',
    'lastopponentmove': [],
    'arrested': [],
    'killed': {
        'knights': 0,
        'assassins': 0
    }
}


class KingAndAssassinsState(game.GameState):
    '''Class representing a state for the King & Assassins game.'''

    DIRECTIONS = {
        'E': (0, 1),
        'W': (0, -1),
        'S': (1, 0),
        'N': (-1, 0)
    }

    def __init__(self, initialstate=KA_INITIAL_STATE):
        super().__init__(initialstate)

    def _nextfree(self, x, y, d):
        people = self._state['visible']['people']
        nx, ny = self._getcoord((x, y, d))
        ix, iy = nx, ny
        while 0 <= ix <= 9 and 0 <= iy <= 9 and people[ix][iy] is not None:
            # Must be a villager
            if people[ix][iy] not in POPULATION:
                return None
            # Cannot be a roof
            if (ix, iy) != (nx, ny) and BOARD[ix][iy] == 'R':
                return None
            ix, iy = self._getcoord((ix, iy, d))
        if 0 <= ix <= 9 and 0 <= iy <= 9:
            return (ix, iy)
        return None

    def update(self, moves, player):
        visible = self._state['visible']
        hidden = self._state['hidden']
        people = visible['people']
        for move in moves:
            print(move)
            # ('move', x, y, dir): moves person at position (x,y) of one cell in direction dir
            if move[0] == 'move':
                x, y, d = int(move[1]), int(move[2]), move[3]
                p = people[x][y]
                if p is None:
                    raise game.InvalidMoveException('{}: there is no one to move'.format(move))
                nx, ny = self._getcoord((x, y, d))
                new = people[nx][ny]
                # King, assassins, villagers can only move on a free cell
                if p != 'knight' and new is not None:
                    raise game.InvalidMoveException('{}: cannot move on a cell that is not free'.format(move))
                if p == 'king' and BOARD[nx][ny] == 'R':
                    raise game.InvalidMoveException('{}: the king cannot move on a roof'.format(move))
                if (p in {'assassin'} or p in POPULATION) and player != 0:
                    raise game.InvalidMoveException('{}: villagers and assassins can only be moved by player 0'.format(move))
                if p in {'king', 'knight'} and player != 1:
                    raise game.InvalidMoveException('{}: the king and knights can only be moved by player 1'.format(move))
                # Move granted if cell is free
                if new is None:
                    people[x][y], people[nx][ny] = people[nx][ny], people[x][y]
                # If cell is not free, check if the knight can push villagers
                else:
                    nf = self._nextfree((x, y, d))
                    if nf is None:
                        raise game.InvalidMoveException('{}: cannot move-and-push in the given direction'.format(move))
                    nfx, nfy = nf
                    while (nfx, nfy) != (x, y):
                        px, py = self._getcoord((nfx, nfx, {'E': 'W', 'W': 'E', 'S': 'N', 'N': 'S'}[d]))
                        people[nfx][nfy] = people[px][py]
                        nfx, nfy = px, py
            # ('arrest', x, y, dir): arrests the villager in direction dir with knight at position (x, y)
            elif move[0] == 'arrest':
                if player != 1:
                    raise game.InvalidMoveException('arrest action only possible for player 1')
                x, y, d = int(move[1]), int(move[2]), move[3]
                arrester = people[x][y]
                if arrester != 'knight':
                    raise game.InvalidMoveException('{}: the attacker is not a knight'.format(move))
                tx, ty = self._getcoord((x, y, d))
                target = people[tx][ty]
                if target not in POPULATION:
                    raise game.InvalidMoveException('{}: only villagers can be arrested'.format(move))
                visible['arrested'].append(people[tx][ty])
                people[tx][ty] = None
            # ('kill', x, y, dir): kills the assassin/knight in direction dir with knight/assassin at position (x, y)
            elif move[0] == 'kill':
                x, y, d = int(move[1]), int(move[2]), move[3]
                killer = people[x][y]
                if killer == 'assassin' and player != 0:
                    raise game.InvalidMoveException('{}: kill action for assassin only possible for player 0'.format(move))
                if killer == 'knight' and player != 1:
                    raise game.InvalidMoveException('{}: kill action for knight only possible for player 1'.format(move))
                tx, ty = self._getcoord((x, y, d))
                target = people[tx][ty]
                if target is None:
                    raise game.InvalidMoveException('{}: there is no one to kill'.format(move))
                if killer == 'assassin' and target == 'knight':
                    visible['killed']['knights'] += 1
                    people[tx][ty] = None
                elif killer == 'knight' and target == 'assassin':
                    visible['killed']['assassins'] += 1
                    people[tx][ty] = None
                else:
                    raise game.InvalidMoveException('{}: forbidden kill'.format(move))
            # ('attack', x, y, dir): attacks the king in direction dir with assassin at position (x, y)
            elif move[0] == 'attack':
                if player != 0:
                    raise game.InvalidMoveException('attack action only possible for player 0')
                x, y, d = int(move[1]), int(move[2]), move[3]
                attacker = people[x][y]
                if attacker != 'assassin':
                    raise game.InvalidMoveException('{}: the attacker is not an assassin'.format(move))
                tx, ty = self._getcoord((x, y, d))
                target = people[tx][ty]
                if target != 'king':
                    raise game.InvalidMoveException('{}: only the king can be attacked'.format(move))
                visible['king'] = 'injured' if visible['king'] == 'healthy' else 'dead'
            # ('reveal', x, y): reveals villager at position (x,y) as an assassin
            elif move[0] == 'reveal':
                if player != 0:
                    raise game.InvalidMoveException('raise action only possible for player 0')
                x, y = int(move[1]), int(move[2])
                p = people[x][y]
                if p not in hidden['assassins']:
                    raise game.InvalidMoveException('{}: the specified villager is not an assassin'.format(move))
                people[x][y] = 'assassin'
        # If assassins' team just played, draw a new card
        if player == 0:
            visible['card'] = hidden['cards'].pop()

    def _getcoord(self, coord):
        return tuple(coord[i] + KingAndAssassinsState.DIRECTIONS[coord[2]][i] for i in range(2))

    def winner(self):
        visible = self._state['visible']
        hidden = self._state['hidden']
        # The king reached the castle
        for doors in visible['castle']:
            coord = self._getcoord(doors)
            if visible['people'][coord[0]][coord[1]] == 'king':
                return 1
        # The are no more cards
        if len(hidden['cards']) == 0:
            return 0
        # The king has been killed
        if visible['king'] == 'dead':
            return 0

        # All the assassins have been arrested or killed
        if visible['killed']['assassins'] + len(set(visible['arrested']) & hidden['assassins']) == 3:
            return 1
        return -1

    def isinitial(self):
        return self._state['hidden']['assassins'] is None

    def setassassins(self, assassins):
        self._state['hidden']['assassins'] = set(assassins)

    def prettyprint(self):
        visible = self._state['visible']
        hidden = self._state['hidden']
        result = ''
        if hidden is not None:
            result += '   - Assassins: {}\n'.format(hidden['assassins'])
            result += '   - Remaining cards: {}\n'.format(len(hidden['cards']))
        result += '   - Current card: {}\n'.format(visible['card'])
        result += '   - King: {}\n'.format(visible['king'])
        result += '   - People:\n'
        result += '   +{}\n'.format('----+' * 10)
        for i in range(10):
            result += '   | {} |\n'.format(' | '.join(['  ' if e is None else e[0:2] for e in visible['people'][i]]))
            result += '   +{}\n'.format(''.join(['----+' if e == 'G' else '^^^^+' for e in visible['board'][i]]))
        print(result)

    @classmethod
    def buffersize(cls):
        return BUFFER_SIZE


class KingAndAssassinsServer(game.GameServer):
    '''Class representing a server for the King & Assassins game'''

    def __init__(self, verbose=False):
        super().__init__('King & Assassins', 2, KingAndAssassinsState(), verbose=verbose)
        self._state._state['hidden'] = {
            'assassins': None,
            'cards': random.sample(CARDS, len(CARDS))
        }

    def _setassassins(self, move):
        state = self._state
        if 'assassins' not in move:
            raise game.InvalidMoveException('The dictionary must contain an "assassins" key')
        if not isinstance(move['assassins'], list):
            raise game.InvalidMoveException('The value of the "assassins" key must be a list')
        for assassin in move['assassins']:
            if not isinstance(assassin, str):
                raise game.InvalidMoveException('The "assassins" must be identified by their name')
            if not assassin in POPULATION:
                raise game.InvalidMoveException('Unknown villager: {}'.format(assassin))
        state.setassassins(move['assassins'])
        state.update([], 0)

    def applymove(self, move):
        try:
            state = self._state
            move = json.loads(move)
            if state.isinitial():
                self._setassassins(move)
            else:
                self._state.update(move['actions'], self.currentplayer)
        except game.InvalidMoveException as e:
            raise e
        except Exception as e:
            print(e)
            raise game.InvalidMoveException('A valid move must be a dictionary')


class KingAndAssassinsClient(game.GameClient):
    '''Class representing a client for the King & Assassins game'''

    def __init__(self, name, server, verbose=False):
        self.__name = name
        self.__actualpos=dict()
        self.__actualpos['knights']=dict()
        self.__actualpos['plebs'] = dict()
        self.__actualpos['assassins'] = dict()
        self.__compt=dict()
        super().__init__(server, KingAndAssassinsState, verbose=verbose)


    def _handle(self, message):
        pass

    def _nextmove(self, state):
        # Two possible situations:
        # - If the player is the first to play, it has to select his/her assassins
        #   The move is a dictionary with a key 'assassins' whose value is a list of villagers' names
        # - Otherwise, it has to choose a sequence of actions
        #   The possible actions are:
        #   ('move', x, y, dir): moves person at position (x,y) of one cell in direction dir
        #   ('arrest', x, y, dir): arrests the villager in direction dir with knight at position (x, y)
        #   ('kill', x, y, dir): kills the assassin/knight in direction dir with knight/assassin at position (x, y)
        #   ('attack', x, y, dir): attacks the king in direction dir with assassin at position (x, y)
        #   ('reveal', x, y): reveals villager at position (x,y) as an assassin
        state = state._state['visible']

        if state['card'] is None:
            if self._playernb==0:
                ass1 = state['people'][2][1]
                ass2 = state['people'][5][5]
                ass3 = state['people'][7][5]
                self.assassins_list = [ass1, ass2, ass3]
                ikn=1
                for i in range(10):
                    for j in range(10):
                        if state['people'][i][j] == 'king':
                            self.__actualpos['king'] = dict()
                            self.__actualpos['king']['x'] = i
                            self.__actualpos['king']['y'] = j


                        if state['people'][i][j] == 'knight':

                            self.__actualpos['knights']['knight' + str(ikn)] = dict()
                            self.__actualpos['knights']['knight' + str(ikn)]['x'] = i
                            self.__actualpos['knights']['knight' + str(ikn)]['y'] = j
                            ikn += 1

                self.__compt['compteur']=1

                return json.dumps({'assassins': [ass1, ass2, ass3]}, separators=(',', ':'))


        else:

            if self._playernb == 0:

                iass = 1
                ikn = 1

                for i in range(10):
                    for j in range(10):
                        if state['people'][i][j] == 'king':
                            self.__actualpos['king'] = dict()
                            self.__actualpos['king']['x'] = i
                            self.__actualpos['king']['y'] = j

                        if state['people'][i][j] == 'knight':

                            self.__actualpos['knights']['knight' + str(ikn)] = dict()
                            self.__actualpos['knights']['knight' + str(ikn)]['x'] = i
                            self.__actualpos['knights']['knight' + str(ikn)]['y'] = j
                            ikn += 1
                        if state['people'][i][j] in self.assassins_list or state['people'][i][j]=='assassin':

                            self.__actualpos['assassins']['assassin'+str(iass)] = dict()
                            self.__actualpos['assassins']['assassin' + str(iass)]['x'] = i
                            self.__actualpos['assassins']['assassin' + str(iass)]['y'] = j
                            iass += 1
                        else:
                            if state['people'][i][j]!='king' and state['people'][i][j]!='assassin' and state['people'][i][j]!='knight':

                                self.__actualpos['plebs'][state['people'][i][j]] = dict()
                                self.__actualpos['plebs'][state['people'][i][j]]['x'] = i
                                self.__actualpos['plebs'][state['people'][i][j]]['y'] = j

                for assassin in self.__actualpos['assassins']:
                    assx=self.__actualpos['assassins'][assassin]['x']
                    assy=(self.__actualpos['assassins'][assassin]['y'])
                    kingx= self.__actualpos['king']['x']
                    kingy= self.__actualpos['king']['y']
                    print('position of ',assassin, 'is',assx, assy)

                    if (assy) < kingy:
                        dir='E'
                        for knight in self.__actualpos['knights']:
                            knightx=self.__actualpos['knights'][knight]['x']
                            knighty=self.__actualpos['knights'][knight]['y']


                            if knightx==(assx) and knighty==assy+1:
                                print('killed the knight in',knightx,knighty)
                                state['people'][knightx][knighty] = None
                                self.__actualpos['knights'].pop(knight,None)
                                return json.dumps({'actions': [('reveal',assx,assy),('kill',assx ,assy,dir)]}, separators=(',', ':'))
                        if kingx==assx and kingy==assy+1 and state['people'][assx][assy]!='assassin':
                            return json.dumps({'actions': [('reveal',assx,assy),('attack',assx ,assy,dir)]}, separators=(',', ':'))
                        if kingx==assx and kingy==assy+1 and state['people'][assx][assy]=='assassin':
                            return json.dumps({'actions': [('attack',assx ,assy,dir)]}, separators=(',', ':'))

                        for person in self.__actualpos['plebs']:
                            personx=self.__actualpos['plebs'][person]['x']
                            persony=self.__actualpos['plebs'][person]['y']

                            if personx==(assx) and persony==assy+1:
                                return json.dumps({'actions': [('move',assx ,assy,'S'),('move',assx ,assy,dir)]}, separators=(',', ':'))


                        else:
                            return json.dumps({'actions': [('move',assx ,assy,dir),('move',assx ,assy+1,dir)]}, separators=(',', ':'))

                    if assy >kingx:
                        dir='W'
                        for knight in self.__actualpos['knights']:
                            knightx=self.__actualpos['knights'][knight]['x']
                            knighty=self.__actualpos['knights'][knight]['y']


                            if knightx==(assx) and knighty==assy-1:
                                print('killed the knight in',knightx,knighty)
                                state['people'][knightx][knighty] = None
                                self.__actualpos['knights'].pop(knight,None)
                                return json.dumps({'actions': [('reveal',assx,assy),('kill',assx ,assy,dir)]}, separators=(',', ':'))
                        if kingx==assx and kingy==assy-1 and state['people'][assx][assy]!='assassin':
                            return json.dumps({'actions': [('reveal',assx,assy),('attack',assx ,assy,dir)]}, separators=(',', ':'))
                        if kingx==assx and kingy==assy-1 and state['people'][assx][assy]=='assassin':
                            return json.dumps({'actions': [('attack',assx ,assy,dir)]}, separators=(',', ':'))

                        for person in self.__actualpos['plebs']:
                            personx=self.__actualpos['plebs'][person]['x']
                            persony=self.__actualpos['plebs'][person]['y']

                            if personx==(assx) and persony==assy-1:

                                return json.dumps({'actions': [('move',assx ,assy,'N'),('move',assx ,assy-1,dir)]}, separators=(',', ':'))



                        else:
                            return json.dumps({'actions': [('move',assx ,assy,dir),('move',assx ,assy,dir)]}, separators=(',', ':'))


                    if assx < kingx:
                        dir='S'
                        for knight in self.__actualpos['knights']:
                            knightx=self.__actualpos['knights'][knight]['x']
                            knighty=self.__actualpos['knights'][knight]['y']


                            if knightx==(assx+1) and knighty==assy:
                                print('killed the knight in',knightx,knighty)
                                state['people'][knightx][knighty] = None
                                self.__actualpos['knights'].pop(knight,None)
                                return json.dumps({'actions': [('reveal',assx,assy),('kill',assx ,assy,dir)]}, separators=(',', ':'))
                        if kingx==assx+1 and kingy==assy and state['people'][assx][assy]!='assassin':
                            return json.dumps({'actions': [('reveal',assx,assy),('attack',assx ,assy,dir)]}, separators=(',', ':'))
                        if kingx==assx+1 and kingy==assy and state['people'][assx][assy]=='assassin':
                            return json.dumps({'actions': [('attack',assx ,assy,dir)]}, separators=(',', ':'))

                        for person in self.__actualpos['plebs']:
                            personx=self.__actualpos['plebs'][person]['x']
                            persony=self.__actualpos['plebs'][person]['y']

                            if personx==(assx+1) and persony==assy:
                                return json.dumps({'actions': [('move',assx ,assy,'E'),('move',assx ,assy,dir)]}, separators=(',', ':'))


                        else:
                            return json.dumps({'actions': [('move',assx ,assy,dir),('move',assx+1 ,assy,dir)]}, separators=(',', ':'))
                    if assx >kingx:
                        dir='N'
                        for knight in self.__actualpos['knights']:
                            knightx=self.__actualpos['knights'][knight]['x']
                            knighty=self.__actualpos['knights'][knight]['y']


                            if knightx==(assx-1) and knighty==assy:
                                print('killed the knight in',knightx,knighty)
                                state['people'][knightx][knighty] = None
                                self.__actualpos['knights'].pop(knight,None)
                                return json.dumps({'actions': [('reveal',assx,assy),('kill',assx ,assy,dir)]}, separators=(',', ':'))

                        if kingx==assx+1 and kingy==assy and state['people'][assx][assy]!='assassin':
                            return json.dumps({'actions': [('reveal',assx,assy),('attack',assx ,assy,dir)]}, separators=(',', ':'))
                        if kingx==assx+1 and kingy==assy and state['people'][assx][assy]=='assassin':
                            return json.dumps({'actions': [('attack',assx ,assy,dir)]}, separators=(',', ':'))

                        for person in self.__actualpos['plebs']:
                            personx=self.__actualpos['plebs'][person]['x']
                            persony=self.__actualpos['plebs'][person]['y']

                            if personx==(assx-1) and persony==assy:
                                return json.dumps({'actions': [('move',assx ,assy,'W'),('move',assx ,assy,dir)]}, separators=(',', ':'))


                        else:
                            return json.dumps({'actions': [('move',assx ,assy,dir),('move',assx-1 ,assy,dir)]}, separators=(',', ':'))

            if self._playernb == 1:
                ikn=1

                for i in range(10):
                    for j in range(10):
                        if state['people'][i][j] == 'king':
                            self.__actualpos['king'] = dict()
                            self.__actualpos['king']['x'] = i
                            self.__actualpos['king']['y'] = j
                        if state['people'][i][j] == 'knight':

                            self.__actualpos['knights']['knight' + str(ikn)] = dict()
                            self.__actualpos['knights']['knight' + str(ikn)]['x'] = i
                            self.__actualpos['knights']['knight' + str(ikn)]['y'] = j
                            ikn += 1
                        else:
                            if state['people'][i][j]!='king' and state['people'][i][j]!='assassin' and state['people'][i][j]!='knight'and state['people'][i][j]!=None:

                                self.__actualpos['plebs'][state['people'][i][j]] = dict()
                                self.__actualpos['plebs'][state['people'][i][j]]['x'] = i
                                self.__actualpos['plebs'][state['people'][i][j]]['y'] = j
                kingx=self.__actualpos['king']['x']
                kingy=self.__actualpos['king']['y']
                knight1x=self.__actualpos['knights']['knight1']['x']
                knight1y=self.__actualpos['knights']['knight1']['y']
                knight2x=self.__actualpos['knights']['knight2']['x']
                knight2y=self.__actualpos['knights']['knight2']['y']
                knight3x=self.__actualpos['knights']['knight3']['x']
                knight3y=self.__actualpos['knights']['knight3']['y']
                knight4x=self.__actualpos['knights']['knight4']['x']
                knight4y=self.__actualpos['knights']['knight4']['y']
                knight5x=self.__actualpos['knights']['knight5']['x']
                knight5y=self.__actualpos['knights']['knight5']['y']
                knight6x=self.__actualpos['knights']['knight6']['x']
                knight6y=self.__actualpos['knights']['knight6']['y']
                knight7x=self.__actualpos['knights']['knight7']['x']
                knight7y=self.__actualpos['knights']['knight7']['y']

                if kingx>8 and kingy>8:

                    return json.dumps({'actions': [('move',knight7x ,knight7y,'W'),('move',kingx ,kingy,'W'),('move',knight3x ,knight3y,'N'),('move',knight5x ,knight5y,'N'),('move',kingx ,kingy-1,'N'),('move',knight7x ,knight7y-1,'E')]}, separators=(',', ':'))
                else:
                    if (kingy) < 2:
                        dir='E'
                        for knight in self.__actualpos['knights']:
                            knightx=self.__actualpos['knights'][knight]['x']
                            knighty=self.__actualpos['knights'][knight]['y']
                            for villager in self.__actualpos['plebs']:
                                villx=self.__actualpos['plebs'][villager]['x']
                                villy=self.__actualpos['plebs'][villager]['y']
                                if knightx==villx and knighty+1==villy:
                                    state['people'][villx][villy] = None
                                    self.__actualpos['plebs'].pop(villager,None)
                                    return json.dumps({'actions': [('arrest',knightx,knighty,dir),('move',knight6x ,knight6y,dir),('move',kingx ,kingy,dir),('move',knight3x ,knight3y,dir),('move',knight4x ,knight4y,dir),('move',knight5x ,knight5y,dir),('move',knight7x ,knight7y,dir)]}, separators=(',', ':'))
                                if kingx==villx and kingy+1==villy:
                                    ndir='N'
                                    return json.dumps({'actions': [('move',kingx ,kingy,ndir),('move',kingx ,kingy,dir)]}, separators=(',', ':'))

                            for assassin in self.__actualpos['assassins']:
                                assx=self.__actualpos['assassins'][assassin]['x']
                                assxy=self.__actualpos['assassins'][assassin]['y']
                                if knightx==assx and knighty+1==assy:
                                    state['people'][villx][villy] = None
                                    self.__actualpos['plebs'].pop(villager,None)
                                    return json.dumps({'actions': [('kill',knightx,knighty,dir),('move',knight6x ,knight6y,dir),('move',kingx ,kingy,dir),('move',knight3x ,knight3y,dir),('move',knight4x ,knight4y,dir),('move',knight5x ,knight5y,dir),('move',knight7x ,knight7y,dir)]}, separators=(',', ':'))





                        return json.dumps({'actions': [('move',knight6x ,knight6y,dir),('move',kingx,kingy,dir),('move',knight3x ,knight3y,dir),('move',knight4x ,knight4y,dir),('move',knight5x ,knight5y,dir),('move',knight7x ,knight7y,dir)]}, separators=(',', ':'))


                    if kingy > 2:
                        dir='W'
                        for knight in self.__actualpos['knights']:
                            knightx=self.__actualpos['knights'][knight]['x']
                            knighty=self.__actualpos['knights'][knight]['y']
                            for villager in self.__actualpos['plebs']:
                                villx=self.__actualpos['plebs'][villager]['x']
                                villy=self.__actualpos['plebs'][villager]['y']
                                if knightx==villx and knighty-1==villy:
                                    state['people'][villx][villy] = None
                                    self.__actualpos['plebs'].pop(villager,None)
                                    print('try to arrest',villager,'by',knightx,knighty)

                                    return json.dumps({'actions': [('arrest',knightx,knighty,dir),('move',knight5x ,knight5y,dir),('move',kingx ,kingy,dir),('move',knight4x ,knight4y,dir),('move',knight3x ,knight3y,dir),('move',knight6x ,knight6y,dir),('move',knight7x ,knight7y,dir)]}, separators=(',', ':'))
                                if kingx==villx and kingy-1==villy:
                                    ndir='N'
                                    return json.dumps({'actions': [('move',kingx ,kingy,ndir),('move',kingx ,kingy,dir)]}, separators=(',', ':'))

                            for assassin in self.__actualpos['assassins']:
                                assx=self.__actualpos['assassins'][assassin]['x']
                                assxy=self.__actualpos['assassins'][assassin]['y']
                                if knightx==assx and knighty-1==assy:
                                    state['people'][villx][villy] = None
                                    self.__actualpos['plebs'].pop(villager,None)
                                    return json.dumps({'actions': [('kill',knightx,knighty,dir),('move',knight5x ,knight5y,dir),('move',kingx ,kingy,dir),('move',knight4x ,knight4y,dir),('move',kingx ,kingy,dir),('move',knight3x ,knight3y,dir),('move',knight6x ,knight6y,dir),('move',knight7x ,knight7y,dir)]}, separators=(',', ':'))




                        return json.dumps({'actions': [('move',knight5x ,knight5y,dir),('move',kingx ,kingy,dir),('move',knight3x ,knight3y,dir),('move',knight4x ,knight4y,dir),('move',knight6x ,knight6y,dir),('move',knight7x ,knight7y,dir)]}, separators=(',', ':'))



                    if kingx < 2:
                        dir='S'
                        for knight in self.__actualpos['knights']:
                            knightx=self.__actualpos['knights'][knight]['x']
                            knighty=self.__actualpos['knights'][knight]['y']
                            for villager in self.__actualpos['plebs']:
                                villx=self.__actualpos['plebs'][villager]['x']
                                villy=self.__actualpos['plebs'][villager]['y']
                                if knightx+1==villx and knighty==villy:
                                    state['people'][villx][villy] = None
                                    self.__actualpos['plebs'].pop(villager,None)
                                    return json.dumps({'actions': [('arrest',knightx,knighty,dir),('move',knight7x ,knight7y,dir),('move',kingx ,kingy,dir),('move',knight3x ,knight3y,dir),('move',knight4x ,knight4y,dir),('move',knight5x ,knight5y,dir),('move',knight6x ,knight6y,dir)]}, separators=(',', ':'))
                                if kingx+1==villx and kingy==villy:
                                    ndir='E'
                                    return json.dumps({'actions': [('move',kingx ,kingy,ndir),('move',kingx ,kingy,dir)]}, separators=(',', ':'))

                            for assassin in self.__actualpos['assassins']:
                                assx=self.__actualpos['assassins'][assassin]['x']
                                assxy=self.__actualpos['assassins'][assassin]['y']
                                if knightx+1==assx and knighty==assy:
                                    state['people'][villx][villy] = None
                                    self.__actualpos['plebs'].pop(villager,None)
                                    return json.dumps({'actions': [('kill',knightx,knighty,dir),('move',knight7x ,knight7y,dir),('move',kingx ,kingy,dir),('move',knight3x ,knight3y,dir),('move',knight4x ,knight4y,dir),('move',knight5x ,knight5y,dir),('move',knight6x ,knight6y,dir)]}, separators=(',', ':'))




                        return json.dumps({'actions': [('move',knight7x ,knight7y,dir),('move',kingx ,kingy,dir),('move',knight3x ,knight3y,dir),('move',knight4x ,knight4y,dir),('move',knight5x ,knight5y,dir),('move',knight6x ,knight6y,dir)]}, separators=(',', ':'))

                    if kingx >2:
                        dir='N'
                        for knight in self.__actualpos['knights']:
                            knightx=self.__actualpos['knights'][knight]['x']
                            knighty=self.__actualpos['knights'][knight]['y']
                            for villager in self.__actualpos['plebs']:
                                villx=self.__actualpos['plebs'][villager]['x']
                                villy=self.__actualpos['plebs'][villager]['y']
                                if knightx-1==villx and knighty==villy:
                                    state['people'][villx][villy] = None
                                    self.__actualpos['plebs'].pop(villager,None)
                                    print('try to arrest ',villx,villy,'by',knightx,knighty)
                                    return json.dumps({'actions': [('arrest',knightx,knighty,dir),('move',knight3x ,knight3y,dir),('move',knight5x ,knight5y,dir),('move',knight4x ,knight4y,dir),('move',kingx,kingy,dir),('move',knight6x ,knight6y,dir),('move',knight7x ,knight7y,dir)]}, separators=(',', ':'))
                                if kingx-1==villx and kingy==villy:
                                    ndir='E'
                                    return json.dumps({'actions': [('move',kingx ,kingy,ndir),('move',kingx ,kingy,dir)]}, separators=(',', ':'))

                            for assassin in self.__actualpos['assassins']:
                                assx=self.__actualpos['assassins'][assassin]['x']
                                assxy=self.__actualpos['assassins'][assassin]['y']
                                if knightx-1==assx and knighty==assy:
                                    state['people'][villx][villy] = None
                                    self.__actualpos['plebs'].pop(villager,None)
                                    return json.dumps({'actions': [('kill',knightx,knighty,dir),('move',knight3x ,knight3y,dir),('move',knight5x ,knight5y,dir),('move',kingx ,kingy,dir),('move',knight4x ,knight4y,dir),('move',knight6x ,knight6y,dir),('move',knight7x ,knight7y,dir)]}, separators=(',', ':'))




                        return json.dumps({'actions': [('move',knight3x ,knight3y,dir),('move',knight5x ,knight5y,dir),('move',kingx ,kingy,dir),('move',knight4x ,knight4y,dir),('move',knight6x ,knight6y,dir),('move',knight7x ,knight7y,dir)]}, separators=(',', ':'))

            else:
                return json.dumps({'actions': []}, separators=(',', ':'))


if __name__ == '__main__':
    # Create the top-level parser
    parser = argparse.ArgumentParser(description='King & Assassins game')
    subparsers = parser.add_subparsers(
        description='server client',
        help='King & Assassins game components',
        dest='component'
    )

    # Create the parser for the 'server' subcommand
    server_parser = subparsers.add_parser('server', help='launch a server')
    server_parser.add_argument('--host', help='hostname (default: localhost)', default='localhost')
    server_parser.add_argument('--port', help='port to listen on (default: 5000)', default=5000)
    server_parser.add_argument('-v', '--verbose', action='store_true')
    # Create the parser for the 'client' subcommand
    client_parser = subparsers.add_parser('client', help='launch a client')
    client_parser.add_argument('name', help='name of the player')
    client_parser.add_argument('--host', help='hostname of the server (default: localhost)',
                               default=socket.gethostbyname(socket.gethostname()))
    client_parser.add_argument('--port', help='port of the server (default: 5000)', default=5000)
    client_parser.add_argument('-v', '--verbose', action='store_true')
    # Parse the arguments of sys.args
    args = parser.parse_args()

    if args.component == 'server':
        KingAndAssassinsServer(verbose=args.verbose).run()
    else:
        KingAndAssassinsClient(args.name, (args.host, args.port), verbose=args.verbose)
