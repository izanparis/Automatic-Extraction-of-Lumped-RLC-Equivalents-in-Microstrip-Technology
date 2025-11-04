# -*- coding: utf-8 -*-
# -------------------------------------------------------------
#  Medición de parámetros S con calibración previa en NanoVNA
#  Compatible con pynanovna
#  Autor: Basado en script de Izan París Marcos - TFG 2025
# -------------------------------------------------------------

import os
import time
import numpy as np
import pandas as pd
import pynanovna
import skrf as rf
import matplotlib.pyplot as plt
import sys
import ast

class VNAMeasurement:
    def __init__(self):
        self.vna = None
        self.measurement_data = None
        self.frequencies = None
        self.s_params = {}
        
    def connect_vna(self):
        """Conectar al NanoVNA"""
        print("📡 Conectando con NanoVNA...")
        try:
            self.vna = pynanovna.VNA()
            if not self.vna.is_connected():
                print("❌ No se detectó ningún NanoVNA. Verifica el cable USB y el puerto COM.")
                return False
            print("✅ NanoVNA detectado correctamente.")
            return True
        except Exception as e:
            print(f"❌ Error conectando al VNA: {e}")
            return False
    
    def load_calibration(self, cal_file):
        """Cargar archivo de calibración al VNA"""
        print(f"\n📁 Cargando calibración: {cal_file}")
        
        cal_file = cal_file.strip().strip('"').strip("'")
        cal_file = os.path.normpath(cal_file)
        
        if not os.path.exists(cal_file):
            print(f"❌ El archivo '{cal_file}' no existe.")
            return False
        
        try:
            self.vna.load_calibration(cal_file)
            print(f"✅ Calibración cargada correctamente")
            return True
        except Exception as e:
            print(f"❌ Error al cargar la calibración: {e}")
            return False
    
    def configure_sweep(self, start_mhz, stop_mhz, points):
        """Configurar barrido de frecuencia"""
        print(f"\n⚙️ Configurando barrido: {start_mhz}-{stop_mhz} MHz, {points} puntos")
        
        try:
            self.vna.set_sweep(start_mhz * 1e6, stop_mhz * 1e6, points)
            
            # Intentar establecer puntos de barrido si está disponible
            if hasattr(self.vna, "sweep_points"):
                try:
                    self.vna.sweep_points = points
                except Exception:
                    pass
                    
            print("✅ Barrido configurado correctamente")
            return True
        except Exception as e:
            print(f"❌ Error configurando barrido: {e}")
            return False
    
    def measure_dut(self, dut_name="DUT"):
        """Medir el Dispositivo Bajo Prueba (DUT)"""
        print(f"\n📊 Realizando medición del {dut_name}...")
        
        try:
            # Iniciar barrido
            self.vna.sweep()
            print("⏱️ Barrido iniciado... esperando adquisición de datos...")
            
            # Esperar mientras se completa el barrido
            total_wait = 8  # Aumentado para asegurar captura
            for i in range(total_wait):
                bar_len = 30
                progress = (i + 1) / total_wait
                filled = int(bar_len * progress)
                bar = "█" * filled + "-" * (bar_len - filled)
                sys.stdout.write(f"\r📡 Adquiriendo datos: |{bar}| {int(progress*100)}%")
                sys.stdout.flush()
                time.sleep(0.5)
            print("\n✅ Barrido completado.")
            
            # Exportar datos a CSV temporal
            csv_temp = f"{dut_name}_temp_measurement.csv"
            self.vna.stream_to_csv(csv_temp)
            print(f"📄 Datos exportados a: {csv_temp}")
            
            # Verificar que el archivo se creó y tiene datos
            if not os.path.exists(csv_temp):
                print("❌ No se pudo crear el archivo CSV temporal")
                return False
                
            file_size = os.path.getsize(csv_temp)
            if file_size == 0:
                print("❌ El archivo CSV está vacío")
                return False
                
            print(f"📏 Tamaño del archivo: {file_size} bytes")
            
            # Procesar datos
            success = self._process_measurement_data(csv_temp)
            
            # Limpiar archivo temporal
            if os.path.exists(csv_temp):
                os.remove(csv_temp)
                
            if success:
                print(f"✅ Medición del {dut_name} completada y procesada")
                return True
            else:
                print(f"❌ Error procesando datos del {dut_name}")
                return False
            
        except Exception as e:
            print(f"❌ Error durante la medición: {e}")
            return False
    
    def _process_measurement_data(self, csv_path):
        """Procesar datos de medición y extraer parámetros S"""
        try:
            df = pd.read_csv(csv_path)
            print(f"📊 DataFrame cargado: {len(df)} filas, {len(df.columns)} columnas")
            print(f"📋 Columnas: {df.columns.tolist()}")
            
            # Normalizar nombres de columnas
            df.columns = [c.strip().lower() for c in df.columns]
            print(f"📋 Columnas normalizadas: {df.columns.tolist()}")
            
            # Verificar columnas requeridas
            required_columns = ["s11", "s21", "freq"]
            if not all(col in df.columns for col in required_columns):
                print(f"❌ Faltan columnas requeridas. Esperadas: {required_columns}")
                print(f"   Encontradas: {df.columns.tolist()}")
                return False
            
            # Mostrar primeras filas para debugging
            print("\n🔍 Primeras filas de datos:")
            print(df.head(3))
            
            # Convertir datos a complejos
            def parse_complex(val):
                try:
                    if isinstance(val, complex):
                        return val
                    if pd.isna(val):
                        return complex(0, 0)
                    # Para cadenas como "(0.123, -0.456)"
                    if isinstance(val, str):
                        val = val.strip()
                        if val.startswith('(') and val.endswith(')'):
                            val = val[1:-1]
                        parts = val.split(',')
                        if len(parts) == 2:
                            real = float(parts[0].strip())
                            imag = float(parts[1].strip())
                            return complex(real, imag)
                    return complex(val)
                except Exception as e:
                    print(f"⚠️ Error parseando valor: {val}, error: {e}")
                    return complex(0, 0)
            
            print("🔄 Convirtiendo datos a complejos...")
            s11 = np.array([parse_complex(v) for v in df["s11"]])
            s21 = np.array([parse_complex(v) for v in df["s21"]])
            freqs = df["freq"].to_numpy()
            
            # Verificar que tenemos datos válidos
            print(f"📏 S11: {len(s11)} puntos, S21: {len(s21)} puntos, Frecuencias: {len(freqs)} puntos")
            print(f"🔢 S11 ejemplo: {s11[0]} (magnitud: {np.abs(s11[0]):.3f})")
            print(f"🔢 S21 ejemplo: {s21[0]} (magnitud: {np.abs(s21[0]):.3f})")
            print(f"📡 Frecuencia ejemplo: {freqs[0]/1e6:.1f} MHz")
            
            # Verificar que no todos los valores sean cero
            if np.all(np.abs(s11) == 0) or np.all(np.abs(s21) == 0):
                print("⚠️  Advertencia: Todos los valores S11 o S21 son cero")
            
            # Almacenar parámetros S
            self.frequencies = freqs
            self.s_params = {
                'S11': s11,
                'S21': s21,
                'S12': s21,  # Asumiendo reciprocidad
                'S22': s11   # Asumiendo simetría
            }
            
            print("✅ Datos procesados correctamente")
            return True
            
        except Exception as e:
            print(f"❌ Error procesando datos del CSV: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_s_parameters(self):
        """Obtener todos los parámetros S medidos"""
        return self.s_params
    
    def get_parameter_dB(self, parameter):
        """Obtener parámetro S en dB"""
        if parameter in self.s_params and len(self.s_params[parameter]) > 0:
            magnitude = np.abs(self.s_params[parameter])
            # Evitar log(0)
            magnitude = np.where(magnitude == 0, 1e-10, magnitude)
            return 20 * np.log10(magnitude)
        return None
    
    def get_parameter_magnitude_phase(self, parameter):
        """Obtener magnitud y fase de un parámetro S"""
        if parameter in self.s_params and len(self.s_params[parameter]) > 0:
            magnitude = np.abs(self.s_params[parameter])
            phase = np.angle(self.s_params[parameter], deg=True)
            return magnitude, phase
        return None, None
    
    def save_s2p_file(self, filename):
        """Guardar parámetros S en archivo Touchstone .s2p"""
        if not self.s_params or len(self.s_params['S11']) == 0:
            print("❌ No hay datos de parámetros S para guardar")
            return False
        
        try:
            # Asegurar que el archivo tenga extensión .s2p
            if not filename.endswith('.s2p'):
                filename += '.s2p'
            
            # Crear red de dos puertos
            s_matrix = np.zeros((len(self.frequencies), 2, 2), dtype=complex)
            s_matrix[:, 0, 0] = self.s_params['S11']
            s_matrix[:, 1, 0] = self.s_params['S21']
            s_matrix[:, 0, 1] = self.s_params['S12']
            s_matrix[:, 1, 1] = self.s_params['S22']
            
            ntw = rf.Network(frequency=self.frequencies, s=s_matrix)
            
            # Guardar archivo .s2p
            ntw.write_touchstone(filename)
            print(f"✅ Parámetros S guardados en: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error guardando archivo .s2p: {e}")
            return False
    
    def save_csv_file(self, filename):
        """Guardar parámetros S en archivo CSV"""
        if not self.s_params or len(self.s_params['S11']) == 0:
            print("❌ No hay datos de parámetros S para guardar")
            return False
        
        try:
            # Asegurar que el archivo tenga extensión .csv
            if not filename.endswith('.csv'):
                filename += '.csv'
            
            data = {
                'Frequency_Hz': self.frequencies
            }
            
            for param in ['S11', 'S21', 'S12', 'S22']:
                magnitude, phase = self.get_parameter_magnitude_phase(param)
                dB = self.get_parameter_dB(param)
                
                data[f'{param}_Magnitude'] = magnitude
                data[f'{param}_Phase_deg'] = phase
                data[f'{param}_dB'] = dB
                data[f'{param}_Real'] = self.s_params[param].real
                data[f'{param}_Imag'] = self.s_params[param].imag
            
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            print(f"✅ Parámetros S guardados en: {filename}")
            print(f"📊 Archivo contiene {len(df)} puntos de medición")
            return True
            
        except Exception as e:
            print(f"❌ Error guardando archivo CSV: {e}")
            return False
    
    def plot_measurement(self, parameters=None, plot_type='dB'):
        """Graficar los parámetros S medidos"""
        if not self.s_params or len(self.s_params['S11']) == 0:
            print("❌ No hay datos para graficar")
            return
        
        if parameters is None:
            parameters = ['S11', 'S21']
        
        # Filtrar parámetros válidos
        valid_params = [p for p in parameters if p in self.s_params and len(self.s_params[p]) > 0]
        if not valid_params:
            print("❌ No hay parámetros válidos para graficar")
            return
        
        plt.figure(figsize=(12, 6))
        
        for param in valid_params:
            freq_mhz = self.frequencies / 1e6
            
            if plot_type == 'dB':
                y_data = self.get_parameter_dB(param)
                y_label = 'dB'
                title_suffix = ' (dB)'
            elif plot_type == 'magnitude':
                y_data, _ = self.get_parameter_magnitude_phase(param)
                y_label = 'Magnitud'
                title_suffix = ' (Magnitud)'
            elif plot_type == 'phase':
                _, y_data = self.get_parameter_magnitude_phase(param)
                y_label = 'Fase (grados)'
                title_suffix = ' (Fase)'
            else:
                print("❌ Tipo de gráfico no válido")
                return
            
            # Verificar que tenemos datos para graficar
            if y_data is not None and len(y_data) > 0:
                plt.plot(freq_mhz, y_data, label=param, linewidth=2)
                print(f"📈 Graficando {param}: {len(y_data)} puntos")
            else:
                print(f"⚠️  No hay datos para {param}")
        
        if plt.gca().has_data():
            plt.xlabel('Frecuencia (MHz)')
            plt.ylabel(y_label)
            plt.title(f'Parámetros S Medidos{title_suffix}')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.show()
            print("✅ Gráfica mostrada correctamente")
        else:
            print("❌ No hay datos válidos para graficar")
            plt.close()
    
    def plot_smith_chart(self):
        """Graficar parámetros S en diagrama de Smith"""
        if not self.s_params or len(self.s_params['S11']) == 0:
            print("❌ No hay datos para graficar")
            return
        
        try:
            # Crear network para diagrama de Smith
            s_matrix = np.zeros((len(self.frequencies), 2, 2), dtype=complex)
            s_matrix[:, 0, 0] = self.s_params['S11']
            s_matrix[:, 1, 1] = self.s_params['S22']
            
            ntw = rf.Network(frequency=self.frequencies, s=s_matrix)
            
            plt.figure(figsize=(8, 8))
            ntw.plot_s_smith(m=0, n=0, label='S11')
            ntw.plot_s_smith(m=1, n=1, label='S22')
            plt.title('Diagrama de Smith - S11 y S22')
            plt.legend()
            plt.tight_layout()
            plt.show()
            print("✅ Diagrama de Smith mostrado correctamente")
            
        except Exception as e:
            print(f"❌ Error generando diagrama de Smith: {e}")

def main():
    """Función principal"""
    print("=" * 60)
    print("   MEDICIÓN DE PARÁMETROS S CON NANOVNA CALIBRADO")
    print("=" * 60)
    
    # Crear instancia de medición
    measurement = VNAMeasurement()
    
    # 1. Conectar al VNA
    if not measurement.connect_vna():
        return
    
    # 2. Cargar calibración
    print("\n📁 Introduce la ruta del archivo de calibración (.cal)")
    cal_file = input("🔸 Archivo de calibración: ")
    
    if not measurement.load_calibration(cal_file):
        print("⚠️  Continuando sin calibración...")
    
    # 3. Configurar barrido
    print("\n⚙️ CONFIGURACIÓN DEL BARRIDO")
    try:
        start_mhz = float(input("Frecuencia inicial [MHz]: "))
        stop_mhz = float(input("Frecuencia final [MHz]: "))
        points = int(input("Número de puntos: "))
        
        if not measurement.configure_sweep(start_mhz, stop_mhz, points):
            return
    except ValueError:
        print("❌ Error: Introduce valores numéricos válidos")
        return
    
    # 4. Medir DUT
    input("\n🔌 Conecta el DUT al VNA y pulsa ENTER para medir...")
    
    dut_name = input("🔸 Nombre del DUT (opcional): ").strip() or "DUT"
    
    if not measurement.measure_dut(dut_name):
        print("❌ No se pudo completar la medición")
        return
    
    # 5. Mostrar resultados
    print(f"\n📊 PARÁMETROS S MEDIDOS PARA {dut_name.upper()}")
    
    # Información de los parámetros
    s_params = measurement.get_s_parameters()
    if not s_params or len(s_params['S11']) == 0:
        print("❌ No hay datos de parámetros S disponibles")
        return
        
    freq = measurement.frequencies
    print(f"📡 Rango de frecuencia: {freq[0]/1e6:.1f} - {freq[-1]/1e6:.1f} MHz")
    print(f"📏 Puntos de medición: {len(freq)}")
    
    for param in ['S11', 'S21']:
        dB = measurement.get_parameter_dB(param)
        mag, phase = measurement.get_parameter_magnitude_phase(param)
        if dB is not None and mag is not None:
            print(f"\n{param}:")
            print(f"  📈 Magnitud: {np.min(mag):.3f} - {np.max(mag):.3f}")
            print(f"  🔊 dB: {np.min(dB):.1f} - {np.max(dB):.1f} dB")
            print(f"  📐 Fase: {np.min(phase):.1f}° - {np.max(phase):.1f}°")
        else:
            print(f"\n{param}: ❌ Datos no disponibles")
    
    # 6. Menú de opciones
    while True:
        print("\n" + "=" * 50)
        print("🎯 OPCIONES DE VISUALIZACIÓN Y GUARDADO")
        print("1. Graficar en dB")
        print("2. Graficar magnitud")
        print("3. Graficar fase")
        print("4. Diagrama de Smith")
        print("5. Guardar como .s2p")
        print("6. Guardar como CSV")
        print("7. Nueva medición")
        print("8. Salir")
        
        opcion = input("\n🔸 Selecciona opción (1-8): ").strip()
        
        if opcion == '1':
            measurement.plot_measurement(['S11', 'S21'], 'dB')
        elif opcion == '2':
            measurement.plot_measurement(['S11', 'S21'], 'magnitude')
        elif opcion == '3':
            measurement.plot_measurement(['S11', 'S21'], 'phase')
        elif opcion == '4':
            measurement.plot_smith_chart()
        elif opcion == '5':
            filename = f"{dut_name}_parametros.s2p"
            measurement.save_s2p_file(filename)
        elif opcion == '6':
            filename = f"{dut_name}_parametros.csv"
            measurement.save_csv_file(filename)
        elif opcion == '7':
            input("\n🔌 Conecta el nuevo DUT y pulsa ENTER...")
            new_dut = input("🔸 Nombre del nuevo DUT: ").strip() or "DUT"
            measurement.measure_dut(new_dut)
            dut_name = new_dut
        elif opcion == '8':
            print("👋 ¡Hasta luego!")
            break
        else:
            print("❌ Opción no válida")

if __name__ == "__main__":
    main()
