import curses
import logging
import chess

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


class HelpPane(Widget):
    def __init__(self, parent, state):
        super().__init__(parent, state, 4, 39, 1, 14)

    def Draw(self):
        self.win.addstr(0, 0, "(Tab) to flip the board")
        self.win.addstr(1, 0, "(Shift+1) to force move")
        # self.win.addstr(2, 0, "(Shift+U) to undo the move")
        super().Draw()


class ChessBoard(Widget):
    def __init__(self, parent, state):
        super().__init__(parent, state, 3 * 8 + 1, 5 * 8 + 1, 4, 1)

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
            self.win.addstr(row + 1, col, ' ' + val + ' ',
                            attr + curses.A_BOLD)
            self.win.addstr(row + 2, col, ' ' * 5, attr)

            if cell in self.state['lastmove']:
                self.win.addstr(row + 0, col, '+---+', curses.color_pair(10))
                self.win.addstr(row + 1, col, '|', curses.color_pair(10))
                self.win.addstr(row + 1, col + 4, '|', curses.color_pair(10))
                self.win.addstr(row + 2, col, '+---+', curses.color_pair(10))

            if cell in [
                    self.state['nextmove'][0:2],
                    self.state['nextmove'][2:4],
            ]:
                self.win.addstr(row + 0, col + 1, '---', curses.color_pair(11))
                self.win.addstr(row + 1, col, '|', curses.color_pair(11))
                self.win.addstr(row + 1, col + 4, '|', curses.color_pair(11))
                self.win.addstr(row + 2, col + 1, '---', curses.color_pair(11))

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
        super().Draw()

    def OnMouse(self, mouse):
        x = mouse[1] - self.win.getbegyx()[1]
        y = mouse[2] - self.win.getbegyx()[0]
        row = y // 3
        col = (x - 1) // 5
        if row < 0 or row >= 8 or col < 0 or col >= 8:
            return False
        ranks = 'abcdefgh'
        files = '12345678'
        rank = ranks[7 - col if self.state['flipped'] else col]
        file = files[row if self.state['flipped'] else 7 - row]
        square = rank + file

        side_to_move = self.state['board'].turn
        idx = chess.SQUARE_NAMES.index(square)
        piece = self.state['board'].piece_at(idx)

        if piece and piece.color == side_to_move:
            self.state['nextmove'] = square
        elif len(self.state['nextmove']) >= 2:
            self.state['nextmove'] = self.state['nextmove'][:2] + square

        return True

    def OnKey(self, key):
        if key == 9:  # Tab
            self.state['flipped'] = not self.state['flipped']
            return True
        if key == ord('!'):
            self.state['forcemove'] = True
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
        tim = self.state['timedsearch']
        if self.state['engine']:
            self.win.addstr("[ ACTIVE  ]", curses.color_pair(7))
        else:
            self.win.addstr("[ STOPPED ]", curses.color_pair(6))
        self.win.addstr("   (Shift+E) to start/stop")
        self.win.addstr(1, 0, "Status: ")
        self.win.addstr(self.state['enginestatus'][:50], curses.color_pair(9))
        self.win.clrtoeol()
        self.win.addstr(2, 0, "White (z): ")
        self.win.addstr(
            '[ timed  ]' if tim[0] else '[infinite]',
            curses.color_pair(7 if tim[0] != self.state['flipped'] else 6))
        self.win.addstr("   Black (x): ")
        self.win.addstr(
            '[ timed  ]' if tim[1] else '[infinite]',
            curses.color_pair(7 if tim[1] == self.state['flipped'] else 6))
        super().Draw()

    def OnKey(self, key):
        if key == ord('E'):
            self.state['engine'] = not self.state['engine']
            return True
        if key == ord('z'):
            self.state['timedsearch'][0] = not self.state['timedsearch'][0]
            return True
        if key == ord('x'):
            self.state['timedsearch'][1] = not self.state['timedsearch'][1]
            return True


