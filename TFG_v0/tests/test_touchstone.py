
import skrf as rf
from pathlib import Path
from tfg_v0.io.touchstone import load_s2p

def test_load_s2p(tmp_path: Path):
    ntw = rf.Network(f=[1e9, 2e9, 3e9], s=[[0,0],[0,0],[0,0]], z0=50)
    p = tmp_path / "tmp.s2p"
    ntw.write_touchstone(str(p.with_suffix("")))
    out = load_s2p(p)
    assert hasattr(out, "s")
