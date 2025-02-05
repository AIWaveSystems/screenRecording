import cv2
import mss
import sounddevice as sd
from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton,
    QComboBox, QDialog, QFormLayout, QLineEdit
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
import os
import asyncio
import qasync
from ..core.recording_manager import RecordingManager
from ..core.screen_capture import ScreenCaptureThread
from ..utils.async_utils import ProcessManager
from ..config.settings import OUTPUT_DIR, PREVIEW_FPS
from .audio_settings import AudioSettingsDialog

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

class StreamApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screen Recorder")
        self.setGeometry(100, 100, 800, 600)
        
        # Inicializar managers
        self.recording_manager = RecordingManager(OUTPUT_DIR)
        self.process_manager = ProcessManager()
        
        # Variables de estado
        self.screens = []
        self.current_screen = None
        self.is_recording = False
        self.selected_speakers = []
        self.selected_mics = []
        self.audio_devices = self.get_audio_devices()
        
        # Inicializar UI
        self.init_ui()
        
        # Configurar loop asíncrono
        self.loop = asyncio.get_event_loop()

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
        # Widget central y layout principal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Botón de configuración de audio
        self.audio_button = QPushButton("Configuración de Audio")
        self.audio_button.clicked.connect(self.show_audio_settings)
        layout.addWidget(self.audio_button)

        # Selector de pantalla
        self.screen_selector = QComboBox()
        self.screen_selector.currentIndexChanged.connect(self.update_screen_selection)
        layout.addWidget(self.screen_selector)

        # Preview
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(640, 360)  # Tamaño mínimo para el preview
        layout.addWidget(self.preview_label)

        # Botón de grabación
        self.record_button = QPushButton("Iniciar Grabación")
        self.record_button.clicked.connect(self.toggle_recording)
        layout.addWidget(self.record_button)

        # Timer para actualizar el preview
        self.preview_timer = QTimer()
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.start(1000 // PREVIEW_FPS)  # Usar PREVIEW_FPS para la actualización

        # Actualizar lista de pantallas
        self.update_screen_list()

    def update_preview(self):
        """Actualiza el preview con el último frame capturado."""
        if hasattr(self, 'capture_thread') and self.capture_thread.isRunning():
            frame = self.capture_thread.last_frame
            if frame is not None:
                try:
                    # Redimensionar el frame para el preview
                    height, width = frame.shape[:2]
                    preview_width = min(640, width)
                    preview_height = int(height * (preview_width / width))
                    
                    frame_resized = cv2.resize(frame, (preview_width, preview_height))
                    frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                    
                    h, w, ch = frame_rgb.shape
                    bytes_per_line = ch * w
                    
                    image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(image)
                    self.preview_label.setPixmap(pixmap)

                    # Si estamos grabando, escribir el frame original
                    if self.is_recording and self.recording_manager.video_writer:
                        self.recording_manager.write_frame(frame)
                except Exception as e:
                    print(f"Error en update_preview: {str(e)}")

    @qasync.asyncSlot()
    async def toggle_recording(self):
        """Maneja el inicio/detención de la grabación de manera asíncrona."""
        if not self.is_recording:
            self.record_button.setEnabled(False)
            self.record_button.setText("Iniciando grabación...")
            
            success = await self.recording_manager.start_recording(
                self.screens[self.current_screen]['monitor'],
                self.selected_speakers,
                self.selected_mics
            )
            
            if success:
                self.is_recording = True
                self.record_button.setText("Detener Grabación")
            else:
                self.record_button.setText("Iniciar Grabación")
            
            self.record_button.setEnabled(True)
        else:
            self.record_button.setEnabled(False)
            self.record_button.setText("Deteniendo grabación...")
            
            await self.recording_manager.stop_recording()
            self.is_recording = False
            self.record_button.setText("Iniciar Grabación")
            self.record_button.setEnabled(True)

    def update_screen_list(self):
        """Actualiza la lista de pantallas disponibles."""
        self.screens = get_screen_list()
        self.screen_selector.clear()
        
        for i, screen in enumerate(self.screens):
            self.screen_selector.addItem(f"{screen['name']} (Monitor {i + 1})")
            
        if self.screens:
            self.current_screen = 0
            self.screen_selector.setCurrentIndex(0)

    def update_screen_selection(self, index):
        """Actualiza la selección de pantalla."""
        if 0 <= index < len(self.screens):
            self.current_screen = index
            if hasattr(self, 'capture_thread') and self.capture_thread is not None:
                self.capture_thread.stop()
            self.start_capture_thread()

    def start_capture_thread(self):
        """Inicia el thread de captura de pantalla."""
        if self.current_screen is not None:
            monitor = self.screens[self.current_screen]['monitor']
            self.capture_thread = ScreenCaptureThread(monitor)
            self.capture_thread.update_image_signal.connect(self.update_preview)
            self.capture_thread.start()

    def show_audio_settings(self):
        """Muestra el diálogo de configuración de audio."""
        dialog = AudioSettingsDialog(self)
        dialog.exec_()

    def closeEvent(self, event):
        """Maneja el cierre de la aplicación."""
        # Detener grabación si está activa
        if self.is_recording:
            self.loop.run_until_complete(self.recording_manager.stop_recording())
        
        # Limpiar recursos
        if hasattr(self, 'capture_thread') and self.capture_thread is not None:
            self.capture_thread.stop()
        
        self.recording_manager.cleanup()
        self.process_manager.stop_all()
        
        event.accept() 