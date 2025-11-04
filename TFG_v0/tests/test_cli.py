
from typer.testing import CliRunner
from tfg_v0.cli import app
import skrf as rf
from pathlib import Path

def test_cli_fit(tmp_path: Path):
    # crear s2p sintético
    ntw = rf.Network(f=[1e9, 2e9, 3e9], s=[[0,0],[0,0],[0,0]], z0=50)
    s2p = tmp_path / "x.s2p"
    ntw.write_touchstone(str(s2p.with_suffix("")))
    cfg = tmp_path / "base.yaml"
    cfg.write_text("processing:\n  ref_frequency_hz: 2e9\n  window_band_hz: 1e9\nmodel:\n  rlc_topology: series\n  initial:\n    R: 10\n    L: 1e-9\n    C: 1e-12\n")

    runner = CliRunner()
    result = runner.invoke(app, ["fit", str(s2p), "--cfg", str(cfg), "--out", str(tmp_path)])
    assert result.exit_code == 0
