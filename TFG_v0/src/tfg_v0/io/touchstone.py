
import skrf as rf
from pathlib import Path

def load_s2p(path: Path) -> rf.Network:
    return rf.Network(str(path))
