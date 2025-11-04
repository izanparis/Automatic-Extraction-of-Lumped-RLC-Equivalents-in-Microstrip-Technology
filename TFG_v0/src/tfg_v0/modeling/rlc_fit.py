
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
import skrf as rf
from .rlc_equiv import z_rlc_series

def fit_equivalent(ntw: rf.Network, cfg) -> pd.DataFrame:
    f = ntw.f
    s11 = ntw.s[:, 0, 0]
    z0 = ntw.z0[:, 0]

    def gamma_from_z(z):
        return (z - z0) / (z + z0)

    f0 = cfg.processing.ref_frequency_hz
    bw = cfg.processing.window_band_hz
    mask = (f > f0 - bw / 2) & (f < f0 + bw / 2)

    def resid(p):
        R, L, C = p
        z = z_rlc_series(f[mask], R, L, C)
        g = gamma_from_z(z) - s11[mask]
        return np.r_[g.real, g.imag]

    p0 = [cfg.model.initial.R, cfg.model.initial.L, cfg.model.initial.C]
    lb = [1e-3, 1e-12, 1e-15]
    ub = [1e3, 1e-6, 1e-9]
    sol = least_squares(resid, p0, bounds=(lb, ub))

    return pd.DataFrame([{
        "R[Ω]": sol.x[0],
        "L[H]": sol.x[1],
        "C[F]": sol.x[2],
        "cost": float(sol.cost)
    }])
def gamma_rlc_series(f_hz: np.ndarray, z0: np.ndarray, R: float, L: float, C: float) -> np.ndarray:
    """Γ(f) del RLC en serie con línea de referencia z0(f)."""
    z = z_rlc_series(f_hz, R, L, C)
    return (z - z0) / (z + z0)


def rmse_db(a: np.ndarray, b: np.ndarray) -> float:
    """Error cuadrático medio entre dos vectores de S11 en dB."""
    a_db = 20 * np.log10(np.abs(a))
    b_db = 20 * np.log10(np.abs(b))
    return float(np.sqrt(np.mean((a_db - b_db) ** 2)))

def rmse_phase_deg(a: np.ndarray, b: np.ndarray) -> float:
    """Error cuadrático medio de fase (grados)."""
    a_ph = np.unwrap(np.angle(a)) * 180 / np.pi
    b_ph = np.unwrap(np.angle(b)) * 180 / np.pi
    return float(np.sqrt(np.mean((a_ph - b_ph) ** 2)))
