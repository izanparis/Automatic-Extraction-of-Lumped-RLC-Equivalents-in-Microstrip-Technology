
from pathlib import Path
import typer
from omegaconf import OmegaConf
from tfg_v0.io.touchstone import load_s2p
from tfg_v0.modeling.rlc_fit import fit_equivalent

app = typer.Typer()

@app.command()
def main(s2p: Path, cfg: Path = Path("config/base.yaml"), out: Path = Path("reports")):
    conf = OmegaConf.load(cfg)
    ntw = load_s2p(s2p)
    df = fit_equivalent(ntw, conf)
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"{s2p.stem}_rlc.csv"
    df.to_csv(p, index=False)
    print(f"Guardado: {p}")

if __name__ == "__main__":
    app()
