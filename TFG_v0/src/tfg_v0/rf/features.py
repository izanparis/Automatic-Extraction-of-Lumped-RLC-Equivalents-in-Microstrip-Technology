
import numpy as np

def mag_phase(s: np.ndarray):
    return np.abs(s), np.angle(s, deg=True)
