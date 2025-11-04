
# TFG — Microstrip → Equivalentes RLC

Herramienta en Python para **obtener un equivalente concentrado RLC** a partir de **S-parámetros** (`.s2p`) de líneas/estructuras en microstrip. Incluye CLI, módulos, tests y base para control remoto de VNA (futuro).

## Requisitos
- Python ≥ 3.10
- (Opcional) Git y VS Code

## Uso rápido
```bash
# 1) Crear entorno
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/Mac:
# source .venv/bin/activate

# 2) Instalar
pip install -U pip
pip install -e .
pip install ruff black pytest

# 3) Colocar .s2p en data/raw/
# 4) Ejecutar ajuste
python -m tfg_v0.cli fit data/raw/ejemplo.s2p --cfg config/base.yaml --out reports
```

## Estructura
Ver `pyproject.toml`, `src/tfg_v0/*` y `config/base.yaml`.
