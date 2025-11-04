# -*- coding: utf-8 -*-
# -------------------------------------------------------------
#  Calibración SOLT (Short, Open, Load, Thru) para NanoVNA
#  Compatible con firmware Hugen79 (NanoVNA-H, H4, clones STM32)
#  Usa la librería 'pynanovna' para comunicarse por USB-Serial
# -------------------------------------------------------------
#  Autor: Izan París Marcos - TFG 2025
# -------------------------------------------------------------

import time
import pynanovna

# =============================================================
# Inicialización del VNA
# =============================================================
vna = pynanovna.VNA()  # Crear objeto de conexión con el NanoVNA

if not vna.is_connected():
    print("❌ No se detectó ningún NanoVNA conectado. Saliendo...")
    quit()

# =============================================================
# Configuración del barrido (rango de frecuencias)
# =============================================================
print("\n📡 CONFIGURACIÓN DE CALIBRACIÓN SOLT")
print("Introduce el rango de frecuencias en MHz y el número de puntos.\n")

start_mhz = float(input("🔸 Frecuencia mínima (MHz): "))
stop_mhz  = float(input("🔸 Frecuencia máxima (MHz): "))
points    = int(input("🔸 Número de puntos: "))

# Convertir MHz a Hz
start = start_mhz * 1e6
stop  = stop_mhz * 1e6

# Configurar el rango de calibración
vna.set_sweep(start, stop, points)

print(f"\n⚙️  Barrido configurado: {start_mhz:.3f} - {stop_mhz:.3f} MHz ({points} puntos).")
print("Es importante calibrar en el mismo rango en el que realizarás tus mediciones.\n")

# =============================================================
# Proceso de calibración paso a paso
# =============================================================

input("🔹 Paso 1: Calibración SHORT.\n"
      "Conecta el estándar CORTOCIRCUITO (SHORT) al puerto 1 del NanoVNA.\n"
      "Pulsa ENTER cuando estés listo...")
vna.calibration_step("short")

input("🔹 Paso 2: Calibración OPEN.\n"
      "Conecta el estándar ABIERTO (OPEN) al puerto 1 del NanoVNA.\n"
      "Pulsa ENTER cuando estés listo...")
vna.calibration_step("open")

input("🔹 Paso 3: Calibración LOAD.\n"
      "Conecta la CARGA (LOAD) de 50 Ω al puerto 1 del NanoVNA.\n"
      "Pulsa ENTER cuando estés listo...")
vna.calibration_step("load")

input("🔹 Paso 4: Calibración ISOLATION.\n"
      "Conecta una carga al puerto 2 (y opcionalmente otra al puerto 1).\n"
      "Pulsa ENTER cuando estés listo...")
vna.calibration_step("isolation")

input("🔹 Paso 5: Calibración THRU.\n"
      "Conecta el conector de paso (THRU) entre el puerto 1 y el puerto 2.\n"
      "Pulsa ENTER cuando estés listo...")
vna.calibration_step("through")

input("\n✅ Todos los pasos de calibración han finalizado.\n"
      "Pulsa ENTER para calcular y aplicar la calibración...")
vna.calibrate()

# =============================================================
# Guardar los parámetros de calibración
# =============================================================

ans = input("\n¿Deseas guardar esta calibración en un archivo? [S/n]: ").strip().lower()

if ans in ["", "s", "si", "sí", "y", "yes"]:
    filename = f"./Calibracion_{int(start_mhz)}MHz_{int(stop_mhz)}MHz_{points}pts.cal"
    print(f"\n💾 Guardando calibración en '{filename}' ...")
    vna.save_calibration(filename)
    print("✅ Calibración guardada correctamente.")
else:
    print("\n🗑️  Calibración descartada. No se ha guardado archivo.")

print("\n🎯 Proceso de calibración SOLT completado con éxito.")
