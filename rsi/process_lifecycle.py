"""Keep an API physical owner independent of its tmux supervisor's terminal."""
import os

def detach_api_worker():
    if os.getsid(0)!=os.getpid():
        os.setsid()
    return {'pid':os.getpid(),'session_id':os.getsid(0),'process_group':os.getpgrp(),
            'independent_terminal_session':os.getsid(0)==os.getpid()}
