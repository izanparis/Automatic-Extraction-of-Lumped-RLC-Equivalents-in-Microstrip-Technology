# scripts/batch_fit.py
from pathlib import Path
import pandas as pd
import skrf as rf

from rich.console import Console
from rich.table import Table

from tfg_v0.config import load_config
from tfg_v0.model import fit_equivalent  # usa tu función actual
# Si tu CLI calcula RMSE, puedes importarlas y añadir métricas

def main(
    data_dir: Path = Path("data/raw"),
    cfg_path: Path = Path("config/base.yaml"),
    out_dir: Path = Path("reports"),
):
    console = Console()
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(data_dir.glob("*.s2p"))
    if not files:
        console.print(f"[red]No hay .s2p en {data_dir}[/red]")
        return

    cfg = load_config(cfg_path)
    rows = []

    console.print(f"[cyan]Procesando {len(files)} archivos .s2p desde {data_dir} ...[/cyan]")

    for fpath in files:
        try:
            ntw = rf.Network(str(fpath))
            res = fit_equivalent(ntw, cfg)  # DataFrame 1x3 con R,L,C
            res_csv = out_dir / f"{fpath.stem}_rlc.csv"
            res.to_csv(res_csv, index=False)

            rows.append({
                "file": fpath.name,
                "R[Ω]": float(res.loc[0,"R[Ω]"]),
                "L[H]": float(res.loc[0,"L[H]"]),
                "C[F]": float(res.loc[0,"C[F]"]),
            })
            console.print(f"  ✅ {fpath.name} → {res_csv.name}")
        except Exception as e:
            console.print(f"  [red]❌ {fpath.name}[/red] → {e}")

    if not rows:
        console.print("[red]No se pudieron generar resultados.[/red]")
        return

    df = pd.DataFrame(rows)
    resume_csv = out_dir / "resumen_rlc.csv"
    df.to_csv(resume_csv, index=False)

    # Tabla bonita
    table = Table(title="📊 Resumen RLC (modo lote)", header_style="bold magenta")
    for col in df.columns:
        table.add_column(col)
    for _, r in df.iterrows():
        table.add_row(
            r["file"],
            f"{r['R[Ω]']:.3g}",
            f"{r['L[H]']:.3g}",
            f"{r['C[F]']:.3g}",
        )
    console.print()
    console.print(table)
    console.print(f"\n📁 Resumen guardado en: [cyan]{resume_csv}[/cyan]")

if __name__ == "__main__":
    main()
