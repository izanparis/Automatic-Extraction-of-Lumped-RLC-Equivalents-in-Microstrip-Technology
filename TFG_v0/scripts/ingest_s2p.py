
from pathlib import Path
import typer
from tfg_v0.io.touchstone import load_s2p

app = typer.Typer()

@app.command()
def main(s2p: Path):
    ntw = load_s2p(s2p)
    print(f"Cargado: {ntw.name or s2p.name} con {len(ntw.f)} puntos")

if __name__ == "__main__":
    app()
