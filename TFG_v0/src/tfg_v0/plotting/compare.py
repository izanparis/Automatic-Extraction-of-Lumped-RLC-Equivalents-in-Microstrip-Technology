# src/tfg_v0/plotting/compare.py
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

def _db(x: np.ndarray) -> np.ndarray:
    return 20 * np.log10(np.abs(x))

def _phase_deg(x: np.ndarray) -> np.ndarray:
    return np.unwrap(np.angle(x)) * 180 / np.pi

def plot_s11_meas_vs_model(
    f_hz: np.ndarray,
    s11_meas: np.ndarray,
    s11_model: np.ndarray,
    outdir: Path,
    stem: str,
):
    outdir.mkdir(parents=True, exist_ok=True)

    # Magnitud
    plt.figure()
    plt.plot(f_hz/1e9, _db(s11_meas), label="|S11| medido [dB]")
    plt.plot(f_hz/1e9, _db(s11_model), linestyle="--", label="|S11| modelo [dB]")
    plt.xlabel("Frecuencia [GHz]"); plt.ylabel("|S11| [dB]")
    plt.title("Comparación |S11| medido vs modelo")
    plt.grid(True); plt.legend()
    mag_path = outdir / f"{stem}_S11_mag.png"
    plt.savefig(mag_path, dpi=180, bbox_inches="tight"); plt.close()

    # Fase
    plt.figure()
    plt.plot(f_hz/1e9, _phase_deg(s11_meas), label="∠S11 medido [°]")
    plt.plot(f_hz/1e9, _phase_deg(s11_model), linestyle="--", label="∠S11 modelo [°]")
    plt.xlabel("Frecuencia [GHz]"); plt.ylabel("Fase [°]")
    plt.title("Comparación fase S11 medido vs modelo")
    plt.grid(True); plt.legend()
    ph_path = outdir / f"{stem}_S11_phase.png"
    plt.savefig(ph_path, dpi=180, bbox_inches="tight"); plt.close()

    return mag_path, ph_path
