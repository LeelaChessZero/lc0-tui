#!/bin/env python3

import os.path
import logging
import chess
import chess.uci
import curses
import datetime
import pickle
from wccc.tui import Tui

############################################################################
# Config
############################################################################

LC0_DIRECTORY = '/home/crem/dev/lc0/build/debugoptimized'
COMMAND_LINE = [
    './lc0',
    '--verbose-move-stats',  # Please keep it! Adds useful data into logs.
    '--move-overhead=10000',  # 10 seconds move overhead. Recommended to keep it.
    '--threads=8',
    '--cpuct=3.02',
    '--fpu-reduction=0.52',
    '--policy-softmax-temp=1.68',
    '--backend=multiplexing',
    '--minibatch-size=128',
    ('--backend-opts='
     '(backend=cudnn-fp16,gpu=0),'
     '(backend=cudnn-fp16,gpu=1),'
     '(backend=cudnn-fp16,gpu=2),'
     '(backend=cudnn-fp16,gpu=3),'
     '(backend=cudnn-fp16,gpu=4),'
     '(backend=cudnn-fp16,gpu=5),'
     '(backend=cudnn-fp16,gpu=6),'
     '(backend=cudnn-fp16,gpu=7)'),
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
            self.dic['info'] = [self.info.copy()] + self.dic['info'][:27]
        super().post_info()


class Controller:
    def __init__(self):
        os.chdir(LC0_DIRECTORY)
        logging.info("Starting engine %s" % repr(COMMAND_LINE))
        self.engine = chess.uci.popen_engine(
            COMMAND_LINE)  #, stderr=subprocess.DEVNULL)
        self.engine.uci()
        logging.info("Engine name: %s" % self.engine.name)
        print("Initializing engine...")
        self.engine.ucinewgame()
        self.search = None

        try:
            self.state = {}
            with open(os.path.join(DATA_DIR, 'state.bin'), 'rb') as f:
                self.state = pickle.load(f)
        except:
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
                'nextmove': '',
                'promotion': 'Q',
                'commitmove': False,
                'undo': False,
            }
        self.engine.info_handlers.append(InfoAppender(self.state))

    def SaveState(self):
        logging.info("Saving state")
        with open(os.path.join(DATA_DIR, 'state.bin'), 'wb') as f:
            pickle.dump(self.state, f)

    def StartSearch(self):
        if self.search:
            self.engine.stop()

        self.state['forcemove'] = False

        if not self.state['engine']:
            return

        if (self.state['board'].is_checkmate()
                or self.state['board'].is_stalemate()):
            logging.info("Terminal position, not searching")
            return

        logging.info("Starting search")
        self.SaveState()

        self.state['info'] = [None] + self.state['info'][:27]

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
        self.SaveState()
        nextmove = self.state['nextmove']
        if len(nextmove) == 4:
            from_sq = chess.SQUARE_NAMES.index(nextmove[:2])
            if (self.state['board'].piece_type_at(from_sq) == chess.PAWN
                    and nextmove[3] in '18'):
                nextmove += self.state['promotion'].lower()

        idx = 0 if self.state['board'].turn else 1
        logging.info("Manually adding move %s" % nextmove)
        try:
            self.state['board'].push_uci(nextmove)
        except:
            logging.exception("Bad move: %s" % nextmove)
            return

        self.state['timer'][idx] += INCREMENT_MS
        self.state['movetimer'][1 - idx] = 0
        self.state['nextmove'] = ''
        self.StartSearch()

    def Update(self):
        if self.state['undo']:
            logging.info("Undo move")
            self.state['undo'] = False
            self.SaveState()
            if self.state['board'].move_stack:
                idx = 0 if self.state['board'].turn else 1
                self.state['timer'][1 - idx] -= INCREMENT_MS
                self.state['movetimer'][1 - idx] = 0
                self.state['board'].pop()
                self.state['nextmove'] = ''

                self.StartSearch()
        if self.state['commitmove']:
            self.CommitMove()
        if self.state['forcemove']:
            self.state['forcemove'] = False
            logging.info("Forcemove, sending stop")
            self.SaveState()
            self.engine.stop(async_callback=True)
        if self.state['engine'] and not self.search:
            self.StartSearch()
        if not self.state['engine'] and self.search:
            logging.info("Aborted search manually")
            self.engine.stop()
            self.search = None
            self.state['enginestatus'] = "Stopped."
            self.SaveState()

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
        self.state['nextmove'] = ''
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
