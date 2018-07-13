#!/bin/env python3

import os.path
import logging
import chess
import chess.uci
import subprocess
import curses
from wccc.tui import Tui

############################################################################
# Config
############################################################################

LC0_DIRECTORY = '/home/crem/dev/lc0/build/debugoptimized'
COMMAND_LINE = [
    './lc0',
    '--verbose-move-stats',
]

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
        logging.info(repr(self.info))
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
            'statusbar': "Hi!",
            'engine': False,
            'enginestatus': "Not doing anything",
            'timedsearch': [False, False],
            'timer': [100000, 100000],
            'info': [],
        }
        self.engine.info_handlers.append(InfoAppender(self.state))

        self.search = None

    def StartSearch(self):
        if self.search:
            self.engine.stop()

        board = self.state['board']
        idx = 0 if board.turn else 1
        self.engine.position(board)

        params = {}
        if self.state['timedsearch'][idx]:
            params['wtime'] = self.state['timer'][0]
            params['btime'] = self.state['timer'][1]
            params['winc'] = 15000
            params['binc'] = 15000
            self.state['enginestatus'] = "go wtime %d btime %d" % tuple(
                self.state['timer'])
        else:
            params['infinite'] = True
            self.state['enginestatus'] = "go infinite"

        logging.info("Starting search, params: %s" % repr(params))
        self.search = self.engine.go(async_callback=True, **params)

    def Update(self):
        if self.state['engine'] and not self.search:
            self.StartSearch()
        if not self.state['engine'] and self.search:
            logging.info("Stopped search manually")
            self.engine.stop()
            self.search = None
            self.state['enginestatus'] = "Stopped."

    def Run(self, stdscr):
        self.tui = Tui(stdscr, self.state)
        while True:
            self.tui.Process()
            self.tui.Draw()
            self.Update()


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
