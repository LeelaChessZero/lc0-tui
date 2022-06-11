import curses
import logging
import chess
import datetime
from . import progressbar

#PIECES_UNICODE = '♙♘♗♖♕♔'
#PIECES_UNICODE = '♟♞♝♜♛♚'
#PIECES_STR = 'PNBRQK'

PIECES = [
    [
        (
            '   🭆🭑  ',
            '   🭖🭡  ',
            '  🬂🬂🬂🬂 ',
        ),
        (
            ' 🬷🬱🬺🬽  ',
            '🬁🬎🬍██🭀 ',
            '  🬋🬎🬎🬌🬃',
        ),
        (
            '   🭮🭬  ',
            '   🭨🭪  ',
            '  🬋🭚🭥🬋 ',
        ),
        (
            ' 🬦🬱🬹🬵🬓 ',
            ' 🭢🭩🭩🭩🭗 ',
            ' 🬍🬎🬎🬎🬌 ',
        ),
        (
            ' 🭀🭀🭋🭀🭋🭋',
            ' 🭐🭐🭅🭐🭅🭅',
            ' 🬍🬎🬎🬎🬎🬌',
        ),
        (
            '🬞🬹🬹🬘🬵🬹🬱',
            '🬁🬬█🬣🬬█🬆',
            ' 🬋🬌🬎🬌🬌🬃',
        ),
    ],
    [
        (
            '   ▄   ',
            '  ▝█▘  ',
            '  ▀▀▀  ',
        ),
        (
            ' ▟▚█▄  ',
            '▝▟▀██▙ ',
            '  ▄██▙▖',
        ),
        (
            '  ▗▙   ',
            '  ▗▙   ',
            ' ▗██▙  ',
        ),
        (
            ' █▙█▙█▌',
            ' ▐████ ',
            ' ▟████▖',
        ),
        (
            '▝▖▚▐▗▘▞',
            ' ▝▟▟▟▞ ',
            ' ▗▟██▄ ',
        ),
        (
            ' ▄▄▐▗▄▖',
            '▝▙▟▌█▄▛',
            ' ▗███▙ ',
        ),
    ],
    [
        ('o', 'T', '<_>'),
        (r'<`^\ ', ' /  )', '<_N_>'),
        (r'o', '(+)', '<_B_>'),
        (r'|UUU|', '| |', '<_R_>'),
        (r'.oOo.', r'\\\\|//', '<_Q_>'),
        (r'_+_', r'(_|_)', '<_K_>'),
    ],
    ['♙ P', '♘ N', '♗ B', '♖ R', '♕ Q', '♔ K'],
    ['pawn', 'kNight', 'Bishop', 'ROOK', 'QUEEN', 'KING'],
]

# Change thouse to 0..15 if youo have 16-color palette
BLACK_PIECES = 232  # 0
WHITE_PIECES = 15
DARK_SQUARES = 94  # 2
LIGHT_SQUARES = 172  # 3

SCREEN_WIDTH = 168
SCREEN_HEIGHT = 42

BLACK_BG = 237
DRAW_BG = 245
WHITE_BG = 231
BLACK_TEXT = 0
WHITE_TEXT = 231

# Colors:q
# Default = 0
# WhiteOnDark = 1
# WhiteOnBright = 2
# BlackOnDark = 3
# BlackOnBright = 4


def RoundDouble(x, digits):
    if x >= 10**digits:
        return str(int(x))
    res = str(x)[:digits]
    if res[-1] == '.':
        res = res[:-1]
    return res


def ShortenNum(num, max_len):
    max_num = 10**(max_len - 1)
    if num < max_num * 10:
        return RoundDouble(num, max_len)
    for s in 'KMBTQ':
        num /= 1000
        if num < max_num:
            return RoundDouble(num, max_len - 1) + s
    return 'inf'


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


class Background(Widget):

    def __init__(self, parent, state):
        super().__init__(parent, state, SCREEN_HEIGHT, SCREEN_WIDTH + 1, 0, 0)

    def Draw(self):
        if self.state['moveready']:
            self.win.bkgd(' ', curses.color_pair(18))
        else:
            self.win.bkgd(' ', curses.color_pair(0))
        super().Draw()


