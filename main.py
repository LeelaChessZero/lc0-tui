#!/usr/bin/env python3

import os.path
import logging
import chess
import chess.engine
import chess.polyglot
import curses
import datetime
import pickle
import copy
import threading
from wccc.tui import Tui

############################################################################
# Config
############################################################################

#LC0_DIRECTORY = '/home/fhuizing/Workspace/chess/lc0/build/release'
LC0_DIRECTORY = '/home/crem/dev/lc0.wt0/build/release'

MULTIPV = 12

COMMAND_LINE = [
    './lc0',
    #'--backend=trivial',
    '--backend=cuda',
    '--show-wdl',
    '--show-movesleft',
    f'--logfile={os.path.abspath(".")}/data/lc0.log',
    '--per-pv-counters',
    '--preload',
    # '--multipv=7',
    # '--score-type=win_percentage',
    # '--weights=/home/fhuizing/Workspace/chess/wccc-tui/data/11248.pb.gz',
    # '--threads=6',
    # '--minibatch-size=256',
    # '--max-collision-events=32',
    # '--nncache=10000000',
    # '--logfile=/home/fhuizing/Workspace/chess/wccc-tui/data/lc0.log',
    # '--backend=multiplexing',
    # '--verbose-move-stats',
    # ('--backend-opts='
    #  '(backend=cudnn,gpu=0),'
    #  '(backend=cudnn,gpu=1),'
    #  ),
    # '--cpuct=3.8'
]

START_TIME = 105 * 60 * 1000
INCREMENT_MS = 30000
OPENING_BOOK = None  # "WCCCbook.bin"

############################################################################

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

LOG_FORMAT = ('%(levelname).1s%(asctime)s.%(msecs)03d %(name)s '
              '%(filename)s:%(lineno)d] %(message)s')
LOG_DATE_FORMAT = '%m%d %H:%M:%S'

LOCK = threading.Lock()

class Controller:

    def __init__(self):
        os.chdir(LC0_DIRECTORY)
        logging.info("Starting engine %s" % repr(COMMAND_LINE))
        self.engine = chess.engine.SimpleEngine.popen_uci(
            COMMAND_LINE)  # , stderr=subprocess.DEVNULL)
        logging.info(f"Engine name: {self.engine.id['name']}")
        print("Initializing engine...")
        self.search = None
        self.opening_book = None
        if OPENING_BOOK:
            self.opening_book = chess.polyglot.open_reader(
                os.path.join(BASE_DIR, OPENING_BOOK))

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
                'moveready': False,
                'nextmove': '',
                'promotion': 'Q',
                'commitmove': False,
                'undo': False,
                'nps': 0,
                'depth': 0,
                'seldepth': 0,
                'thinking': {}
            }
        self.state['lasttimestamp'] = datetime.datetime.now()
        # self.engine.info_handlers.append(InfoAppender(self.state))

    def SaveState(self):
        logging.info("Saving state")
        with open(os.path.join(DATA_DIR, 'state.bin'), 'wb') as f:
            pickle.dump(self.state, f)

    def StopSearch(self):
        if self.search:
            self.search.stop()

    def StartSearch(self):
        self.StopSearch()
        self.state['forcemove'] = False

        if not self.state['engine']:
            return

        if (self.state['board'].is_checkmate()
                or self.state['board'].is_stalemate()):
            logging.info("Terminal position, not searching")
            return

        logging.info("Starting search")
        self.SaveState()

        self.state['thinking'] = {}
        for key in ['nps', 'depth', 'seldepth']:
            self.state[key] = 0

        board = self.state['board']
        idx = 0 if board.turn else 1

        limit = None
        if self.state['timedsearch'][idx]:
            if self.opening_book:
                try:
                    entry = self.opening_book.weighted_choice(
                        self.state['board'])
                    logging.info("Opening book hit: %s" % str(entry.move))
                    idx = 0 if self.state['board'].turn else 1
                    self.state['board'].push(entry.move)
                    self.state['timer'][idx] += INCREMENT_MS
                    self.state['movetimer'][1 - idx] = 0
                    self.state['nextmove'] = ''
                    curses.flash()
                    curses.beep()
                    self.state['moveready'] = True
                    self.StartSearch()
                    return
                except IndexError:
                    pass

            limit = chess.engine.Limit(
                white_clock=self.state['timer'][0] / 1000.0,
                black_clock=self.state['timer'][1] / 1000.0,
                white_inc=INCREMENT_MS / 1000.0,
                black_inc=INCREMENT_MS / 1000.0)
            logging.info("Searching with time limit: %s" % str(limit))
            self.state['enginestatus'] = "go wtime %d btime %d" % tuple(
                self.state['timer'])
        else:
            self.state['enginestatus'] = "go infinite"

        logging.info(f"Starting search, board=[{board.fen()}] limit={limit}")
        self.search = self.engine.analysis(board=board,
                                           limit=limit,
                                           multipv=MULTIPV)

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
            self.StopSearch()
        if self.state['engine'] and not self.search:
            self.StartSearch()
        if not self.state['engine'] and self.search:
            logging.info("Aborted search manually")
            self.StopSearch()
            self.search = None
            self.state['enginestatus'] = "Stopped."
            self.SaveState()

    def UpdateTimer(self):
        newtime = datetime.datetime.now()
        if self.state['timerenabled']:
            idx = 0 if self.state['board'].turn else 1
            delta = (newtime - self.state['lasttimestamp']
                     ) / datetime.timedelta(milliseconds=1)
            self.state['timer'][idx] -= delta
            self.state['movetimer'][idx] += delta
        self.state['lasttimestamp'] = newtime

    def UpdateSearchInfo(self):
        if not self.search:
            return

        thinking = self.state['thinking']

        while not self.search.empty():
            info = self.search.get()
            if 'curr' not in thinking or info['time'] > thinking['curr'][
                    'time']:
                thinking['prev'] = thinking.get('curr', {'time': 0})
                thinking['curr'] = {"time": info['time'], "moves": {}}
            for key in ['nps', 'depth', 'seldepth']:
                if key in info:
                    self.state[key] = info[key]
            if not info.get('pv', None):
                continue
            move = info['pv'][0].uci()
            thinking['curr']['moves'][move] = {
                'score': info['score'].white() if 'score' in info else None,
                'wdl': info['wdl'].white() if 'wdl' in info else None,
                'nodes': info.get('nodes', 0),
            }

    def UpdateOnSearchDone(self):
        if not self.search:
            return

        return

        if not self.search.done():
            return

        curses.flash()
        curses.beep()
        self.state['moveready'] = True
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
            self.UpdateSearchInfo()
            self.UpdateOnSearchDone()


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
