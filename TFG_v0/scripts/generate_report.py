
from pathlib import Path
import pandas as pd
import typer

app = typer.Typer()

@app.command()
def main(csv: Path, out: Path = Path("reports/tables/summary.md")):
    df = pd.read_csv(csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(df.to_markdown(index=False), encoding="utf-8")
    print(f"Reporte escrito en: {out}")

if __name__ == "__main__":
    app()