class HelpPane(Widget):

    def __init__(self, parent, state):
        super().__init__(parent, state, 10, 31, 34, 1)

    def Draw(self):
        self.win.addstr(
            0, 0, "(Shift+1) force\n(Shift+U) undo\n"
            "    (Tab) flip\n(Shift+V) view\n\n")
        self.win.addstr("\n Autocommit (Shift+A): ")
        if self.state['autocommitenabled']:
            self.win.addstr("[ ON  ]", curses.color_pair(7))
        else:
            self.win.addstr("[ OFF ]", curses.color_pair(6))
        self.win.addstr("\n     Notify (Shift+M): ")
        if self.state['movenotify']:
            self.win.addstr("[ ON  ]", curses.color_pair(6))
        else:
            self.win.addstr("[ OFF ]", curses.color_pair(7))

        super().Draw()

    def OnKey(self, key):
        if key == ord('A'):  # Shift+A
            self.state[
                'autocommitenabled'] = not self.state['autocommitenabled']
        elif key == ord('M'):  # Shift+M
            self.state['movenotify'] = not self.state['movenotify']
        elif key == ord('V'):  # Shift+V
            self.state['piecedisplay'] += 1
            if self.state['piecedisplay'] >= len(PIECES):
                self.state['piecedisplay'] = 0
        else:
            return False
        return True


