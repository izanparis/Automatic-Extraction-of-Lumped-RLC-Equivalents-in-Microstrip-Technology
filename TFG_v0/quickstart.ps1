
# Ejecutar desde la carpeta del proyecto TFG_v0
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -e .
pip install ruff black pytest
# Copia el archivo ejemplo.s2p a data/raw/
if (!(Test-Path -Path "data\raw")) { New-Item -ItemType Directory -Path "data\raw" | Out-Null }
Copy-Item -Path "$PSScriptRoot\ejemplo.s2p" -Destination "data\raw\ejemplo.s2p" -Force
# Ejecuta una prueba rápida
python -m tfg_v0.cli fit data/raw/ejemplo.s2p --cfg config/base.yaml --out reports
