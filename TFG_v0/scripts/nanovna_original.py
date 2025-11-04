#!/usr/bin/env python3
"""
NanoVNA S-A-A-2 - Control Simple
Interfaz minimalista con control total de parámetros
"""

import serial
import numpy as np
import matplotlib.pyplot as plt
import struct
import time
import sys

class NanoVNA_Simple:
    def __init__(self, port="COM5", baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        
    def connect(self):
        """Conectar al NanoVNA"""
        try:
            print(f"🔌 Conectando a {self.port}...")
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=2
            )
            time.sleep(2)
            self.serial.reset_input_buffer()
            
            # Test connection
            response = self._send_command(b'\x0d')
            if response == b'2':
                print("✅ Conectado!")
                return True
            else:
                print("❌ Error de conexión")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    def _send_command(self, command_bytes):
        """Enviar comando"""
        self.serial.reset_input_buffer()
        self.serial.write(command_bytes)
        time.sleep(0.1)
        
        if self.serial.in_waiting > 0:
            return self.serial.read(self.serial.in_waiting)
        return b''

    def setup_sweep(self, start_hz, stop_hz, points):
        """Configurar barrido"""
        step_hz = (stop_hz - start_hz) / (points - 1) if points > 1 else 0
        
        # Configurar parámetros
        start_bytes = int(start_hz).to_bytes(8, 'little')
        for i in range(8):
            self._send_command(bytes([0x20, i, start_bytes[i]]))
        
        step_bytes = int(step_hz).to_bytes(8, 'little')
        for i in range(8):
            self._send_command(bytes([0x20, 0x10 + i, step_bytes[i]]))
        
        points_bytes = points.to_bytes(2, 'little')
        self._send_command(bytes([0x20, 0x20, points_bytes[0]]))
        self._send_command(bytes([0x20, 0x21, points_bytes[1]]))
        
        self._send_command(bytes([0x20, 0x22, 1]))  # 1 valor por frecuencia
        self._send_command(bytes([0x20, 0x23, 0]))
        
        time.sleep(0.5)

    def capture_data(self, points):
        """Capturar datos"""
        print("📊 Capturando...")
        
        # Limpiar FIFO
        self._send_command(bytes([0x20, 0x30, 0x00]))
        time.sleep(1)
        
        # Leer datos
        cmd = bytes([0x18, 0x30, 0x00, 0x04])  # 1024 bytes
        data = self._send_command(cmd)
        
        # Procesar
        measurements = []
        for i in range(0, len(data), 32):
            chunk = data[i:i+32]
            if len(chunk) == 32:
                measurement = self._parse_data(chunk)
                if measurement:
                    measurements.append(measurement)
        
        return measurements[:points]

    def _parse_data(self, data):
        """Parsear datos del FIFO"""
        try:
            fwd0_re = struct.unpack('<i', data[0:4])[0]
            fwd0_im = struct.unpack('<i', data[4:8])[0]
            rev0_re = struct.unpack('<i', data[8:12])[0]
            rev0_im = struct.unpack('<i', data[12:16])[0]
            
            reference = complex(fwd0_re, fwd0_im)
            s11_raw = complex(rev0_re, rev0_im)
            
            if abs(reference) > 1e-6:
                s11 = s11_raw / reference
            else:
                s11 = complex(0, 0)
            
            return {
                's11': s11,
                'magnitude': abs(s11),
                'phase': np.angle(s11)
            }
        except:
            return None

    def plot_results(self, start_hz, stop_hz, measurements):
        """Mostrar resultados"""
        if not measurements:
            print("❌ No hay datos")
            return
            
        frequencies = np.linspace(start_hz, stop_hz, len(measurements))
        freqs_mhz = frequencies / 1e6
        
        s11_data = [m['s11'] for m in measurements]
        magnitude = [m['magnitude'] for m in measurements]
        phase = [m['phase'] for m in measurements]
        
        # Crear gráficas
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
        
        # 1. Carta de Smith
        ax1.set_aspect('equal')
        theta = np.linspace(0, 2*np.pi, 100)
        for r in [0.2, 0.5, 1.0]:
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            ax1.plot(x, y, 'gray', linewidth=0.5, alpha=0.5)
        
        real = [z.real for z in s11_data]
        imag = [z.imag for z in s11_data]
        ax1.plot(real, imag, 'b-', linewidth=2)
        ax1.plot(real, imag, 'ro', markersize=2)
        ax1.set_title('Carta de Smith - S11')
        ax1.grid(True)
        
        # 2. Magnitud
        magnitude_db = 20 * np.log10(np.maximum(magnitude, 1e-6))
        ax2.plot(freqs_mhz, magnitude_db, 'b-', linewidth=2)
        ax2.set_title('Magnitud S11 (dB)')
        ax2.set_xlabel('Frecuencia (MHz)')
        ax2.grid(True)
        
        # 3. Fase
        phase_deg = np.degrees(phase)
        ax3.plot(freqs_mhz, phase_deg, 'g-', linewidth=2)
        ax3.set_title('Fase S11 (grados)')
        ax3.set_xlabel('Frecuencia (MHz)')
        ax3.grid(True)
        
        # 4. VSWR
        vswr = [(1 + m) / (1 - m) if m < 0.99 else 10 for m in magnitude]
        ax4.plot(freqs_mhz, vswr, 'r-', linewidth=2)
        ax4.set_title('VSWR')
        ax4.set_xlabel('Frecuencia (MHz)')
        ax4.set_ylim(1, min(10, max(vswr) * 1.1))
        ax4.grid(True)
        
        plt.tight_layout()
        plt.show()

