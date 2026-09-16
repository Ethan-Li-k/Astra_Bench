from pathlib import Path
from rsi.live import LiveSim
ROOT = Path(__file__).resolve().parents[1]
def create_settled_backend():
    b = LiveSim(wrist_pi=True)
    for _ in range(250): b.tick()
    if b.reason: raise RuntimeError(b.reason)
    return b
