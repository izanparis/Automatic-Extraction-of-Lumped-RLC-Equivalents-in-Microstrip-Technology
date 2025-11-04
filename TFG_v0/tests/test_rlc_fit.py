
import skrf as rf
from tfg_v0.modeling.rlc_fit import fit_equivalent
from types import SimpleNamespace

def test_fit_equivalent_runs():
    ntw = rf.Network(f=[1e9, 1.5e9, 2e9], s=[[0,0],[0,0],[0,0]], z0=50)
    cfg = SimpleNamespace(
        processing=SimpleNamespace(ref_frequency_hz=1.5e9, window_band_hz=1e9),
        model=SimpleNamespace(initial=SimpleNamespace(R=10.0, L=1e-9, C=1e-12))
    )
    df = fit_equivalent(ntw, cfg)
    assert {"R[Ω]", "L[H]", "C[F]"}.issubset(df.columns)
