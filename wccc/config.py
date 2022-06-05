import os

LC0_DIRECTORY = '/home/crem/dev/lc0.wt0/build/release'

COMMAND_LINE = [
    './lc0',
    '--backend=trivial',
    # '--backend=cuda',
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

START_TIME = 1 * 60
INCREMENT = 1
OPENING_BOOK = "WCCCbook.bin"
