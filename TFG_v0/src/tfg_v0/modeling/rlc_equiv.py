
import numpy as np

def z_rlc_series(f_hz: np.ndarray, R: float, L: float, C: float) -> np.ndarray:
    w = 2 * np.pi * f_hz
    return R + 1j * w * L + 1 / (1j * w * C)
