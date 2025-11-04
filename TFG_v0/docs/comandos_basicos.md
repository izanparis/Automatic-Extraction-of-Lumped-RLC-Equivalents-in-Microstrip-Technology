# ⚙️ Guía de comandos esenciales — Proyecto TFG_v0

## 🧩 1️⃣ Activar el entorno virtual

### 🔹 PowerShell (recomendado)
```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea el script:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 🔹 CMD clásico
```cmd
.\.venv\Scriptsctivate.bat
```

### 🔹 Git Bash o VS Code (bash)
```bash
source .venv/Scripts/activate
```

---

## 📦 2️⃣ Instalar o reinstalar el paquete (modo desarrollo)
```powershell
pip install -e .
```

---

## 🧹 3️⃣ Limpiar cachés y versiones antiguas
```powershell
pip uninstall -y tfg-v0
Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
Remove-Item .uild, .\dist, .\*.egg-info -Recurse -Force -ErrorAction SilentlyContinue
```

---

## 🧪 4️⃣ Verificar el CLI
```powershell
python -m tfg_v0.cli --help
```

Debe mostrar:
```
Commands:
  fit  Ajusta el equivalente RLC para un .s2p y genera reportes.
```

---

## ⚙️ 5️⃣ Ejecutar el pipeline completo
```powershell
python -m tfg_v0.cli fit .\dataaw\ejemplo.s2p --cfg .\configase.yaml --out .eports
```

✅ Genera en `/reports`:
- `ejemplo_rlc.csv`
- `ejemplo_S11_mag.png`
- `ejemplo_S11_phase.png`
- *(opcional)* `ejemplo_curvas.csv` si añades `--save-curves`

---

## 🧮 6️⃣ Crear resumen global de resultados
```powershell
Get-ChildItem .eports\ *_rlc.csv | % {
    Import-Csv $_ | Add-Member -NotePropertyName "file" -NotePropertyValue $_.BaseName -PassThru
} | Export-Csv .eportsesumen_rlc.csv -NoTypeInformation
```

---

## 🧰 7️⃣ Salir del entorno virtual
```powershell
deactivate
```

---

## ✨ Tip (VS Code)
Para usar automáticamente el entorno virtual en VS Code:
```
Ctrl + Shift + P → Python: Select Interpreter → .venv (TFG_v0)
```

---

📁 **Ubicación sugerida:**  
`C:\Users\izan1\Desktop\TFG_v0\docs\comandos_basicos.md`