class ChessBoard(Widget):
    CELL_WIDTH = 7
    CELL_HEIGHT = 3

    def __init__(self, parent, state):
        super().__init__(parent, state, self.CELL_HEIGHT * 8 + 1,
                         self.CELL_WIDTH * 8 + 1, 8, 1)

    def Draw(self):
        flipped = self.state['flipped']

        lastmove = []
        if self.state['board'].move_stack:
            lastmove = [
                chess.SQUARE_NAMES[x] for x in [
                    self.state['board'].peek().from_square,
                    self.state['board'].peek().to_square
                ]
            ]

        def DrawCell(cell):
            rank_idx = ord(cell[0]) - ord('a')
            file_idx = ord(cell[1]) - ord('1')
            is_dark = rank_idx % 2 == file_idx % 2

            idx = file_idx * 8 + rank_idx
            piece = self.state['board'].piece_at(idx)
            color = piece is not None and piece.color

            if piece:
                disp = PIECES[self.state['piecedisplay']][piece.piece_type - 1]
                if isinstance(disp, tuple):
                    (top, mid, bot) = (x.center(self.CELL_WIDTH) for x in disp)
                else:
                    top = bot = ' ' * self.CELL_WIDTH
                    mid = disp.center(7)
            else:
                top = mid = bot = ' ' * self.CELL_WIDTH

            if color:
                attr = curses.color_pair(1 if is_dark else 2)
            else:
                attr = curses.color_pair(3 if is_dark else 4)

            row = (file_idx if flipped else 7 - file_idx) * self.CELL_HEIGHT
            col = (7 - rank_idx if flipped else rank_idx) * self.CELL_WIDTH + 1

            self.win.addstr(row + 0, col, top, attr)
            self.win.addstr(row + 1, col, mid, attr + curses.A_BOLD)
            self.win.addstr(row + 2, col, bot, attr)

            if cell in lastmove:
                hor = '+' + '-' * (self.CELL_WIDTH - 2) + '+'
                self.win.addstr(row + 0, col, '┌─', curses.color_pair(11))
                self.win.addstr(row + 0, col + self.CELL_WIDTH - 2, '─┐',
                                curses.color_pair(11))
                self.win.addstr(row + 1, col, '│', curses.color_pair(11))
                self.win.addstr(row + 1, col + self.CELL_WIDTH - 1, '│',
                                curses.color_pair(11))
                self.win.addstr(row + 2, col, '└─', curses.color_pair(11))
                self.win.addstr(row + 2, col + self.CELL_WIDTH - 2, '─┘',
                                curses.color_pair(11))

            if cell in [
                    self.state['nextmove'][0:2],
                    self.state['nextmove'][2:4],
            ]:
                hor = '-' * (self.CELL_WIDTH - 2)
                self.win.addstr(row + 0, col + 1, '╱', curses.color_pair(10))
                self.win.addstr(row + 0, col + self.CELL_WIDTH - 2, '╲',
                                curses.color_pair(10))
                self.win.addstr(row + 1, col, '<', curses.color_pair(10))
                self.win.addstr(row + 1, col + self.CELL_WIDTH - 1, '>',
                                curses.color_pair(10))
                self.win.addstr(row + 2, col + 1, '╲', curses.color_pair(10))
                self.win.addstr(row + 2, col + self.CELL_WIDTH - 2, '╱',
                                curses.color_pair(10))

        self.win.erase()
        files = '12345678'
        ranks = 'hgfedcba'

        for i in range(8):
            idx = i if flipped else 7 - i
            self.win.addstr(i * self.CELL_HEIGHT + 1, 0, files[idx],
                            curses.color_pair(0))
            self.win.addstr(8 * self.CELL_HEIGHT,
                            i * self.CELL_WIDTH + (self.CELL_WIDTH // 2 + 1),
                            ranks[idx], curses.color_pair(0))

        for rank in ranks:
            for file in files:
                DrawCell(rank + file)
        super().Draw()

    def OnMouse(self, mouse):
        x = mouse[1] - self.win.getbegyx()[1]
        y = mouse[2] - self.win.getbegyx()[0]
        row = y // self.CELL_HEIGHT
        col = (x - 1) // self.CELL_WIDTH
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
            if self.state['autocommitenabled']:
                self.state['commitmove'] = True

        return True

    def OnKey(self, key):
        if key == 9:  # Tab
            self.state['flipped'] = not self.state['flipped']
            return True
        if key == ord('!'):
            self.state['forcemove'] = True
            return True
        if key == ord('U'):
            self.state['undo'] = True
            return True


class StatusBar(Widget):

    def __init__(self, parent, state):
        self.lasttime = datetime.datetime(year=2000, month=1, day=1)
        self.count = 0
        self.fps = 0
        super().__init__(parent, state, 1, SCREEN_WIDTH + 2, SCREEN_HEIGHT, 0)

    def Draw(self):
        new_time = datetime.datetime.now()
        if new_time - self.lasttime > datetime.timedelta(seconds=1):
            self.fps = self.count
            self.count = 0
            self.lasttime = new_time
        self.count += 1
        self.win.bkgdset(' ', curses.color_pair(5))
        self.win.addstr(
            0, 0, f" %-{SCREEN_WIDTH-8}sFPS: %-3d" %
            (self.state['statusbar'], self.fps))
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
        super().__init__(parent, state, 4, 46, 1, 59)

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
        super().__init__(parent, state, 4, 39, 35, 18)

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


class Thinking(Widget):
    NUM_MOVES = 12

    def __init__(self, parent, state):
        super().__init__(parent, state, self.NUM_MOVES * 3 + 1, 47, 5, 59)

    def Draw(self):
        self.win.addstr(0, 0, "Move  Nodes", curses.color_pair(9))

        moveses = self.state['thinking'].get('curr', {}).get('moves', {})
        moves = sorted(moveses.keys(),
                       key=lambda x: (moveses[x]['nodes'], x),
                       reverse=True)[:self.NUM_MOVES]

        max_n = 1
        if moves:
            max_n = moveses[moves[0]]['nodes'] or 1

        for i, m in enumerate(moves):
            move = moveses[m]
            san = self.state['board'].san(chess.Move.from_uci(m))
            self.win.addstr(i * 3 + 1, 0, f"{san:6}")
            progressbar.ProgressBar(win=self.win,
                                    width=31,
                                    value=move['nodes'],
                                    max_value=max_n,
                                    text=f'N={move["nodes"]}',
                                    bar_color=19,
                                    remainder_color=20,
                                    text_color=21)

            prev = self.state['thinking'].get('prev', {})
            if 'moves' in prev and m in prev['moves']:
                prev_move = prev['moves'][m]
                delta = int(move['nodes'] - prev_move['nodes']) / (
                    self.state['thinking']['curr']['time'] -
                    self.state['thinking']['prev']['time'])
                self.win.addstr(f" +{ShortenNum(delta, 4)}/s".ljust(8))
            self.win.move(i * 3 + 2, 0)
            progressbar.WdlBar(self.win, 45, move['wdl'].wins,
                               move['wdl'].draws, move['wdl'].losses, 12, 13,
                               14, 15, 16, 17)
            self.win.addstr(i * 3 + 3, 0, " " * 45)
        self.win.clrtobot()
        super().Draw()


class MoveInput(Widget):

    def __init__(self, parent, state):
        super().__init__(parent, state, 2, 39, 34, 18)

    def Draw(self):
        self.win.addstr(0, 0, "Enter move (e.g. e2e4 or h2h1n): ",
                        curses.color_pair(9))
        self.win.addstr(self.state['nextmove'], curses.color_pair(10))
        self.win.clrtoeol()
        super().Draw()

    def OnKey(self, key):
        st = self.state['nextmove']
        if key in [127, 263]:  # Backspace
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


class Timer(Widget):

    def __init__(self, parent, state):
        super().__init__(parent, state, 25, 56, 4, 1)

    def Draw(self):
        self.win.addstr(0, 5, "Time", curses.color_pair(9))
        self.win.addstr(0, 15, "Move", curses.color_pair(9))
        self.win.addstr("    Timer (Shift+T): ")
        if self.state['timerenabled']:
            self.win.addstr("[ ACTIVE  ]", curses.color_pair(7))
        else:
            self.win.addstr("[ STOPPED ]", curses.color_pair(6))
        for i in range(2):
            idx = i if self.state['flipped'] else 1 - i
            tim = int(self.state['timer'][idx])
            neg = tim < 0
            if neg:
                tim = -tim
            mt = int(self.state['movetimer'][idx])
            s = "  %s%1d:%02d:%02d %5d:%02d  " % (
                ('-' if neg else ' '),
                tim // 60 // 60,
                (tim // 60) % 60,
                (tim % 60),
                mt // 60,
                mt % 60,
            )
            self.win.addstr(
                1 + i, 0, s,
                curses.color_pair(10 if ((
                    idx == 0) == self.state['board'].turn) else 0))
        self.win.addstr(1, 23, "(9/0)±1s (Shift+9/0)±20s (o/p)±5m")
        self.win.addstr(2, 23, "(-/=)±1s (Shift+-/=)±20s ([/])±5m")

        super().Draw()

    def OnKey(self, key):
        if key == ord('T'):
            self.state['timerenabled'] = not self.state['timerenabled']
            self.state['lasttimestamp'] = datetime.datetime.now()
            return True
        keys = [
            ('-', False, -1),
            ('=', False, 1),
            ('_', False, -20),
            ('+', False, 20),
            ('[', False, -60 * 5),
            (']', False, 60 * 5),
            ('9', True, -1),
            ('0', True, 1),
            ('(', True, -20),
            (')', True, 20),
            ('o', True, -60 * 5),
            ('p', True, 60 * 5),
        ]
        for x in keys:
            if key == ord(x[0]):
                idx = 0 if self.state['flipped'] == x[1] else 1
                self.state['timer'][idx] += x[2]
                return True


class MoveList(Widget):
    NUM_PLY = 40

    def __init__(self, parent, state):
        super().__init__(parent, state, 1 + self.NUM_PLY, 65, 1, 104)

    def Draw(self):
        self.win.addstr(0, 3, "Moves:", curses.color_pair(9))
        res = []
        brd = self.state['board'].root()
        for x, y in zip(self.state['board'].move_stack,
                        self.state['move_info']):
            if brd.turn == chess.WHITE:
                hdr = '%3d.' % brd.fullmove_number
            else:
                hdr = '  ...'
            move = brd.san(x)
            brd.push(x)
            res.append((hdr + move, y))

        for i, (move, info) in enumerate(res[-self.NUM_PLY:]):
            self.win.addstr(i + 1, 0, "%-12s" % move)
            if isinstance(info, str):
                self.win.addstr(info.ljust(52))
            else:
                progressbar.WdlBar(self.win, 52, info.wins, info.draws,
                                   info.losses, 12, 13, 14, 15, 16, 17)
        self.win.clrtobot()
        super().Draw()


class Status(Widget):

    def __init__(self, parent, state):
        super().__init__(parent, state, 4, 45, 1, 15)

    def Draw(self):
        self.win.addstr(0, 0, "Status: ", curses.color_pair(9))
        if self.state['board'].is_checkmate():
            self.win.addstr("[ CHECKMATE ]", curses.color_pair(7))
        elif self.state['board'].is_stalemate():
            self.win.addstr("[ DRAW: STALEMATE ]", curses.color_pair(7))
        elif self.state['board'].is_insufficient_material():
            self.win.addstr("[ DRAW: NO MATERIAL ]", curses.color_pair(7))
        elif self.state['board'].can_claim_fifty_moves():
            self.win.addstr("[ DRAW POSSIBLE: FIFTY MOVES ]",
                            curses.color_pair(6))
        elif self.state['board'].can_claim_threefold_repetition():
            self.win.addstr("[ DRAW POSSIBLE: THREEFOLD REP ]",
                            curses.color_pair(6))
        else:
            self.win.addstr("game is not finished.")
        self.win.clrtoeol()
        self.win.addstr(1, 0, "Rule50 ply:", curses.color_pair(9))
        self.win.addstr("%3d" % self.state['board'].halfmove_clock)
        self.win.addstr("   Depth:", curses.color_pair(9))
        self.win.addstr(
            "%2d/%-3d" %
            (self.state.get('depth', 0), self.state.get('seldepth', 0)))
        self.win.addstr("  NPS:", curses.color_pair(9))
        self.win.addstr("%7d" % self.state.get('nps', 0))
        super().Draw()


class MoveReady(Widget):

    def __init__(self, parent, state):
        super().__init__(parent, state, 30, 47, 18, 59)

    def Draw(self):
        if not self.state['movenotify']:
            return
        if self.state['moveready']:
            for x in range(23):
                self.win.addstr(
                    x, 0, " MOVE READY!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! ",
                    curses.color_pair(7))
        super().Draw()

    def OnKey(self, key):
        self.state['moveready'] = False
        return False

    def OnMouse(self, mouse):
        self.state['moveready'] = False
        return False


class Tui:

    def __init__(self, stdscr, state):
        self.state = state
        self.scr = stdscr
        curses.mousemask(curses.BUTTON1_CLICKED)
        curses.init_pair(1, WHITE_PIECES,
                         DARK_SQUARES)  # White piece on dark square
        curses.init_pair(2, WHITE_PIECES, LIGHT_SQUARES)  # White on bright
        curses.init_pair(3, BLACK_PIECES, DARK_SQUARES)  # Black on dark
        curses.init_pair(4, BLACK_PIECES, LIGHT_SQUARES)  # Black on bright
        curses.init_pair(5, 0, 12)  # Status bar
        curses.init_pair(6, 15, 9)  # [FAIL]
        curses.init_pair(7, 15, 2)  # [OK]
        curses.init_pair(8, 9, 0)  # Logo
        curses.init_pair(9, 14, 0)  # Bright white on black
        curses.init_pair(10, 10, 0)  # Past move from/to marker, move text
        curses.init_pair(11, 9, 4)  # Move selector from/to marker

        curses.init_pair(12, BLACK_TEXT, WHITE_BG)  # White block
        curses.init_pair(13, WHITE_TEXT, DRAW_BG)  # Draw block
        curses.init_pair(14, WHITE_TEXT, BLACK_BG)  # Black block
        curses.init_pair(15, WHITE_BG, DRAW_BG)  # Black to draw
        curses.init_pair(16, DRAW_BG, BLACK_BG)  # Draw to white
        curses.init_pair(17, WHITE_BG, BLACK_BG)  # Black to white

        curses.init_pair(18, 0, 156)  # Background

        curses.init_pair(19, 231, 56)  # Progress bar
        curses.init_pair(20, 56, 0)  # Progress bar remoinder
        curses.init_pair(21, 231, 0)  # Progress bar text

        curses.halfdelay(1)
        self.scr.clear()

        self.widgets = [
            # Background(stdscr, state),
            Logo(stdscr, state),
            HelpPane(stdscr, state),
            Status(stdscr, state),
            ChessBoard(stdscr, state),
            StatusBar(stdscr, state),
            Engine(stdscr, state),
            Timer(stdscr, state),
            Thinking(stdscr, state),
            MoveList(stdscr, state),
            Promotions(stdscr, state),
            MoveReady(stdscr, state),
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
