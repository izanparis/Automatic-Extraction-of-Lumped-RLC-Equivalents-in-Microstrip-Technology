#!/usr/bin/env python3
"""
NanoVNA S-A-A-2 Controller - Gráficas Corregidas
"""

import serial
import numpy as np
import matplotlib.pyplot as plt
import struct
import time
import sys

class NanoVNA_SAA2:
    def __init__(self, port="COM5", baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.connected = False
        
    def connect(self):
        """Conectar al NanoVNA S-A-A-2"""
        try:
            print(f"🔌 Conectando a {self.port} con {self.baudrate} baud...")
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=2,
                write_timeout=2
            )
            time.sleep(2)
            self.serial.reset_input_buffer()
            
            # Probar comunicación con comando INDICATE (0x0d)
            response = self._send_command(b'\x0d')
            if response == b'2':
                print("✅ Conexión exitosa! (Protocolo S-A-A-2 detectado)")
                self.connected = True
                return True
            else:
                print(f"❌ Dispositivo no responde correctamente: {response}")
                return False
                
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            return False

    def _send_command(self, command_bytes):
        """Enviar comando binario y leer respuesta"""
        self.serial.reset_input_buffer()
        self.serial.write(command_bytes)
        time.sleep(0.1)
        
        # Leer toda la respuesta disponible
        if self.serial.in_waiting > 0:
            return self.serial.read(self.serial.in_waiting)
        return b''

    def clear_fifo(self):
        """Limpiar el FIFO escribiendo cualquier valor a address 0x30"""
        print("🧹 Limpiando FIFO...")
        # WRITE command a address 0x30 para limpiar FIFO
        cmd = bytes([0x20, 0x30, 0x00])
        self._send_command(cmd)
        time.sleep(0.5)

    def setup_sweep(self, start_hz, stop_hz, points=101):
        """Configurar barrido de frecuencia"""
        print(f"📡 Configurando barrido: {start_hz/1e6:.1f}-{stop_hz/1e6:.1f} MHz, {points} puntos")
        
        # Calcular step frequency
        step_hz = (stop_hz - start_hz) / (points - 1) if points > 1 else 0
        
        # Escribir parámetros de sweep (little endian)
        # sweepStartHz (address 0x00-0x07) - uint64
        start_bytes = int(start_hz).to_bytes(8, 'little')
        for i in range(8):
            cmd = bytes([0x20, i, start_bytes[i]])
            self._send_command(cmd)
        
        # sweepStepHz (address 0x10-0x17) - uint64  
        step_bytes = int(step_hz).to_bytes(8, 'little')
        for i in range(8):
            cmd = bytes([0x20, 0x10 + i, step_bytes[i]])
            self._send_command(cmd)
        
        # sweepPoints (address 0x20-0x21) - uint16
        points_bytes = points.to_bytes(2, 'little')
        cmd1 = bytes([0x20, 0x20, points_bytes[0]])
        cmd2 = bytes([0x20, 0x21, points_bytes[1]])
        self._send_command(cmd1)
        self._send_command(cmd2)
        
        # valuesPerFrequency (address 0x22-0x23) - uint16
        values_bytes = (1).to_bytes(2, 'little')
        cmd1 = bytes([0x20, 0x22, values_bytes[0]])
        cmd2 = bytes([0x20, 0x23, values_bytes[1]])
        self._send_command(cmd1)
        self._send_command(cmd2)
        
        time.sleep(1.0)

    def capture_data_smart(self, expected_points=101):
        """Captura inteligente - leer en bloques grandes y procesar"""
        print("📊 Capturando datos (método inteligente)...")
        
        self.clear_fifo()
        time.sleep(2.0)  # Esperar a que se generen datos
        
        # Intentar leer en varios bloques
        all_data = b''
        block_size = 256  # Leer en bloques de 256 bytes (8 puntos)
        
        for attempt in range(5):  # Máximo 5 intentos
            print(f"🔍 Intento {attempt + 1}: Leyendo bloque...")
            
            # READFIFO con tamaño de bloque
            cmd = bytes([0x18, 0x30, block_size & 0xFF, (block_size >> 8) & 0xFF])
            block_data = self._send_command(cmd)
            
            if block_data:
                all_data += block_data
                print(f"   + {len(block_data)} bytes (total: {len(all_data)})")
                
                # Si tenemos suficientes datos, procesar
                if len(all_data) >= expected_points * 32:
                    break
            else:
                print("   - Sin datos nuevos")
            
            time.sleep(0.5)
        
        # Procesar todos los datos
        data_points = []
        for i in range(0, len(all_data), 32):
            chunk = all_data[i:i+32]
            if len(chunk) == 32:
                point_data = self._parse_fifo_data(chunk)
                if point_data:
                    data_points.append(point_data)
        
        # Limitar al número esperado de puntos
        data_points = data_points[:expected_points]
        
        # Generar frecuencias reales basadas en la configuración del sweep
        if data_points:
            start_freq = 1e6  # Asumimos el inicio configurado
            stop_freq = 100e6  # Asumimos el fin configurado
            frequencies = np.linspace(start_freq, stop_freq, len(data_points))
        else:
            frequencies = []
        
        print(f"✅ Capturados {len(data_points)} puntos de {len(all_data)} bytes totales")
        return frequencies, data_points

    def _parse_fifo_data(self, fifo_data):
        """Parsear datos del FIFO (32 bytes)"""
        try:
            if len(fifo_data) != 32:
                return None
            
            # Parsear estructura según UG1101
            fwd0_re = struct.unpack('<i', fifo_data[0:4])[0]
            fwd0_im = struct.unpack('<i', fifo_data[4:8])[0]
            rev0_re = struct.unpack('<i', fifo_data[8:12])[0]   # S11 real
            rev0_im = struct.unpack('<i', fifo_data[12:16])[0]  # S11 imag
            rev1_re = struct.unpack('<i', fifo_data[16:20])[0]  # S21 real
            rev1_im = struct.unpack('<i', fifo_data[20:24])[0]  # S21 imag
            freq_index = struct.unpack('<H', fifo_data[24:26])[0]
            
            # Calcular parámetros S
            reference = complex(fwd0_re, fwd0_im)
            s11_raw = complex(rev0_re, rev0_im)
            s21_raw = complex(rev1_re, rev1_im)
            
            # Aplicar calibración básica
            if abs(reference) > 1e-6:
                s11 = s11_raw / reference
                s21 = s21_raw / reference
            else:
                s11 = complex(0, 0)
                s21 = complex(0, 0)
            
            return {
                'freq_index': freq_index,
                's11': s11,
                's21': s21,
                's11_magnitude': abs(s11),
                's11_phase': np.angle(s11),
                's21_magnitude': abs(s21),
                's21_phase': np.angle(s21),
                'raw_reference': abs(reference)  # Para debug
            }
            
        except Exception as e:
            print(f"❌ Error parseando datos: {e}")
            return None

    def plot_measured_data(self, frequencies, data_points):
        """Graficar datos medidos REALES"""
        if not data_points:
            print("❌ No hay datos para graficar")
            return
        
        # Extraer datos S11
        s11_data = [point['s11'] for point in data_points]
        s11_magnitude = [point['s11_magnitude'] for point in data_points]
        s11_phase = [point['s11_phase'] for point in data_points]
        
        # Convertir frecuencias a MHz para las gráficas
        frequencies_mhz = frequencies / 1e6
        
        # Crear figura con subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
        
        # 1. Carta de Smith
        ax1.set_aspect('equal')
        ax1.grid(True, alpha=0.3)
        
        # Dibujar círculos de Smith
        theta = np.linspace(0, 2*np.pi, 100)
        for r in [0.2, 0.5, 1.0]:
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            ax1.plot(x, y, 'gray', linewidth=0.5, alpha=0.5)
        
        real_parts = [z.real for z in s11_data]
        imag_parts = [z.imag for z in s11_data]
        ax1.plot(real_parts, imag_parts, 'b-', linewidth=2, alpha=0.7, label='S11')
        ax1.plot(real_parts, imag_parts, 'ro', markersize=4, alpha=0.7)
        ax1.set_xlim(-1.1, 1.1)
        ax1.set_ylim(-1.1, 1.1)
        ax1.set_title('S11 - Carta de Smith')
        ax1.set_xlabel('Parte Real')
        ax1.set_ylabel('Parte Imaginaria')
        ax1.legend()
        
        # 2. Magnitud en dB
        magnitude_db = 20 * np.log10(np.maximum(s11_magnitude, 1e-6))
        ax2.plot(frequencies_mhz, magnitude_db, 'b-', linewidth=2, marker='o', markersize=3)
        ax2.grid(True, alpha=0.3)
        ax2.set_title('S11 - Magnitud')
        ax2.set_xlabel('Frecuencia (MHz)')
        ax2.set_ylabel('Magnitud (dB)')
        
        # 3. Fase
        phase_deg = np.degrees(s11_phase)
        ax3.plot(frequencies_mhz, phase_deg, 'g-', linewidth=2, marker='o', markersize=3)
        ax3.grid(True, alpha=0.3)
        ax3.set_title('S11 - Fase')
        ax3.set_xlabel('Frecuencia (MHz)')
        ax3.set_ylabel('Fase (grados)')
        
        # 4. VSWR
        vswr = [(1 + mag) / (1 - mag) if mag < 0.99 else 10 for mag in s11_magnitude]
        ax4.plot(frequencies_mhz, vswr, 'r-', linewidth=2, marker='o', markersize=3)
        ax4.grid(True, alpha=0.3)
        ax4.set_title('VSWR')
        ax4.set_xlabel('Frecuencia (MHz)')
        ax4.set_ylabel('VSWR')
        ax4.set_ylim(1, min(10, max(vswr) * 1.1))
        
        plt.suptitle(f'MEDICIÓN REAL - NanoVNA S-A-A-2\n{len(data_points)} puntos capturados', 
                    fontweight='bold', fontsize=14)
        plt.tight_layout()
        plt.show()
        
        # Mostrar información de debug
        self._print_debug_info(data_points)

    def _print_debug_info(self, data_points):
        """Mostrar información de debug de los datos capturados"""
        print("\n📊 INFORMACIÓN DE LOS DATOS CAPTURADOS:")
        print(f"   • Puntos totales: {len(data_points)}")
        
        if data_points:
            first_point = data_points[0]
            last_point = data_points[-1]
            
            print(f"   • Rango de freq_index: {first_point['freq_index']} - {last_point['freq_index']}")
            print(f"   • Referencia (primer punto): {first_point['raw_reference']:.2f}")
            print(f"   • S11 magnitude range: {min(p['s11_magnitude'] for p in data_points):.3f} - {max(p['s11_magnitude'] for p in data_points):.3f}")
            print(f"   • S11 phase range: {min(np.degrees(p['s11_phase']) for p in data_points):.1f}° - {max(np.degrees(p['s11_phase']) for p in data_points):.1f}°")

    def plot_simple_demo(self):
        """Mostrar datos de demostración"""
        print("📈 Mostrando datos de demostración...")
        
        # Crear datos de ejemplo
        frequencies = np.linspace(1e6, 100e6, 11)
        
        # Simular respuesta de una antena resonante
        f_center = 50e6
        f_span = 99e6
        
        # Crear una respuesta resonante
        s11_magnitude = 0.8 * np.exp(-((frequencies - f_center) / (f_span / 4))**2) + 0.2
        s11_phase = np.pi * (frequencies - f_center) / f_span
        s11_data = s11_magnitude * np.exp(1j * s11_phase)
        
        # Usar la misma función de graficado pero con datos de demo
        self._plot_demo_data(frequencies, s11_data)

    def _plot_demo_data(self, frequencies, s11_data):
        """Graficar datos de demostración"""
        frequencies_mhz = frequencies / 1e6
        s11_magnitude = np.abs(s11_data)
        s11_phase = np.angle(s11_data)
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
        
        # Carta de Smith
        ax1.set_aspect('equal')
        theta = np.linspace(0, 2*np.pi, 100)
        for r in [0.2, 0.5, 1.0]:
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            ax1.plot(x, y, 'gray', linewidth=0.5, alpha=0.5)
        
        real_parts = [z.real for z in s11_data]
        imag_parts = [z.imag for z in s11_data]
        ax1.plot(real_parts, imag_parts, 'b-', linewidth=2, marker='o')
        ax1.set_title('S11 - Carta de Smith (Demo)')
        ax1.grid(True, alpha=0.3)
        
        # Magnitud
        magnitude_db = 20 * np.log10(np.maximum(s11_magnitude, 1e-6))
        ax2.plot(frequencies_mhz, magnitude_db, 'b-', linewidth=2, marker='o')
        ax2.set_title('S11 - Magnitud (dB)')
        ax2.set_xlabel('Frecuencia (MHz)')
        ax2.grid(True, alpha=0.3)
        
        # Fase
        phase_deg = np.degrees(s11_phase)
        ax3.plot(frequencies_mhz, phase_deg, 'g-', linewidth=2, marker='o')
        ax3.set_title('S11 - Fase (grados)')
        ax3.set_xlabel('Frecuencia (MHz)')
        ax3.grid(True, alpha=0.3)
        
        # VSWR
        vswr = (1 + s11_magnitude) / (1 - s11_magnitude)
        ax4.plot(frequencies_mhz, vswr, 'r-', linewidth=2, marker='o')
        ax4.set_title('VSWR')
        ax4.set_xlabel('Frecuencia (MHz)')
        ax4.set_ylim(1, 5)
        ax4.grid(True, alpha=0.3)
        
        plt.suptitle('DATOS DE DEMOSTRACIÓN', fontweight='bold', color='blue')
        plt.tight_layout()
        plt.show()

