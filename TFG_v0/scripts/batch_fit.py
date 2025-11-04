# scripts/batch_fit.py
from pathlib import Path
import math
import numpy as np
import pandas as pd
import skrf as rf
import sys

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TimeElapsedColumn, TimeRemainingColumn, SpinnerColumn, TextColumn

from tfg_v0.config import load_config
from tfg_v0.model import fit_equivalent  # Debe existir tfg_v0/model.py con fit_equivalent(...)

# Plotting opcional (usa tu módulo si existe; si no, fallback interno)
_HAS_PLOTTING = False
try:
    from tfg_v0.plotting.compare import plot_s11_meas_vs_model
    _HAS_PLOTTING = True
except Exception:
    # Fallback simple con matplotlib si no existe tfg_v0.plotting.compare
    try:
        import matplotlib.pyplot as plt
        def _db(x): return 20*np.log10(np.abs(x))
        def _phase_deg(x): return np.unwrap(np.angle(x))*180/np.pi
        def plot_s11_meas_vs_model(f_hz, s11_meas, s11_model, outdir: Path, stem: str):
            outdir.mkdir(parents=True, exist_ok=True)
            # Magnitud
            plt.figure()
            plt.plot(f_hz/1e9, _db(s11_meas), label="|S11| medido [dB]")
            plt.plot(f_hz/1e9, _db(s11_model), linestyle="--", label="|S11| modelo [dB]")
            plt.xlabel("Frecuencia [GHz]"); plt.ylabel("|S11| [dB]")
            plt.title("Comparación |S11| medido vs modelo"); plt.grid(True); plt.legend()
            plt.savefig(outdir / f"{stem}_S11_mag.png", dpi=180, bbox_inches="tight"); plt.close()

            # Fase
            plt.figure()
            plt.plot(f_hz/1e9, _phase_deg(s11_meas), label="∠S11 medido [°]")
            plt.plot(f_hz/1e9, _phase_deg(s11_model), linestyle="--", label="∠S11 modelo [°]")
            plt.xlabel("Frecuencia [GHz]"); plt.ylabel("Fase [°]")
            plt.title("Comparación fase S11 medido vs modelo"); plt.grid(True); plt.legend()
            plt.savefig(outdir / f"{stem}_S11_phase.png", dpi=180, bbox_inches="tight"); plt.close()

        _HAS_PLOTTING = True
    except Exception:
        _HAS_PLOTTING = False

# -------- utils ----------
def gamma_rlc_series(f_hz: np.ndarray, z0: np.ndarray | float, R: float, L: float, C: float) -> np.ndarray:
    w = 2 * np.pi * f_hz
    Z = R + 1j * (w * L - 1.0 / (w * C))
    z0_arr = np.asarray(z0)
    if getattr(z0_arr, "ndim", 1) > 1:  # (N,2) → puerto 1
        z0_arr = z0_arr[:, 0]
    return (Z - z0_arr) / (Z + z0_arr)

def rmse_db(a: np.ndarray, b: np.ndarray) -> float:
    A = 20 * np.log10(np.abs(a)); B = 20 * np.log10(np.abs(b))
    return float(np.sqrt(np.mean((A - B) ** 2)))

def rmse_phase_deg(a: np.ndarray, b: np.ndarray) -> float:
    A = np.unwrap(np.angle(a)) * 180 / np.pi
    B = np.unwrap(np.angle(b)) * 180 / np.pi
    return float(np.sqrt(np.mean((A - B) ** 2)))

def fmt_si(x: float, unit: str) -> str:
    if x == 0 or math.isnan(x): return f"0 {unit}"
    scales = [(1e-12, "p"), (1e-9, "n"), (1e-6, "µ"), (1e-3, "m"), (1e3, "k"), (1e6, "M"), (1e9, "G")]
    absx = abs(x); sym = ""; scale = 1.0
    for s, s_sym in scales:
        if absx >= s and s >= scale: sym, scale = s_sym, s
    return f"{x/scale:.3g} {sym}{unit}" if sym else f"{x:.3g} {unit}"

