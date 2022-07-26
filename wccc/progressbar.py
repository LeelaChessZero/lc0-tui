import curses
import logging

BLOCK_UNICODE = ' ▏▎▍▌▋▊▉█'
TICK_UNICODE = '▏🭰🭱🭲🭳🭴🭵▕'

def TickBar(win, width, percentage, color):
    if not (0 <= percentage <1):
        return
    value_bits = int(8*width*percentage)
    left_width = value_bits // 8
    right_width = width - left_width - 1
    win.addstr(' ' * left_width, curses.color_pair(color))
    win.addstr(TICK_UNICODE[value_bits % 8], curses.color_pair(color))
    win.addstr(' ' * right_width, curses.color_pair(color))


def ProgressBar(win, width, value, max_value, text, bar_color, remainder_color,
                text_color):
    value_bits = int(8 * width * value / max_value)
    left_width = value_bits // 8
    if left_width >= len(text):
        win.addstr(text.ljust(left_width), curses.color_pair(bar_color))
    else:
        win.addstr(' ' * left_width, curses.color_pair(bar_color))
    remainer_width = value_bits % 8
    if left_width < width:
        win.addstr(BLOCK_UNICODE[remainer_width],
                   curses.color_pair(remainder_color))
    right_width = width - left_width - 1  # -1 for remainder
    if left_width >= len(text):
        win.addstr(' ' * right_width, curses.color_pair(text_color))
    else:
        win.addstr(text.ljust(right_width), curses.color_pair(text_color))


def WriteBarMeat(win, width, left_text, middle_text, right_text, color):
    left_text = left_text + ' ' if left_text else ''
    right_text = ' ' + right_text if right_text else ''
    middle_text = middle_text if middle_text else ''
    win.addstr(
        f'{left_text}'
        f'{middle_text.center(width - len(left_text) - len(right_text))}'
        f'{right_text}', curses.color_pair(color))



def WdlBar(win, width, w, d, l, white_bar, draw_bar, black_bar, white_to_draw,
           draw_to_black, white_to_black):
    total = w + d + l
    white_bits = int(8 * width * w / total)
    black_bits = int(8 * width * l / total)
    draw_bits = width * 8 - white_bits - black_bits
    if white_bits % 8 > 0 and white_bits // 8 == (white_bits + draw_bits) // 8:
        white_bits += draw_bits // 2
        black_bits += draw_bits - draw_bits // 2
        draw_bits = 0
    white_width = white_bits // 8
    black_width = black_bits // 8
    draw_width = max(0, (draw_bits - (8 - white_bits % 8) % 8) // 8)
    white_text = f'W={w}'
    black_text = f'B={l}'
    draw_text = f'D={d}'

    layouts = [
        " W  D  B ",
        "   WD  B ",
        " W  DB   ",
        "   WDB   ",
        " WD    B " if w > l else " W    DB ",
        " W    DB " if w > l else " WD    B ",
        "WDB      " if w > l else "      WDB",
        "      WDB" if w > l else "WDB      ",
    ]

    def label_length(layout):
        res = 0
        for c in layout:
            if c != ' ':
                if res:
                    res += 1
                if c == 'W':
                    res += len(white_text)
                elif c == 'B':
                    res += len(black_text)
                elif c == 'D':
                    res += len(draw_text)
        return res

    def get_text(char):
        if char == 'W':
            return white_text
        elif char == 'B':
            return black_text
        elif char == 'D':
            return draw_text
        return None

    def draw_meat(layout, width, color):
        WriteBarMeat(win, width, get_text(layout[0]), get_text(layout[1]),
                     get_text(layout[2]), color)

    for layout in layouts:
        (lw, ld, lb) = [layout[i:i + 3] for i in range(0, len(layout), 3)]
        if white_width < label_length(lw): continue
        if draw_width < label_length(ld): continue
        if black_width < label_length(lb): continue
        draw_meat(lw, white_width, white_bar)
        if white_bits % 8 > 0:
            win.addstr(
                BLOCK_UNICODE[white_bits % 8],
                curses.color_pair(
                    white_to_draw if draw_bits > 0 else white_to_black))
        draw_meat(ld, draw_width, draw_bar)
        if draw_bits and (white_bits + draw_bits) % 8 > 0:
            win.addstr(BLOCK_UNICODE[(white_bits + draw_bits) % 8],
                       curses.color_pair(draw_to_black))
        draw_meat(lb, black_width, black_bar)
        return