def main():
    print("=" * 60)
    print("    NANOVNA S-A-A-2 - ¡FUNCIONANDO!")
    print("=" * 60)
    
    nv = NanoVNA_SAA2("COM5", 9600)
    
    if not nv.connect():
        return
    
    try:
        while True:
            print("\n" + "="*50)
            print("1. 📊 Capturar y graficar datos REALES")
            print("2. 📈 Mostrar datos de demostración")
            print("3. 🚪 Salir")
            
            opcion = input("\nSelecciona opción (1-3): ").strip()
            
            if opcion == '1':
                print("\n🎯 Capturando datos reales del NanoVNA...")
                nv.setup_sweep(1e6, 100e6, 11)
                frequencies, data = nv.capture_data_smart(11)
                
                if data:
                    print("✅ ¡Datos capturados exitosamente! Mostrando gráficas...")
                    nv.plot_measured_data(frequencies, data)
                else:
                    print("❌ No se pudieron capturar datos. Mostrando demo...")
                    nv.plot_simple_demo()
                    
            elif opcion == '2':
                nv.plot_simple_demo()
                
            elif opcion == '3':
                break
            else:
                print("❌ Opción no válida")
                
    except KeyboardInterrupt:
        print("\n👋 Interrumpido por usuario")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if nv.serial:
            nv.serial.close()
        print("🔌 Desconectado")

if __name__ == "__main__":
    main()