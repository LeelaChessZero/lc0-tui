import os
import datetime

LC0_DIRECTORY = '/home/wccc/lc0/build/release'

COMMAND_LINE = [
    './lc0',
    #'--backend=random',
    '--backend=multiplexing',
    '--backend-opts=a(backend=demux,(backend=cuda-fp16,gpu=0),(backend=cuda-fp16,gpu=1),(backend=cuda-fp16,gpu=2),(backend=cuda-fp16,gpu=3)),b(backend=demux,(backend=cuda-fp16,gpu=4),(backend=cuda-fp16,gpu=5),(backend=cuda-fp16,gpu=6),(backend=cuda-fp16,gpu=7))',
    #'--backend-opts=backend=cuda-fp16,(gpu=6),(gpu=7)',
    '--minibatch-size=768',
# WCCC/WCCSC
    #'--cpuct=1.9', # WCCC
    # '--cpuct=1.8', # WCCC
    '--cpuct=1.75', # WCCSC, tie breaks and armageddon
    '--cpuct-base=45669',
    '--cpuct-factor=3.973',
    '--fpu-value=0.25',
    '--policy-softmax-temp=1.15',

    '--move-overhead=10000',
    '--weights=/home/wccc/book-gen/lczero-book-maker/784139',
    '--threads=3',
    '--syzygy-paths=/home/wccc/syzygy',
    '--ramlimit-mb=90000',
    '--nncache=50000000',
    '--show-wdl',
    '--show-movesleft',
    f'--logfile={os.path.abspath(".")}/logs/lc0-{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}.log',
    '--per-pv-counters',
    '--preload',
# Uncomment for BLITZ  / Armageddon and other games with <10 seconds increment
    #'--time-manager=smooth(midpoint=43.0,max-piggybank-moves=12.0,force-piggybank-ms=700,trend-nps-update-period-ms=4000)',
    '--time-manager=smooth(midpoint=43.0,max-piggybank-moves=7.0,force-piggybank-ms=400,trend-nps-update-period-ms=2000)',
    #'--time-manager=smooth(midpoint=43.0,max-piggybank-moves=12.0)',
# WHEN PLAYING WHITE
    #'--draw-score-white=-20', '--draw-score-black=10',
# WHEN PLAYING BLACK
    #'--draw-score-black=-20', '--draw-score-white=10',
    #

    #'--draw-score-black=-30', '--draw-score-white=20',     # Baron, black
    #'--draw-score-white=-30', '--draw-score-black=20',      # Tie break, white
    #'--draw-score-black=-15', '--draw-score-white=7',      # Tie break, black
    #'--draw-score-white=-90', '--draw-score-black=15',     # Armageddon, white
    #'--draw-score-white=-25', '--draw-score-black=50',     # Armageddon, black
    #'--draw-score-white=-20', '--draw-score-black=10',     # Speed chess, white
    #'--draw-score-black=-20', '--draw-score-white=10',     # Speed chess, black
    '--score-type=Q',
]

START_TIME = 5 * 60.0
INCREMENT = 5.0
OPENING_BOOK = None
#OPENING_BOOK = 'baron-v4.bin'
OPENING_BOOK = 'plutie.bin'  # For tie breaks, and for speed chess
#OPENING_BOOK = 'h3.bin'  # For armageddon, as black, potentially for tie breaks/speed chess too
#OPENING_BOOK = 'armag-w.bin'
#OPENING_BOOK = 'shredder-v2.bin'
#OPENING_BOOK = 'chiron.bin'

#OPENING_BOOK = 'wccc2022.bin'
        
STATUS = "Speed chess games"
# WCSC - using zz's T75 tune
#    '--cpuct=1.9',
#    '--cpuct-base=45669',
#    '--cpuct-factor=3.973',
#    '--fpu-value=0.65',
#    '--policy-softmax-temp=1.68',
