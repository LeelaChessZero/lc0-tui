#!/usr/bin/env python3

import os.path
import logging
import chess
import chess.engine
import chess.polyglot
import curses
import datetime
import pickle
import threading
from wccc.tui import Tui
from wccc.config import *

MULTIPV = 12
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

LOG_FORMAT = ('%(levelname).1s%(asctime)s.%(msecs)03d %(name)s '
              '%(filename)s:%(lineno)d] %(message)s')
LOG_DATE_FORMAT = '%m%d %H:%M:%S'

LOCK = threading.Lock()


class Controller:

    def __init__(self):
        os.chdir(LC0_DIRECTORY)
        logging.info("Starting engine %s" % repr(COMMAND_LINE))
        self.engine = chess.engine.SimpleEngine.popen_uci(
            COMMAND_LINE, timeout=20)  # , stderr=subprocess.DEVNULL)
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
                'move_info': [],
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
                'autocommitenabled': True,
                'movenotify': False,
                'piecedisplay': 0,
                'drift_compensation': round(INCREMENT) / 2,
            }
        self.state['lasttimestamp'] = datetime.datetime.now()
        self.state['thinking'] = {}
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
            self.state['timerenabled'] = False
            self.state['engine'] = False
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
                    self.state['timer'][idx] += self.GetIncrement(
                        self.state['board'].turn)
                    self.state['board'].push(entry.move)
                    self.state['move_info'].append('Still theory.')
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
                white_clock=self.state['timer'][0],
                black_clock=self.state['timer'][1],
                white_inc=self.GetIncrement(chess.WHITE),
                black_inc=self.GetIncrement(chess.BLACK))
            logging.info("Searching with time limit: %s" % str(limit))
            self.state['enginestatus'] = "go w %d+%d b %d+%d" % tuple(
                int(x * 1000) for x in [
                    self.state['timer'][0],
                    self.GetIncrement(chess.WHITE), self.state['timer'][1],
                    self.GetIncrement(chess.BLACK)
                ])
        else:
            self.state['enginestatus'] = "go infinite"

        logging.info(f"Starting search, board=[{board.fen()}] limit={limit}")
        self.search = self.engine.analysis(board=board,
                                           limit=limit,
                                           multipv=MULTIPV)

    def GetIncrement(self, white_color):
        if self.state['timedsearch'][0] == self.state['timedsearch'][1]:
            return INCREMENT
        if (white_color == chess.WHITE) == self.state['timedsearch'][0]:
            return max(0, INCREMENT - self.state['drift_compensation'])
        else:
            return min(2 * INCREMENT,
                       INCREMENT + self.state['drift_compensation'])

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
            self.state['move_info'].append(self.GetBestWdl())
            self.state['thinking'] = {}
        except:
            logging.exception("Bad move: %s" % nextmove)
            return

        self.state['timer'][idx] += self.GetIncrement(
            not self.state['board'].turn)
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
                self.state['movetimer'][1 - idx] = 0
                self.state['board'].pop()
                self.state['move_info'].pop()
                self.state['nextmove'] = ''
                self.state['thinking'] = {}

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
                     ) / datetime.timedelta(seconds=1)
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
                thinking['curr'] = {"time": info['time'], "moves": {}, "pv":[]}
            for key in ['nps', 'depth', 'seldepth']:
                if key in info:
                    self.state[key] = info[key]
            if not info.get('pv', None):
                continue
            if info.get('multipv', 1) == 1:
                thinking['curr']['pv'] = info['pv']
            move = info['pv'][0].uci()
            thinking['curr']['moves'][move] = {
                'score': info['score'].white() if 'score' in info else None,
                'wdl': info['wdl'].white() if 'wdl' in info else None,
                'nodes': info.get('nodes', 0),
            }

    def GetBestWdl(self):
        if 'curr' not in self.state['thinking']: return "(unknown)"
        if not self.state['thinking']['curr'].get('moves'):
            return "(unknown)"
        return max(self.state['thinking']['curr']['moves'].values(),
                   key=lambda x: x['nodes']).get('wdl', '(unknown)')

    def UpdateOnSearchDone(self):
        if not self.search:
            return

        if not self.search.inner._finished.done():
            return

        self.UpdateSearchInfo()
        curses.flash()
        curses.beep()
        self.state['moveready'] = True
        idx = 0 if self.state['board'].turn else 1
        self.state['timer'][idx] += self.GetIncrement(self.state['board'].turn)
        self.state['movetimer'][1 - idx] = 0
        best_move = self.search.wait()
        self.state['board'].push(best_move.move)
        self.state['move_info'].append(self.GetBestWdl())
        self.state['nextmove'] = ''
        self.state['thinking'] = {}
        self.state['enginestatus'] = "Stopped."
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
        filename=os.path.join(LOGS_DIR, f'wccc-{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}.log'),
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
