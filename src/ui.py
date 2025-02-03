import sys
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                            QWidget, QPushButton, QComboBox, QDialog, QLineEdit, 
                            QFormLayout, QCheckBox, QGroupBox, QHBoxLayout, 
                            QTabWidget, QScrollArea)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
import mss
import numpy as np
import cv2
from datetime import datetime
import os
import sounddevice as sd
import wave
import subprocess
import time
from time import sleep
import win32gui
import win32ui
import win32con
import win32api
from ctypes import windll

def capture_cursor():
    """Captura la posición y la imagen del cursor."""
    try:
        cursor_info = win32gui.GetCursorInfo()
        hcursor = cursor_info[1]
        pos = win32api.GetCursorPos()
        
        # Crear DC y bitmap para el cursor
        hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        hbmp = win32ui.CreateBitmap()
        hbmp.CreateCompatibleBitmap(hdc, 32, 32)
        
        # Crear DC compatible para dibujar
        hdc_mem = hdc.CreateCompatibleDC()
        hdc_mem.SelectObject(hbmp)
        
        # Dibujar el cursor
        hdc_mem.DrawIcon((0, 0), hcursor)
        
        # Convertir a array de numpy
        bmp_bits = hbmp.GetBitmapBits(True)
        cursor_img = np.frombuffer(bmp_bits, dtype=np.uint8).reshape(32, 32, 4)
        
        # Limpiar
        win32gui.DeleteObject(hbmp.GetHandle())
        hdc_mem.DeleteDC()
        hdc.DeleteDC()
        
        return cursor_img, pos
    except Exception as e:
        print(f"Error al capturar cursor: {str(e)}")
        return None, None

class ScreenCaptureThread(QThread):
    update_image_signal = pyqtSignal(object)

    def __init__(self, monitor, fps):
        super().__init__()
        self.monitor = monitor
        self.fps = fps
        self.running = True

    def run(self):
        with mss.mss() as sct:
            while self.running:
                try:
                    start_time = time.time()
                    
                    # Capturar pantalla
                    monitor_dict = {
                        'top': self.monitor['top'],
                        'left': self.monitor['left'],
                        'width': self.monitor['width'],
                        'height': self.monitor['height'],
                        'mon': self.monitor['mon']
                    }
                    
                    screenshot = np.array(sct.grab(monitor_dict))
                    
                    # Capturar cursor
                    cursor_img, cursor_pos = capture_cursor()
                    
                    if cursor_img is not None and cursor_pos is not None:
                        # Ajustar posición del cursor relativa al monitor
                        cursor_x = cursor_pos[0] - self.monitor['left']
                        cursor_y = cursor_pos[1] - self.monitor['top']
                        
                        # Verificar si el cursor está dentro de la pantalla capturada
                        if (0 <= cursor_x < self.monitor['width'] - 32 and 
                            0 <= cursor_y < self.monitor['height'] - 32):
                            
                            # Crear una máscara alpha del cursor
                            cursor_alpha = cursor_img[..., 3:] / 255.0
                            cursor_rgb = cursor_img[..., :3]
                            
                            # Región donde se dibujará el cursor
                            roi = screenshot[cursor_y:cursor_y+32, cursor_x:cursor_x+32]
                            
                            # Combinar cursor con la imagen
                            for c in range(3):  # Para cada canal de color
                                roi[..., c] = (roi[..., c] * (1 - cursor_alpha[..., 0]) + 
                                             cursor_rgb[..., c] * cursor_alpha[..., 0])
                    
                    self.update_image_signal.emit(screenshot)
                    
                    # Control de FPS
                    elapsed_time = time.time() - start_time
                    sleep_time = max(0, (1 / self.fps) - elapsed_time)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                        
                except Exception as e:
                    print(f"Error en captura: {str(e)}")
                    time.sleep(1/self.fps)  # Esperar antes de reintentar

    def stop(self):
        self.running = False

class AudioSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Configuración de Audio")
        self.setGeometry(150, 150, 500, 400)
        self.selected_speakers = []
        self.selected_mics = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Crear el widget de pestañas
        tab_widget = QTabWidget()

        # Pestaña de Micrófonos
        mic_tab = QWidget()
        mic_layout = QVBoxLayout()
        
        # Crear área de desplazamiento para micrófonos
        mic_scroll = QScrollArea()
        mic_scroll.setWidgetResizable(True)
        mic_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        mic_container = QWidget()
        mic_container_layout = QVBoxLayout()
        
        for device in self.parent.audio_devices['mics']:
            checkbox = QCheckBox(device['name'])
            checkbox.setChecked(any(d['id'] == device['id'] for d in self.parent.selected_mics))
            checkbox.stateChanged.connect(lambda state, d=device: self.toggle_microphone(state, d))
            mic_container_layout.addWidget(checkbox)
        
        # Agregar espacio expansible al final
        mic_container_layout.addStretch()
        mic_container.setLayout(mic_container_layout)
        mic_scroll.setWidget(mic_container)
        mic_layout.addWidget(mic_scroll)
        mic_tab.setLayout(mic_layout)

        # Pestaña de Salida de Audio
        speaker_tab = QWidget()
        speaker_layout = QVBoxLayout()
        
        # Crear área de desplazamiento para parlantes
        speaker_scroll = QScrollArea()
        speaker_scroll.setWidgetResizable(True)
        speaker_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        speaker_container = QWidget()
        speaker_container_layout = QVBoxLayout()
        
        for device in self.parent.audio_devices['speakers']:
            checkbox = QCheckBox(device['name'])
            checkbox.setChecked(any(d['id'] == device['id'] for d in self.parent.selected_speakers))
            checkbox.stateChanged.connect(lambda state, d=device: self.toggle_speaker(state, d))
            speaker_container_layout.addWidget(checkbox)
        
        # Agregar espacio expansible al final
        speaker_container_layout.addStretch()
        speaker_container.setLayout(speaker_container_layout)
        speaker_scroll.setWidget(speaker_container)
        speaker_layout.addWidget(speaker_scroll)
        speaker_tab.setLayout(speaker_layout)

        # Agregar pestañas al widget de pestañas
        tab_widget.addTab(mic_tab, "Micrófonos")
        tab_widget.addTab(speaker_tab, "Salida de Audio")
        
        layout.addWidget(tab_widget)

        # Botones de Aceptar/Cancelar
        button_layout = QHBoxLayout()
        
        accept_button = QPushButton("Aceptar")
        accept_button.clicked.connect(self.accept)
        button_layout.addWidget(accept_button)
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def toggle_speaker(self, state, device):
        if state:
            self.selected_speakers.append(device)
        else:
            self.selected_speakers = [d for d in self.selected_speakers if d['id'] != device['id']]

    def toggle_microphone(self, state, device):
        if state:
            self.selected_mics.append(device)
        else:
            self.selected_mics = [d for d in self.selected_mics if d['id'] != device['id']]

    def accept(self):
        self.parent.selected_speakers = self.selected_speakers
        self.parent.selected_mics = self.selected_mics
        super().accept()

class StreamApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screen Streamer")
        self.setGeometry(100, 100, 800, 600)
        self.screens = []
        self.current_screen = None
        self.preview_label = QLabel(self)
        self.capture_thread = None
        self.is_recording = False
        self.video_writer = None
        self.audio_devices = self.get_audio_devices()
        self.selected_speakers = []
        self.selected_mics = []
        self.audio_stream = None
        self.audio_settings_dialog = None
        self.temp_dir = None  # Para archivos temporales
        self.ffmpeg_processes = {}  # Para almacenar los procesos de FFmpeg
        
        # Crear carpeta de grabaciones en el directorio del usuario
        self.output_dir = os.path.join(os.path.expanduser('~'), 'ScreenRecordings')
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        self.current_frame = None
        self.wav_files = {}
        self.init_ui()

    def get_audio_devices(self):
        """Obtiene la lista de dispositivos de audio disponibles."""
        devices = {'speakers': [], 'mics': []}
        try:
            device_list = sd.query_devices()
            default_input = sd.default.device[0]
            default_output = sd.default.device[1]
            
            for i, device in enumerate(device_list):
                device_info = {
                    'id': i,
                    'name': device['name'],
                    'channels': device.get('max_output_channels', 0),
                    'is_default': (i == default_input or i == default_output)
                }
                
                if device.get('max_output_channels', 0) > 0:
                    devices['speakers'].append(device_info)
                if device.get('max_input_channels', 0) > 0:
                    devices['mics'].append(device_info)
            
            print("Dispositivos de audio disponibles:")
            print(f"Micrófono predeterminado: {device_list[default_input]['name']}")
            print(f"Parlante predeterminado: {device_list[default_output]['name']}")
            
        except Exception as e:
            print(f"Error al obtener dispositivos de audio: {str(e)}")
        return devices

    def init_ui(self):
        layout = QVBoxLayout()

        # Botón para configuración de audio
        audio_button = QPushButton("Configuración de Audio", self)
        audio_button.clicked.connect(self.show_audio_settings)
        layout.addWidget(audio_button)

        # Resto de la UI existente
        self.screen_selector = QComboBox(self)
        self.screen_selector.currentIndexChanged.connect(self.update_screen_selection)
        layout.addWidget(self.screen_selector)

        self.preview_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview_label)

        self.add_keys_button = QPushButton("Agregar Claves", self)
        self.add_keys_button.clicked.connect(self.show_add_keys_dialog)
        layout.addWidget(self.add_keys_button)

        self.record_button = QPushButton("Iniciar Grabación")
        self.record_button.clicked.connect(self.toggle_recording)
        layout.addWidget(self.record_button)

        central_widget = QWidget(self)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.update_screen_list()
    
    

    def update_screen_list(self):
        self.screens = get_screen_list()
        self.screen_selector.clear()
        for i, screen in enumerate(self.screens):
            self.screen_selector.addItem(f"{screen['name']} (Monitor {i + 1})")
        
        if len(self.screens) > 0:
            self.current_screen = 0
            self.screen_selector.setCurrentIndex(self.current_screen)

    def update_screen_selection(self):
        self.current_screen = self.screen_selector.currentIndex()
        if self.capture_thread is not None:
            self.capture_thread.stop()
        self.start_capture_thread()

    def start_capture_thread(self):
        if self.current_screen is not None:
            monitor = self.screens[self.current_screen]['monitor']
            fps = 30  # Definir FPS constante
            self.capture_thread = ScreenCaptureThread(monitor, fps)
            self.capture_thread.update_image_signal.connect(self.update_preview)
            self.capture_thread.start()

    def update_preview(self, screenshot=None):
        if screenshot is not None:
            try:
                # La imagen viene en formato BGRA
                height, width = screenshot.shape[:2]
                
                # Para la previsualización (convertir de BGRA a RGB)
                preview_frame = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2RGB)
                bytes_per_line = 3 * width
                preview_image = QImage(preview_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(preview_image)
                self.preview_label.setPixmap(pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio))

                # Para la grabación (convertir de BGRA a BGR)
                if self.is_recording and self.video_writer is not None:
                    record_frame = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
                    self.video_writer.write(record_frame)
            except Exception as e:
                print(f"Error en update_preview: {str(e)}")
                if self.is_recording and self.video_writer is not None:
                    try:
                        print("Intentando grabar frame sin procesar...")
                        self.video_writer.write(cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR))
                    except Exception as e2:
                        print(f"Error al grabar frame sin procesar: {str(e2)}")

    def show_add_keys_dialog(self):
        dialog = AddKeysDialog(self)
        dialog.exec_()

    def show_audio_settings(self):
        if not self.audio_settings_dialog:
            self.audio_settings_dialog = AudioSettingsDialog(self)
        self.audio_settings_dialog.selected_speakers = self.selected_speakers.copy()
        self.audio_settings_dialog.selected_mics = self.selected_mics.copy()
        self.audio_settings_dialog.exec_()

    def start_audio_recording(self, filename_base):
        if not (self.selected_speakers or self.selected_mics):
            print("No hay dispositivos de audio seleccionados")
            return

        self.wav_files = {}
        
        try:
            # Verificar dispositivos antes de iniciar
            print("\n=== Verificación de dispositivos de audio ===")

            # Configurar micrófono
            if self.selected_mics:
                mic_id = self.selected_mics[0]['id']
                mic_info = sd.query_devices(mic_id)
                print(f"\nMicrófono seleccionado:")
                print(f"ID: {mic_id}")
                print(f"Nombre: {mic_info['name']}")
                
                try:
                    self.wav_files['mic'] = wave.open(f"{filename_base}_mic.wav", 'wb')
                    self.wav_files['mic'].setnchannels(2)
                    self.wav_files['mic'].setsampwidth(2)
                    self.wav_files['mic'].setframerate(44100)

                    def mic_callback(indata, frames, time, status):
                        if status:
                            print(f"Estado del micrófono: {status}")
                        if self.is_recording and len(indata) > 0:
                            try:
                                data = (indata * 32767).astype(np.int16)
                                self.wav_files['mic'].writeframes(data.tobytes())
                            except Exception as e:
                                print(f"Error en callback de micrófono: {str(e)}")

                    self.mic_stream = sd.InputStream(
                        device=mic_id,
                        channels=2,
                        callback=mic_callback,
                        samplerate=44100,
                        blocksize=4096,
                        dtype=np.float32
                    )
                    self.mic_stream.start()
                    print("✓ Stream de micrófono iniciado correctamente")
                except Exception as e:
                    print(f"✗ Error al configurar micrófono: {str(e)}")
                    if 'mic' in self.wav_files:
                        self.wav_files['mic'].close()
                        del self.wav_files['mic']
                    self.mic_stream = None

            # Configurar audio del sistema
            if self.selected_speakers:
                try:
                    speaker_id = self.selected_speakers[0]['id']
                    speaker_info = sd.query_devices(speaker_id)
                    print(f"\nConfigurando grabación de audio del sistema:")
                    print(f"ID: {speaker_id}")
                    print(f"Nombre: {speaker_info['name']}")

                    # Buscar el dispositivo de salida predeterminado
                    devices = sd.query_devices()
                    default_output = None
                    for i, device in enumerate(devices):
                        if device.get('max_output_channels', 0) > 0:
                            if 'default' in device['name'].lower() or i == sd.default.device[1]:
                                default_output = (i, device)
                                break
                    
                    if not default_output:
                        # Si no encontramos el default, usar el primer dispositivo con salida
                        for i, device in enumerate(devices):
                            if device.get('max_output_channels', 0) > 0:
                                default_output = (i, device)
                                break
                    
                    if not default_output:
                        raise Exception("No se encontró dispositivo de salida de audio")

                    device_id, device_info = default_output
                    print(f"\nUsando dispositivo para captura: {device_info['name']} (ID: {device_id})")

                    self.wav_files['speakers'] = wave.open(f"{filename_base}_speakers.wav", 'wb')
                    self.wav_files['speakers'].setnchannels(2)
                    self.wav_files['speakers'].setsampwidth(2)
                    self.wav_files['speakers'].setframerate(44100)

                    def speaker_callback(indata, frames, time, status):
                        if status:
                            print(f"Estado del audio del sistema: {status}")
                        if self.is_recording and len(indata) > 0:
                            try:
                                # Normalizar y amplificar el audio
                                normalized = np.clip(indata * 4, -1, 1)  # Multiplicar por 4 para aumentar volumen
                                data = (normalized * 32767).astype(np.int16)
                                self.wav_files['speakers'].writeframes(data.tobytes())
                            except Exception as e:
                                print(f"Error en callback de audio del sistema: {str(e)}")

                    # Configurar el stream de audio usando WASAPI
                    print(f"Iniciando grabación con dispositivo ID: {device_id}")
                    try:
                        # Intentar primero con WASAPI
                        self.speaker_stream = sd.InputStream(
                            device=f'wasapi:{device_info["name"]}',
                            channels=2,
                            callback=speaker_callback,
                            samplerate=44100,
                            blocksize=2048,
                            dtype=np.float32,
                            extra_settings={'wasapi_exclusive': False, 'wasapi_loopback': True}
                        )
                        self.speaker_stream.start()
                        print("✓ Grabación de audio del sistema iniciada correctamente (WASAPI)")
                    except Exception as e1:
                        print(f"Error al iniciar WASAPI: {str(e1)}")
                        print("Intentando método alternativo 1...")
                        try:
                            # Intentar con método directo de sounddevice
                            self.speaker_stream = sd.InputStream(
                                device=device_id,
                                channels=2,
                                callback=speaker_callback,
                                samplerate=44100,
                                blocksize=2048,
                                dtype=np.float32
                            )
                            self.speaker_stream.start()
                            print("✓ Grabación de audio del sistema iniciada correctamente (método directo)")
                        except Exception as e2:
                            print(f"Error en método alternativo 1: {str(e2)}")
                            print("Intentando método alternativo 2 (PyAudio)...")
                            try:
                                import pyaudio
                                
                                # Inicializar PyAudio
                                p = pyaudio.PyAudio()
                                
                                # Buscar el dispositivo de loopback
                                loopback_device = None
                                for i in range(p.get_device_count()):
                                    dev_info = p.get_device_info_by_index(i)
                                    print(f"Dispositivo PyAudio {i}: {dev_info['name']}")
                                    if (dev_info['maxInputChannels'] > 0 and
                                        ('stereo mix' in dev_info['name'].lower() or
                                         'what u hear' in dev_info['name'].lower() or
                                         'voicemeeter' in dev_info['name'].lower() or
                                         'wasapi' in dev_info['name'].lower())):
                                        loopback_device = i
                                        break
                                
                                if loopback_device is None:
                                    # Si no encontramos un dispositivo específico, usar el predeterminado
                                    loopback_device = p.get_default_input_device_info()['index']
                                
                                def pyaudio_callback(in_data, frame_count, time_info, status):
                                    if self.is_recording:
                                        try:
                                            # Convertir los bytes a numpy array
                                            audio_data = np.frombuffer(in_data, dtype=np.int16)
                                            # Normalizar a float32
                                            normalized = audio_data.astype(np.float32) / 32768.0
                                            # Amplificar y volver a convertir a int16
                                            amplified = np.clip(normalized * 4, -1, 1)
                                            data = (amplified * 32767).astype(np.int16)
                                            self.wav_files['speakers'].writeframes(data.tobytes())
                                        except Exception as e:
                                            print(f"Error en callback de PyAudio: {str(e)}")
                                    return (in_data, pyaudio.paContinue)
                                
                                # Configurar y iniciar el stream de PyAudio
                                self.speaker_stream = p.open(
                                    format=pyaudio.paInt16,
                                    channels=2,
                                    rate=44100,
                                    input=True,
                                    input_device_index=loopback_device,
                                    frames_per_buffer=2048,
                                    stream_callback=pyaudio_callback
                                )
                                self.speaker_stream.start_stream()
                                print("✓ Grabación de audio del sistema iniciada correctamente (PyAudio)")
                                
                                # Guardar la instancia de PyAudio para cerrarla después
                                self.pyaudio_instance = p
                                
                            except Exception as e3:
                                print(f"Error en método alternativo 2: {str(e3)}")
                                raise Exception("No se pudo iniciar la captura de audio del sistema")
                        
                except Exception as e:
                    print(f"✗ Error al configurar audio del sistema: {str(e)}")
                    print(f"Detalles del error: {str(e)}")
                    if 'speakers' in self.wav_files:
                        self.wav_files['speakers'].close()
                        del self.wav_files['speakers']
                    self.speaker_stream = None

            # Verificar si al menos un stream se inició correctamente
            if not (hasattr(self, 'mic_stream') or hasattr(self, 'speaker_stream')):
                print("\n✗ No se pudo iniciar ningún stream de audio")
                raise Exception("No se pudo iniciar la grabación de audio")

            print("\n=== Resumen de grabación de audio ===")
            print(f"Micrófono activo: {'Sí' if hasattr(self, 'mic_stream') and self.mic_stream is not None else 'No'}")
            print(f"Audio del sistema activo: {'Sí' if hasattr(self, 'speaker_stream') and self.speaker_stream is not None else 'No'}")

        except Exception as e:
            print(f"\n✗ Error al iniciar la grabación de audio: {str(e)}")
            self.stop_audio_recording()

    def stop_audio_recording(self):
        try:
            # Primero detener la grabación
            self.is_recording = False
            
            # Esperar un momento para que los callbacks terminen
            time.sleep(0.1)
            
            # Detener y cerrar streams
            if hasattr(self, 'mic_stream') and self.mic_stream is not None:
                try:
                    self.mic_stream.stop()
                    self.mic_stream.close()
                except Exception as e:
                    print(f"Error al cerrar stream de micrófono: {str(e)}")
                finally:
                    self.mic_stream = None

            if hasattr(self, 'speaker_stream') and self.speaker_stream is not None:
                try:
                    # Verificar si es un stream de PyAudio
                    if hasattr(self, 'pyaudio_instance'):
                        if self.speaker_stream.is_active():
                            self.speaker_stream.stop_stream()
                        self.speaker_stream.close()
                        self.pyaudio_instance.terminate()
                        del self.pyaudio_instance
                    else:
                        # Stream de sounddevice
                        self.speaker_stream.stop()
                        self.speaker_stream.close()
                except Exception as e:
                    print(f"Error al cerrar stream de audio del sistema: {str(e)}")
                finally:
                    self.speaker_stream = None

            # Esperar otro momento antes de cerrar los archivos
            time.sleep(0.1)
            
            # Cerrar archivos WAV
            if hasattr(self, 'wav_files'):
                for key, wav_file in self.wav_files.items():
                    try:
                        if hasattr(wav_file, 'flush'):
                            wav_file.flush()
                        wav_file.close()
                        print(f"Archivo WAV {key} cerrado correctamente")
                    except Exception as e:
                        print(f"Error al cerrar archivo WAV {key}: {str(e)}")
                self.wav_files = {}

            print("Grabación de audio detenida correctamente")
        except Exception as e:
            print(f"Error al detener la grabación de audio: {str(e)}")

    def toggle_recording(self):
        if not self.is_recording:
            # Crear carpeta y nombre de archivo
            date_folder = datetime.now().strftime("%Y-%m-%d")
            recording_dir = os.path.join(self.output_dir, date_folder)
            os.makedirs(recording_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%H-%M-%S")
            filename_base = os.path.join(recording_dir, f"recording_{timestamp}")
            temp_video = f"{filename_base}_temp.avi"
            final_output = f"{filename_base}.avi"
            
            try:
                # Iniciar grabación de video
                self.video_writer = cv2.VideoWriter(
                    temp_video,
                    cv2.VideoWriter_fourcc(*'XVID'),
                    30.0,
                    (self.screens[self.current_screen]['monitor']['width'],
                     self.screens[self.current_screen]['monitor']['height'])
                )
                
                if not self.video_writer.isOpened():
                    print(f"Error: No se pudo crear el archivo de video")
                    return
                
                # Iniciar grabación de audio
                self.is_recording = True  # Establecer is_recording antes de iniciar el audio
                self.start_audio_recording(filename_base)
                
                self.record_button.setText("Detener Grabación")
                self.current_recording = {
                    'video': temp_video,
                    'mic': f"{filename_base}_mic.wav" if self.selected_mics else None,
                    'speakers': f"{filename_base}_speakers.wav" if self.selected_speakers else None,
                    'final': final_output
                }
                print(f"Iniciando grabación en: {filename_base}")
            except Exception as e:
                print(f"Error al crear el video: {str(e)}")
                self.is_recording = False
                if self.video_writer:
                    self.video_writer.release()
                    self.video_writer = None
        else:
            # Detener grabación
            self.is_recording = False  # Primero marcamos que no estamos grabando
            
            # Esperar un momento para asegurar que los últimos frames se escriban
            time.sleep(0.5)
            
            # Detener y cerrar streams de audio
            self.stop_audio_recording()
            
            # Esperar otro momento para asegurar que los archivos se cierren
            time.sleep(0.5)
            
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            
            # Combinar audio y video si hay archivos de audio
            if hasattr(self, 'current_recording'):
                audio_files = []
                if self.current_recording['mic'] and os.path.exists(self.current_recording['mic']):
                    audio_files.append(self.current_recording['mic'])
                if self.current_recording['speakers'] and os.path.exists(self.current_recording['speakers']):
                    audio_files.append(self.current_recording['speakers'])
                
                self.combine_audio_video(
                    self.current_recording['video'],
                    audio_files,
                    self.current_recording['final']
                )
            
            self.record_button.setText("Iniciar Grabación")
            print("Grabación detenida")

    def closeEvent(self, event):
        if self.capture_thread:
            self.capture_thread.stop()
        if self.video_writer:
            self.video_writer.release()
        self.stop_audio_recording()
        event.accept()

    def combine_audio_video(self, video_file, audio_files, output_file):
        """Combina el video con los archivos de audio usando FFmpeg."""
        try:
            if not os.path.exists(video_file):
                print(f"Error: No se encuentra el archivo de video: {video_file}")
                return

            print("\nVerificando archivos antes de combinar:")
            print(f"Video: {video_file} ({os.path.getsize(video_file)} bytes)")
            
            # Solo usar archivos de audio que existan y tengan datos
            valid_audio_files = []
            for audio_file in audio_files:
                if os.path.exists(audio_file):
                    size = os.path.getsize(audio_file)
                    print(f"Audio encontrado: {audio_file} ({size} bytes)")
                    if size > 44:  # Tamaño mínimo de un archivo WAV válido
                        valid_audio_files.append(audio_file)
                    else:
                        print(f"Archivo de audio ignorado por estar vacío: {audio_file}")
                else:
                    print(f"Audio no encontrado: {audio_file}")

            if not valid_audio_files:
                print("No hay archivos de audio válidos para combinar, copiando solo el video...")
                os.rename(video_file, output_file)
                return

            # Construir el comando FFmpeg
            cmd_parts = ['ffmpeg', '-y']
            
            # Agregar input de video
            cmd_parts.extend(['-i', video_file])
            
            # Agregar inputs de audio válidos
            for audio_file in valid_audio_files:
                cmd_parts.extend(['-i', audio_file])

            # Construir el filtro para mezclar audios
            if len(valid_audio_files) > 1:
                # Si hay múltiples audios, mezclarlos con volumen normalizado
                filter_complex = []
                for i in range(len(valid_audio_files)):
                    filter_complex.append(f'[{i+1}:a]volume=1[a{i}];')
                filter_str = ''.join(filter_complex)
                for i in range(len(valid_audio_files)):
                    filter_str += f'[a{i}]'
                filter_str += f'amix=inputs={len(valid_audio_files)}:duration=longest[a]'
                cmd_parts.extend(['-filter_complex', filter_str])
                cmd_parts.extend(['-map', '0:v', '-map', '[a]'])
            else:
                # Si solo hay un archivo de audio, usarlo directamente
                cmd_parts.extend(['-map', '0:v', '-map', '1:a'])

            # Agregar códecs y output con mejor calidad
            cmd_parts.extend([
                '-c:v', 'mpeg4',
                '-q:v', '1',
                '-c:a', 'aac',
                '-b:a', '320k',  # Mayor bitrate para mejor calidad
                output_file
            ])

            print("\nEjecutando comando FFmpeg:")
            print(f"Comando completo: {' '.join(cmd_parts)}")
            
            # Ejecutar FFmpeg
            try:
                result = subprocess.run(
                    cmd_parts,
                    capture_output=True,
                    text=True,
                    check=True
                )
                print("FFmpeg se ejecutó correctamente")
                
                if os.path.exists(output_file):
                    print(f"\nArchivo final creado exitosamente: {output_file}")
                    print(f"Tamaño del archivo: {os.path.getsize(output_file)} bytes")
                    
                    # Limpiar archivos temporales
                    os.remove(video_file)
                    for audio_file in valid_audio_files:
                        os.remove(audio_file)
                else:
                    raise Exception("El archivo final no se creó")
                    
            except subprocess.CalledProcessError as e:
                print("\nError al ejecutar FFmpeg:")
                print(f"Código de salida: {e.returncode}")
                print(f"Error: {e.stderr}")
                raise
            except Exception as e:
                print(f"\nError inesperado: {str(e)}")
                raise

        except Exception as e:
            print(f"\nError al combinar audio y video: {str(e)}")
            # Si falla la combinación, mantener el video temporal como archivo final
            if os.path.exists(video_file):
                os.rename(video_file, output_file)

class AddKeysDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar Claves")
        self.setGeometry(150, 150, 400, 200)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout()

        self.key_input = QLineEdit(self)
        layout.addRow("Clave de Transmisión:", self.key_input)

        self.add_button = QPushButton("Agregar", self)
        self.add_button.clicked.connect(self.add_key)
        layout.addWidget(self.add_button)

        self.setLayout(layout)

    def add_key(self):
        key = self.key_input.text()
        if key:
            print(f"Clave agregada: {key}")
            self.accept()

def get_screen_list():
    """Retorna una lista con las pantallas disponibles usando mss."""
    screens = []
    with mss.mss() as sct:
        monitors = sct.monitors[1:]  # Ignorar el monitor primario
        for i, monitor in enumerate(monitors, start=1):
            # Ajustar el monitor para incluir el cursor
            monitor_with_cursor = {
                'top': monitor['top'],
                'left': monitor['left'],
                'width': monitor['width'],
                'height': monitor['height'],
                'mon': i,
            }
            screens.append({
                'name': f"Monitor {i}",
                'monitor': monitor_with_cursor
            })
    return screens

def main():
    app = QApplication(sys.argv)
    window = StreamApp()  # Creamos la ventana de la aplicación
    window.show()  # Mostrar la ventana
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()