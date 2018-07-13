import curses
from enum import Enum
import logging

PIECES_UNICODE = '♙♘♗♖♕♔'
PIECES_STR = 'PNBRQK'

# Colors:
# Default = 0
# WhiteOnDark = 1
# WhiteOnBright = 2
# BlackOnDark = 3
# BlackOnBright = 4


class Widget:
    def __init__(self, parent, state, rows, cols, row, col):
        self.state = state
        self.win = parent.subwin(rows, cols, row, col)

    def Draw(self):
        self.win.noutrefresh()

    def OnKey(self, key):
        return False

    def OnMouse(self, mouse):
        return False


class ChessBoard(Widget):
    def __init__(self, parent, state):
        super().__init__(parent, state, 3 * 8 + 2, 5 * 8 + 1, 5, 1)

    def Draw(self):
        flipped = self.state['flipped']

        def DrawCell(cell):
            rank_idx = ord(cell[0]) - ord('a')
            file_idx = ord(cell[1]) - ord('1')
            is_dark = rank_idx % 2 == file_idx % 2

            idx = file_idx * 8 + rank_idx
            piece = self.state['board'].piece_at(idx)
            color = piece is not None and piece.color

            if piece:
                val = (PIECES_UNICODE[piece.piece_type - 1] + ' ' +
                       PIECES_STR[piece.piece_type - 1])
            else:
                val = '   '

            if color:
                attr = curses.color_pair(1 if is_dark else 2)
            else:
                attr = curses.color_pair(3 if is_dark else 4)

            row = (file_idx if flipped else 7 - file_idx) * 3
            col = (7 - rank_idx if flipped else rank_idx) * 5 + 1

            self.win.addstr(row + 0, col, ' ' * 5, attr)
            self.win.addstr(row + 1, col, ' ' + val + ' ', attr)
            self.win.addstr(row + 2, col, ' ' * 5, attr)

        self.win.erase()
        files = '12345678'
        ranks = 'hgfedcba'

        for i in range(8):
            idx = i if flipped else 7 - i
            self.win.addstr(i * 3 + 1, 0, files[idx], curses.color_pair(0))
            self.win.addstr(8 * 3, i * 5 + 3, ranks[idx], curses.color_pair(0))

        for rank in ranks:
            for file in files:
                DrawCell(rank + file)

        self.win.addstr(8 * 3 + 1, 0, "(Tab) to flip the board")

        super().Draw()

    def OnKey(self, key):
        if key == 9:  # Tab
            self.state['flipped'] = not self.state['flipped']
            return True


class StatusBar(Widget):
    def __init__(self, parent, state):
        super().__init__(parent, state, 1, 140, 35, 0)

    def Draw(self):
        self.win.bkgdset(' ', curses.color_pair(5))
        self.win.addstr(0, 0, " %-138s" % self.state['statusbar'])
        self.win.noutrefresh()
        super().Draw()


class Logo(Widget):
    def __init__(self, parent, state):
        super().__init__(parent, state, 3, 10, 0, 2)

    def Draw(self):
        self.win.addstr(0, 0, "       _", curses.color_pair(8))
        self.win.addstr(1, 0, "|   _ | |", curses.color_pair(8))
        self.win.addstr(2, 0, "|_ |_ |_|", curses.color_pair(8))
        super().Draw()


class Engine(Widget):
    def __init__(self, parent, state):
        super().__init__(parent, state, 4, 60, 1, 80)

    def Draw(self):
        self.win.addstr(0, 0, "Engine: ")
        if self.state['engine']:
            self.win.addstr("[ ACTIVE  ]", curses.color_pair(7))
        else:
            self.win.addstr("[ STOPPED ]", curses.color_pair(6))
        self.win.addstr("   (E) to start/stop")
        self.win.addstr(1, 0, "Status: ")
        self.win.addstr(self.state['enginestatus'][:50], curses.color_pair(9))
        self.win.clrtoeol()
        super().Draw()

    def OnMouse(self, mouse):
        self.state['engine'] = not self.state['engine']
        return True

    def OnKey(self, key):
        if key == ord('E'):
            self.state['engine'] = not self.state['engine']
            return True


class Info(Widget):
    def __init__(self, parent, state):
        super().__init__(parent, state, 30, 60, 4, 80)

    def Draw(self):
        self.win.addstr(0, 0, "Depth Score   Nps     Nodes   Pv ",
                        curses.color_pair(9))

        infos = self.state['info']
        for i in range(len(infos)):
            info = infos[i]
            score = info['score'][1].cp
            if not self.state['board'].turn:
                score = -score

            st = "%2d/%2d %5d %7d %9d %s" % (
                info['depth'], info['seldepth'], score, info['nps'],
                info['nodes'], ' '.join([str(x) for x in info['pv'][1]]))

            self.win.addstr(i + 1, 0, st[:55])
        super().Draw()


class Tui:
    def __init__(self, stdscr, state):
        self.state = state
        self.scr = stdscr
        curses.mousemask(curses.BUTTON1_CLICKED)
        curses.init_pair(1, 15, 94)  # White piece on dark square
        curses.init_pair(2, 15, 172)  # White on bright
        curses.init_pair(3, 16, 94)  # Black on dark
        curses.init_pair(4, 16, 172)  # Black on bright
        curses.init_pair(5, 16, 12)  # Status bar
        curses.init_pair(6, 15, 9)  # [FAIL]
        curses.init_pair(7, 15, 10)  # [OK]
        curses.init_pair(8, 9, 0)  # Logo
        curses.init_pair(9, 231, 0)  # Bright white on black

        curses.halfdelay(1)
        self.scr.clear()

        self.widgets = [
            Logo(stdscr, state),
            ChessBoard(stdscr, state),
            StatusBar(stdscr, state),
            Engine(stdscr, state),
            Info(stdscr, state),
        ]

    def Draw(self):
        for x in self.widgets:
            try:
                x.Draw()
            except curses.error:
                logging.exception("Unable to draw widget: %s" % repr(x))
        curses.doupdate()

    def Process(self):
        x = self.scr.getch()
        if x == -1:
            return
        if x == curses.KEY_MOUSE:
            try:
                mouse = curses.getmouse()
            except curses.error:
                return
            for x in self.widgets:
                if x.win.enclose(mouse[2], mouse[1]) and x.OnMouse(mouse):
                    return
        else:
            for y in self.widgets:
                if y.OnKey(x):
                    return