class Promotions(Widget):
    def __init__(self, parent, state):
        super().__init__(parent, state, 4, 39, 32, 1)

    def Draw(self):
        prom = self.state['promotion']
        self.win.addstr(0, 0, "Promote to: ")
        self.win.addstr(1, 0, "[ Queen (Shift+Q) ]",
                        curses.color_pair(7 if prom == 'Q' else 0))
        self.win.addstr("[ Knight (Shift+N) ]",
                        curses.color_pair(6 if prom == 'N' else 0))
        self.win.addstr(2, 0, "[ Rook  (Shift+R) ]",
                        curses.color_pair(6 if prom == 'R' else 0))
        self.win.addstr("[ Bishop (Shift+B) ]",
                        curses.color_pair(6 if prom == 'B' else 0))
        super().Draw()

    def OnKey(self, key):
        for x in 'QBNR':
            if key == ord(x):
                self.state['promotion'] = x
                return True

    def OnMouse(self, mouse):
        x = mouse[1] - self.win.getbegyx()[1]
        y = mouse[2] - self.win.getbegyx()[0]
        if y == 1:
            self.state['promotion'] = 'Q' if x < 19 else 'N'
        if y == 2:
            self.state['promotion'] = 'R' if x < 19 else 'B'
        return True


class Info(Widget):
    def __init__(self, parent, state):
        super().__init__(parent, state, 30, 60, 5, 80)

    def Draw(self):
        self.win.addstr(0, 0, "Depth Score   Nps     Nodes   Pv ",
                        curses.color_pair(9))

        infos = self.state['info']
        for i in range(len(infos)):
            info = infos[i]

            if info is None:
                st = '=' * 55
            else:
                st = "%2d/%2d %5d %7d %9d %s" % (
                    info['depth'], info['seldepth'], info['cp'], info['nps'],
                    info['nodes'], ' '.join([str(x) for x in info['pv'][1]]))

            self.win.addstr(i + 1, 0, st[:55])
        super().Draw()


class MoveInput(Widget):
    def __init__(self, parent, state):
        super().__init__(parent, state, 2, 39, 30, 1)

    def Draw(self):
        self.win.addstr(1, 15, "(Enter) to commit move.")
        self.win.addstr(0, 0, "Enter move (e.g. e2e4 or h2h1n): ",
                        curses.color_pair(9))
        self.win.addstr(self.state['nextmove'], curses.color_pair(10))
        self.win.clrtoeol()
        super().Draw()

    def OnKey(self, key):
        st = self.state['nextmove']
        if key == 127:  # Backspace
            self.state['nextmove'] = self.state['nextmove'][:-1]
            return True
        if key == 10 and len(st) >= 4:
            self.state['commitmove'] = True
        if len(st) in [0, 2]:
            for x in 'abcdefgh':
                if key == ord(x):
                    self.state['nextmove'] += x
                    return True
            return False
        if len(st) in [1, 3]:
            for x in '12345678':
                if key == ord(x):
                    self.state['nextmove'] += x
                    return True
            return False
        if len(st) in [4]:
            for x in 'qnkb':
                if key == ord(x):
                    self.state['nextmove'] += x
                    return True
            return False
        return False


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
        curses.init_pair(7, 15, 2)  # [OK]
        curses.init_pair(8, 9, 0)  # Logo
        curses.init_pair(9, 231, 0)  # Bright white on black
        curses.init_pair(10, 10, 16)  # Past move from/to marker, move text
        curses.init_pair(11, 9, 4)  # Move selector from/to marker

        curses.halfdelay(1)
        self.scr.clear()

        self.widgets = [
            Logo(stdscr, state),
            HelpPane(stdscr, state),
            ChessBoard(stdscr, state),
            StatusBar(stdscr, state),
            Engine(stdscr, state),
            Info(stdscr, state),
            Promotions(stdscr, state),
            MoveInput(stdscr, state),
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