def get_float_input(prompt, default=0):
    """Obtener entrada float con valor por defecto"""
    try:
        value = input(f"{prompt} [{default}]: ").strip()
        return float(value) if value else default
    except:
        return default

def get_int_input(prompt, default=0):
    """Obtener entrada int con valor por defecto"""
    try:
        value = input(f"{prompt} [{default}]: ").strip()
        return int(value) if value else default
    except:
        return default

def main():
    print("=" * 50)
    print("    NANOVNA - CONTROL SIMPLE")
    print("=" * 50)
    
    # Configuración inicial
    port = input("Puerto COM [COM5]: ").strip() or "COM5"
    baudrate = get_int_input("Baudrate", 9600)
    
    nv = NanoVNA_Simple(port, baudrate)
    
    if not nv.connect():
        return
    
    try:
        while True:
            print("\n" + "="*40)
            print("🏠 MENU PRINCIPAL")
            print("="*40)
            print("1. 📡 Configurar y Medir")
            print("2. 🚪 Salir")
            
            choice = input("\nElige opción [1]: ").strip() or "1"
            
            if choice == "1":
                print("\n🎯 CONFIGURACIÓN DE BARRIDO")
                print("-" * 30)
                
                # Obtener parámetros
                start_mhz = get_float_input("Frecuencia inicial (MHz)", 1)
                stop_mhz = get_float_input("Frecuencia final (MHz)", 100)
                points = get_int_input("Número de puntos", 101)
                
                # Validar
                if start_mhz >= stop_mhz:
                    print("❌ Error: Frecuencia inicial debe ser menor que final")
                    continue
                    
                if points < 2 or points > 1001:
                    print("❌ Error: Puntos debe estar entre 2 y 1001")
                    continue
                
                # Convertir a Hz
                start_hz = start_mhz * 1e6
                stop_hz = stop_mhz * 1e6
                
                print(f"\n⚡ Configurando: {start_mhz}-{stop_mhz} MHz, {points} puntos")
                
                # Configurar y medir
                nv.setup_sweep(start_hz, stop_hz, points)
                measurements = nv.capture_data(points)
                
                if measurements:
                    print(f"✅ {len(measurements)} puntos capturados")
                    nv.plot_results(start_hz, stop_hz, measurements)
                else:
                    print("❌ No se capturaron datos")
                    
            elif choice == "2":
                break
            else:
                print("❌ Opción no válida")
                
    except KeyboardInterrupt:
        print("\n👋 Saliendo...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if nv.serial:
            nv.serial.close()
        print("🔌 Desconectado")

if __name__ == "__main__":
    main()