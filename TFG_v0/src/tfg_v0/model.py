import numpy as np
import pandas as pd
import skrf as rf
from scipy.optimize import least_squares

def fit_equivalent(ntw: rf.Network, cfg) -> pd.DataFrame:
    """
    Ajusta un modelo RLC simple (serie o paralelo) alrededor de la frecuencia central.
    Devuelve DataFrame con R, L, C (y opcionalmente métricas RMSE).
    """

    f0 = cfg.processing.ref_frequency_hz
    bw = cfg.processing.window_band_hz
    f = ntw.f
    s11 = ntw.s[:,0,0]

    # limitar banda
    mask = (f > f0 - bw/2) & (f < f0 + bw/2)
    f_fit, s11_fit = f[mask], s11[mask]

    # función modelo
    def s11_model(params, f):
        R, L, C = params
        w = 2*np.pi*f
        Z = R + 1j*(w*L - 1/(w*C))
        return (Z - 50)/(Z + 50)

    def residuals(params):
        return np.abs(s11_model(params, f_fit) - s11_fit)

    x0 = [cfg.model.initial.R, cfg.model.initial.L, cfg.model.initial.C]
    res = least_squares(residuals, x0, bounds=(0, np.inf))

    R, L, C = res.x
    df = pd.DataFrame([{"R[Ω]": R, "L[H]": L, "C[F]": C}])

    return df
