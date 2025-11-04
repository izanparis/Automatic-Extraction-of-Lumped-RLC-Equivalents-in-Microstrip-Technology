import typer
import numpy as np
from pathlib import Path
import skrf as rf
import pandas as pd
from tfg_v0.config import load_config
from tfg_v0.model import fit_equivalent
from tfg_v0.plotting.compare import plot_s11_meas_vs_model

app = typer.Typer(help="CLI para flujo completo: ingestión .s2p → ajuste RLC → reportes")

@app.command()
def main(
    s2p: Path = typer.Argument(..., help="Ruta del archivo .s2p a procesar"),
    cfg: Path = typer.Option(Path("config/base.yaml"), help="Archivo de configuración YAML"),
    out: Path = typer.Option(Path("reports"), help="Carpeta de salida para reportes e imágenes"),
    save_curves: bool = typer.Option(False, help="Guardar curvas medida/modelo en CSV"),
):
    """
    Ejecuta el pipeline principal: lectura .s2p → ajuste RLC → exportación de resultados y figuras.
    """

    # ================== CARGA DE CONFIGURACIÓN Y DATOS ==================
    cfg_obj = load_config(cfg)

    if not s2p.exists():
        typer.echo(f"❌ El archivo {s2p} no existe.")
        raise typer.Exit(code=1)

    out.mkdir(parents=True, exist_ok=True)

    typer.echo(f"📡 Cargando Touchstone: {s2p.name}")
    ntw = rf.Network(str(s2p))

    # ================== AJUSTE DEL MODELO ==================
    typer.echo("⚙️  Ejecutando ajuste RLC ...")
    res = fit_equivalent(ntw, cfg_obj)

    # ================== GUARDAR RESULTADOS ==================
    csv_path = out / f"{s2p.stem}_rlc.csv"
    res.to_csv(csv_path, index=False)
    typer.echo(f"💾 Resultados guardados en: {csv_path}")

    # ================== GRAFICAR ==================
    # Prepara datos medidos y del modelo para el plotting
    f = ntw.f                      # (N,)
    s11_meas = ntw.s[:, 0, 0]      # (N,)

    # z0 puede ser (N,2) en 2-puertos → usa el puerto 1
    z0_arr = ntw.z0
    z0_1 = z0_arr[:, 0] if getattr(z0_arr, "ndim", 1) > 1 else z0_arr

    # Recupera R, L, C del DataFrame 'res'
    R = float(res.loc[0, "R[Ω]"])
    L = float(res.loc[0, "L[H]"])
    C = float(res.loc[0, "C[F]"])

    # Modelo RLC serie: Γ = (Z - Z0)/(Z + Z0), Z = R + j(ωL - 1/(ωC))
    w = 2 * np.pi * f
    Z = R + 1j * (w * L - 1.0 / (w * C))
    s11_model = (Z - z0_1) / (Z + z0_1)

    # Llamada correcta a la función de plotting
    plot_s11_meas_vs_model(f, s11_meas, s11_model, out, s2p.stem)


    # ================== PRETTY SUMMARY EN CONSOLA ==================
    from rich.console import Console
    from rich.table import Table

    console = Console()

    def _fmt_si(x: float, unit: str) -> str:
        """Formatea con prefijo SI (p, n, µ, m, k, M, G)."""
        import math
        if x == 0 or math.isnan(x):
            return f"0 {unit}"
        prefixes = [
            (1e-12, "p"),
            (1e-9,  "n"),
            (1e-6,  "µ"),
            (1e-3,  "m"),
            (1e3,   "k"),
            (1e6,   "M"),
            (1e9,   "G"),
        ]
        absx = abs(x)
        best = ("", 1.0)
        for scale, sym in prefixes:
            if absx >= scale and scale >= best[1]:
                best = (sym, scale)
        sym, scale = best
        if sym == "":
            return f"{x:.3g} {unit}"
        return f"{x/scale:.3g} {sym}{unit}"

    R = float(res.loc[0, "R[Ω]"])
    L = float(res.loc[0, "L[H]"])
    C = float(res.loc[0, "C[F]"])

    f0 = float(cfg_obj.processing.ref_frequency_hz)
    bw = float(cfg_obj.processing.window_band_hz)

    table = Table(
        title="📊 Resultados del ajuste RLC",
        show_header=False,
        header_style="bold magenta",
        padding=(0, 1),
    )

    table.add_row("Archivo", s2p.name)
    table.add_row("Frecuencia central", f"{f0/1e9:.3f} GHz")
    table.add_row("Ventana de ajuste", f"±{bw/2/1e6:.0f} MHz")
    table.add_row("Topología", str(cfg_obj.model.rlc_topology).capitalize())
    table.add_row("R", _fmt_si(R, "Ω"))
    table.add_row("L", _fmt_si(L, "H"))
    table.add_row("C", _fmt_si(C, "F"))

    if "rmse_db" in res.columns:
        table.add_row("RMSE |S11|", f"{float(res.loc[0, 'rmse_db']):.3f} dB")
    if "rmse_phase_deg" in res.columns:
        table.add_row("RMSE fase", f"{float(res.loc[0, 'rmse_phase_deg']):.2f} °")

    console.print("\n" + "─" * 80)
    console.print(table)
    console.print(f"\n📁 Resultados guardados en: [cyan]{out}[/cyan]")
    console.print("─" * 80 + "\n")

    typer.echo("✅ Proceso completado correctamente.")


if __name__ == "__main__":
    app()

