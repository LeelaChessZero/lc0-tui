#!/bin/env python3

import os.path
import logging
import chess
import chess.uci
import subprocess
import curses
import datetime
from wccc.tui import Tui

############################################################################
# Config
############################################################################

LC0_DIRECTORY = '/home/crem/dev/lc0/build/debugoptimized'
COMMAND_LINE = [
    './lc0',
    '--verbose-move-stats',
    '--move-overhead=10000',
]

START_TIME = 115 * 60 * 1000
INCREMENT_MS = 15000

############################################################################

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

LOG_FORMAT = ('%(levelname).1s%(asctime)s.%(msecs)03d %(name)s '
              '%(filename)s:%(lineno)d] %(message)s')
LOG_DATE_FORMAT = '%m%d %H:%M:%S'


class InfoAppender(chess.uci.InfoHandler):
    def __init__(self, dic):
        self.dic = dic
        super().__init__()

    def post_info(self):
        self.info['cp'] = self.info['score'][1].cp

        #if not self.dic['board'].turn:
        #    self.info['cp'] = -self.info['cp']

        if not self.info.get('string'):
            self.dic['info'] = [self.info.copy()] + self.dic['info'][:25]
        super().post_info()


class Controller:
    def __init__(self):
        os.chdir(LC0_DIRECTORY)
        logging.info("Starting engine %s" % repr(COMMAND_LINE))
        self.engine = chess.uci.popen_engine(
            COMMAND_LINE, stderr=subprocess.DEVNULL)
        self.engine.uci()
        logging.info("Engine name: %s" % self.engine.name)
        print("Initializing engine...")
        self.engine.ucinewgame()

        self.state = {
            'board': chess.Board(),
            'flipped': False,
            'statusbar': "",
            'engine': False,
            'enginestatus': "Not doing anything",
            'timedsearch': [True, False],
            'timer': [START_TIME, START_TIME],
            'movetimer': [0, 0],
            'timerenabled': False,
            'lasttimestamp': None,
            'info': [],
            'forcemove': False,
            'lastmove': [],
            'nextmove': '',
            'promotion': 'Q',
            'commitmove': False,
            'undo': False,
        }
        self.engine.info_handlers.append(InfoAppender(self.state))

        self.search = None

    def StartSearch(self):
        if self.search:
            self.engine.stop()

        self.state['forcemove'] = False

        if not self.state['engine']:
            return

        self.state['info'] = [None] + self.state['info'][:25]

        board = self.state['board']
        idx = 0 if board.turn else 1
        self.engine.position(board)

        params = {}
        if self.state['timedsearch'][idx]:
            params['wtime'] = self.state['timer'][0]
            params['btime'] = self.state['timer'][1]
            params['winc'] = INCREMENT_MS
            params['binc'] = INCREMENT_MS
            self.state['enginestatus'] = "go wtime %d btime %d" % tuple(
                self.state['timer'])
        else:
            params['infinite'] = True
            self.state['enginestatus'] = "go infinite"

        logging.info("Starting search, params: %s" % repr(params))
        self.search = self.engine.go(async_callback=True, **params)

    def CommitMove(self):
        self.state['commitmove'] = False
        nextmove = self.state['nextmove']
        if len(nextmove) == 4:
            from_sq = chess.SQUARE_NAMES.index(nextmove[:2])
            if (self.state['board'].piece_type_at(from_sq) == chess.PAWN
                    and nextmove[3] in '18'):
                nextmove += self.state['promotion'].lower()

        idx = 0 if self.state['board'].turn else 1
        self.state['timer'][idx] += INCREMENT_MS
        self.state['movetimer'][1 - idx] = 0
        self.state['board'].push_uci(nextmove)
        self.state['lastmove'] = [nextmove[0:2], nextmove[2:4]]
        self.state['nextmove'] = ''
        self.StartSearch()

    def Update(self):
        if self.state['undo']:
            self.state['undo'] = False
            if self.state['board'].move_stack:
                idx = 0 if self.state['board'].turn else 1
                self.state['timer'][1 - idx] -= INCREMENT_MS
                self.state['movetimer'][1 - idx] = 0
                self.state['board'].pop()
                self.state['nextmove'] = ''
                if self.state['board'].move_stack:
                    self.state['lastmove'] = [
                        self.state['board'].peek().from_square,
                        self.state['board'].peek().to_square,
                    ]
                else:
                    self.state['lastmove'] = []

                self.StartSearch()
        if self.state['commitmove']:
            self.CommitMove()
        if self.state['forcemove']:
            self.engine.stop(async_callback=True)
            self.state['forcemove'] = False
        if self.state['engine'] and not self.search:
            self.StartSearch()
        if not self.state['engine'] and self.search:
            logging.info("Stopped search manually")
            self.engine.stop()
            self.search = None
            self.state['enginestatus'] = "Stopped."

    def UpdateTimer(self):
        if not self.state['timerenabled']:
            return
        newtime = datetime.datetime.now()
        idx = 0 if self.state['board'].turn else 1
        delta = (newtime - self.state['lasttimestamp']
                 ) / datetime.timedelta(milliseconds=1)
        self.state['timer'][idx] -= delta
        self.state['movetimer'][idx] += delta
        self.state['lasttimestamp'] = newtime

    def UpdateSearch(self):
        if not self.search:
            return

        if not self.search.done():
            return

        idx = 0 if self.state['board'].turn else 1
        self.state['timer'][idx] += INCREMENT_MS
        self.state['movetimer'][1 - idx] = 0
        self.state['board'].push(self.search.result().bestmove)
        self.state['lastmove'] = [
            chess.SQUARE_NAMES[x] for x in [
                self.search.result().bestmove.from_square,
                self.search.result().bestmove.to_square
            ]
        ]
        self.state['nextmove'] = ''
        logging.info(repr(self.state['lastmove']))
        self.search = None
        self.StartSearch()

    def Run(self, stdscr):
        self.tui = Tui(stdscr, self.state)
        while True:
            self.UpdateTimer()
            self.tui.Process()
            self.tui.Draw()
            self.Update()
            self.UpdateSearch()


def main():
    try:
        os.makedirs(DATA_DIR)
    except OSError:
        # Already exists
        pass

    logging.basicConfig(
        filename=os.path.join(DATA_DIR, 'wccc.log'),
        format=('%(levelname).1s%(asctime)s.%(msecs)03d %(name)s '
                '%(filename)s:%(lineno)d] %(message)s'),
        datefmt='%m%d %H:%M:%S',
        level=logging.DEBUG)
    logging.info('=' * 60 + ' Started!')

    controller = Controller()

    def Run(stdscr):
        controller.Run(stdscr)

    curses.wrapper(Run)


if __name__ == "__main__":
    main()