# ---------- batch ----------
def batch_fit(
    data_dir: Path = Path("data/raw"),
    cfg_path: Path = Path("config/base.yaml"),
    out_dir: Path = Path("reports"),
    recursive: bool = False,
    plots: bool = True,
    rmse_ok_db: float = 1.0,
    rmse_warn_db: float = 2.0,
) -> None:
    console = Console()
    out_dir.mkdir(parents=True, exist_ok=True)

    pattern = "**/*.s2p" if recursive else "*.s2p"
    files = sorted(data_dir.glob(pattern))
    if not files:
        console.print(f"[red]No hay .s2p en {data_dir}[/red]")
        return

    cfg = load_config(cfg_path)
    rows = []
    console.print(f"[cyan]Procesando {len(files)} archivo(s) .s2p desde {data_dir}[/cyan]")

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    with progress:
        task = progress.add_task("Ajustando…", total=len(files))

        for fpath in files:
            try:
                ntw = rf.Network(str(fpath))
                res = fit_equivalent(ntw, cfg)  # DataFrame con R,L,C

                f = ntw.f
                s11_meas = ntw.s[:, 0, 0]
                z0 = ntw.z0
                s11_model = gamma_rlc_series(
                    f, z0,
                    float(res.loc[0, "R[Ω]"]),
                    float(res.loc[0, "L[H]"]),
                    float(res.loc[0, "C[F]"]),
                )

                e_db = rmse_db(s11_meas, s11_model)
                e_ph = rmse_phase_deg(s11_meas, s11_model)

                # CSV por archivo
                per_file_csv = out_dir / f"{fpath.stem}_rlc.csv"
                res2 = res.copy()
                res2.loc[0, "rmse_db"] = e_db
                res2.loc[0, "rmse_phase_deg"] = e_ph
                res2.to_csv(per_file_csv, index=False)

                # Gráficos por archivo (si posible)
                if plots and _HAS_PLOTTING:
                    plot_s11_meas_vs_model(f, s11_meas, s11_model, out_dir, fpath.stem)

                rows.append({
                    "file": fpath.name,
                    "R[Ω]": float(res.loc[0, "R[Ω]"]),
                    "L[H]": float(res.loc[0, "L[H]"]),
                    "C[F]": float(res.loc[0, "C[F]"]),
                    "rmse_db": e_db,
                    "rmse_phase_deg": e_ph,
                })
            except Exception as e:
                console.print(f"[red]❌ {fpath.name}[/red] → {e}")
            finally:
                progress.update(task, advance=1)

    if not rows:
        console.print("[red]No se pudieron generar resultados.[/red]")
        return

    df = pd.DataFrame(rows).sort_values("rmse_db").reset_index(drop=True)
    resume_csv = out_dir / "resumen_rlc.csv"
    df.to_csv(resume_csv, index=False)

    # Tabla final
    table = Table(title="📊 Resumen batch (ordenado por RMSE dB)", header_style="bold magenta")
    for col in ["file","R","L","C","RMSE dB","RMSE fase (°)"]:
        table.add_column(col)
    for _, r in df.iterrows():
        color = "green" if r["rmse_db"] <= rmse_ok_db else ("yellow" if r["rmse_db"] <= rmse_warn_db else "red")
        table.add_row(
            r["file"],
            fmt_si(r["R[Ω]"], "Ω"),
            fmt_si(r["L[H]"], "H"),
            fmt_si(r["C[F]"], "F"),
            f"[{color}]{r['rmse_db']:.3f}[/{color}]",
            f"{r['rmse_phase_deg']:.2f}",
        )

    console.print()
    console.print(table)
    console.print(f"\n📁 Resumen guardado en: [cyan]{resume_csv}[/cyan]")

# ---------- CLI mínima ----------
if __name__ == "__main__":
    # Uso:
    #   python scripts/batch_fit.py [data_dir] [cfg_path] [out_dir] [--recursive] [--no-plots]
    data_dir  = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else Path("data/raw")
    cfg_path  = Path(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith("-") else Path("config/base.yaml")
    out_dir   = Path(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith("-") else Path("reports")
    recursive = ("--recursive" in sys.argv) or ("-r" in sys.argv)
    plots     = not ("--no-plots" in sys.argv)
    batch_fit(data_dir, cfg_path, out_dir, recursive, plots)
