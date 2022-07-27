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
    '--cpuct=1.9', # WCCC
    # '--cpuct=1.75', # WCCSC
    '--cpuct-base=45669',
    '--cpuct-factor=3.973',
    '--fpu-value=0.25',
    '--policy-softmax-temp=1.15',
# WCSC - using zz's T75 tune
#    '--cpuct=1.9',
#    '--cpuct-base=45669',
#    '--cpuct-factor=3.973',
#    '--fpu-value=0.65',
#    '--policy-softmax-temp=1.68',
    '--move-overhead=60000',
    '--weights=/home/wccc/book-gen/lczero-book-maker/784139',
    '--threads=3',
    '--syzygy-paths=/home/wccc/syzygy',
    '--ramlimit-mb=100000',
    '--nncache=50000000',
    '--show-wdl',
    '--show-movesleft',
    f'--logfile={os.path.abspath(".")}/logs/lc0-{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}.log',
    '--per-pv-counters',
    '--preload',
# Uncomment for BLITZ
    #'--time-manager=smooth(midpoint=43.0,max-piggybank-moves=7.0)',
    '--time-manager=smooth(midpoint=43.0,max-piggybank-moves=20.0)',
# WHEN PLAYING WHITE
    #'--draw-score-white=-20', '--draw-score-black=7',
# WHEN PLAYING BLACK
    #'--draw-score-black=-20', '--draw-score-white=7',
    #'--draw-score-white=-15', '--draw-score-black=10',     # White against Ghinkgo
     '--draw-score-white=-25', '--draw-score-black=15',   # White against Baron
    #'--draw-score-white=-100', '--draw-score-black=20',
    '--score-type=Q',
]

START_TIME = 60 * 60.0
INCREMENT = 15.0
#OPENING_BOOK = "WCSC.bin"
#OPENING_BOOK = "wccc2022.bin"
OPENING_BOOK = 'd4.bin' #None #"wccc2022.bin"
#OPENING_BOOK = "book_1.bin"
#OPENING_BOOK = "book_791557.bin"
        
