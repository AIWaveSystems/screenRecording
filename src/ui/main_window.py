import asyncio

import cv2
import mss
import qasync
import sounddevice as sd
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QComboBox,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..config.settings import OUTPUT_DIR, PREVIEW_FPS, PREVIEW_MAX_WIDTH
from ..core.recording_manager import RecordingError, RecordingManager
from ..core.screen_capture import ScreenCaptureThread
from .audio_settings import AudioSettingsDialog


def get_screen_list():
    """Lista los monitores disponibles.

    mss.monitors[0] es el escritorio virtual completo (todos los monitores
    juntos); los individuales empiezan en el índice 1.
    """
    screens = []
    with mss.mss() as sct:
        for i, monitor in enumerate(sct.monitors[1:], start=1):
            screens.append({
                'name': f"Monitor {i} ({monitor['width']}x{monitor['height']})",
                'monitor': {
                    'top': monitor['top'],
                    'left': monitor['left'],
                    'width': monitor['width'],
                    'height': monitor['height'],
                    'mon': i,
                },
            })
    return screens


class StreamApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screen Recorder")
        self.setGeometry(100, 100, 800, 600)

        self.recording_manager = RecordingManager(OUTPUT_DIR)

        self.screens = []
        self.current_screen = None
        self.capture_thread = None
        self.is_recording = False
        self.audio_devices = self.get_audio_devices()
        self.selected_mics = self._default_selection('mics')
        self.selected_speakers = self._default_selection('speakers')

        self.init_ui()

        if not self.recording_manager.ffmpeg_available():
            self.status_label.setText(
                "FFmpeg no encontrado: se grabará vídeo sin audio mezclado."
            )

    def get_audio_devices(self):
        """Dispositivos de audio disponibles, agrupados por entrada y salida.

        Windows expone el mismo aparato por MME, DirectSound, WASAPI y WDM-KS.
        Se prefiere WASAPI (nombres completos, menor latencia) y se eliminan
        los duplicados para que la lista sea legible.
        """
        devices = {'speakers': [], 'mics': []}
        try:
            device_list = sd.query_devices()

            default_names = set()
            for kind in ('input', 'output'):
                try:
                    default_names.add(sd.query_devices(kind=kind)['name'])
                except Exception:
                    pass

            def hostapi_name(index):
                return sd.query_hostapis(index)['name']

            wasapi = [i for i, d in enumerate(device_list)
                      if 'wasapi' in hostapi_name(d['hostapi']).lower()]
            indices = wasapi or range(len(device_list))

            seen = {'speakers': set(), 'mics': set()}
            for i in indices:
                device = device_list[i]
                info = {
                    'id': i,
                    'name': device['name'],
                    'is_default': device['name'] in default_names,
                }
                for kind, channels in (('speakers', 'max_output_channels'),
                                       ('mics', 'max_input_channels')):
                    if device.get(channels, 0) > 0 and device['name'] not in seen[kind]:
                        seen[kind].add(device['name'])
                        devices[kind].append(info)
        except Exception as exc:
            print(f"Error al obtener dispositivos de audio: {exc}")
        return devices

    def _default_selection(self, kind):
        """Dispositivo preseleccionado: el predeterminado del sistema."""
        candidates = self.audio_devices[kind]
        if not candidates:
            return []
        for device in candidates:
            if device['is_default']:
                return [device]
        return [candidates[0]]

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.audio_button = QPushButton("Configuración de Audio")
        self.audio_button.clicked.connect(self.show_audio_settings)
        layout.addWidget(self.audio_button)

        self.screen_selector = QComboBox()
        self.screen_selector.currentIndexChanged.connect(self.update_screen_selection)
        layout.addWidget(self.screen_selector)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(640, 360)
        layout.addWidget(self.preview_label)

        self.status_label = QLabel("Listo")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.record_button = QPushButton("Iniciar Grabación")
        self.record_button.clicked.connect(self.toggle_recording)
        layout.addWidget(self.record_button)

        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.start(max(1, 1000 // PREVIEW_FPS))

        self.update_screen_list()

    def update_preview(self):
        """Muestra el último frame capturado. Solo se invoca desde el hilo de UI."""
        if self.capture_thread is None or not self.capture_thread.isRunning():
            return

        frame = self.capture_thread.latest_frame
        if frame is None:
            return

        try:
            height, width = frame.shape[:2]
            preview_width = min(PREVIEW_MAX_WIDTH, width)
            preview_height = max(1, int(height * (preview_width / width)))

            frame_resized = cv2.resize(
                frame, (preview_width, preview_height), interpolation=cv2.INTER_AREA
            )
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)

            h, w, ch = frame_rgb.shape
            image = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
            self.preview_label.setPixmap(QPixmap.fromImage(image.copy()))
        except Exception as exc:
            print(f"Error en update_preview: {exc}")

    @qasync.asyncSlot()
    async def toggle_recording(self):
        if not self.is_recording:
            await self.start_recording()
        else:
            await self.stop_recording()

    async def start_recording(self):
        if self.capture_thread is None or not self.capture_thread.isRunning():
            QMessageBox.warning(self, "Sin captura",
                                "No hay ninguna pantalla capturándose.")
            return

        self.record_button.setEnabled(False)
        try:
            self.recording_manager.start(
                self.screens[self.current_screen]['monitor'],
                self.selected_speakers,
                self.selected_mics,
                lambda: self.capture_thread.latest_frame if self.capture_thread else None,
            )
        except RecordingError as exc:
            QMessageBox.critical(self, "No se pudo iniciar la grabación", str(exc))
            self.record_button.setEnabled(True)
            self.status_label.setText("Listo")
            return
        except Exception as exc:
            QMessageBox.critical(self, "Error inesperado", str(exc))
            self.record_button.setEnabled(True)
            return

        self.is_recording = True
        self.record_button.setText("Detener Grabación")
        self.record_button.setEnabled(True)
        self.screen_selector.setEnabled(False)
        self.audio_button.setEnabled(False)
        self.status_label.setText("Grabando...")

    async def stop_recording(self):
        self.record_button.setEnabled(False)
        self.record_button.setText("Procesando...")
        self.status_label.setText("Cerrando archivos...")

        paths = self.recording_manager.stop()
        self.is_recording = False

        if paths:
            self.status_label.setText("Mezclando audio y vídeo...")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self.recording_manager.finalize, paths
            )
            self.status_label.setText(f"Guardado: {result}")

        self.record_button.setText("Iniciar Grabación")
        self.record_button.setEnabled(True)
        self.screen_selector.setEnabled(True)
        self.audio_button.setEnabled(True)

    def update_screen_list(self):
        self.screens = get_screen_list()
        self.screen_selector.blockSignals(True)
        self.screen_selector.clear()
        for screen in self.screens:
            self.screen_selector.addItem(screen['name'])
        self.screen_selector.blockSignals(False)

        if self.screens:
            self.screen_selector.setCurrentIndex(0)
            self.update_screen_selection(0)
        else:
            QMessageBox.critical(self, "Sin monitores",
                                 "No se detectó ningún monitor para capturar.")

    def update_screen_selection(self, index):
        if not (0 <= index < len(self.screens)) or self.is_recording:
            return

        self.current_screen = index
        self.stop_capture_thread()
        self.start_capture_thread()

    def start_capture_thread(self):
        if self.current_screen is None:
            return
        monitor = self.screens[self.current_screen]['monitor']
        self.capture_thread = ScreenCaptureThread(monitor, parent=self)
        self.capture_thread.start()

    def stop_capture_thread(self):
        if self.capture_thread is not None:
            self.capture_thread.stop()
            self.capture_thread.deleteLater()
            self.capture_thread = None
            self.preview_label.clear()

    def show_audio_settings(self):
        dialog = AudioSettingsDialog(self)
        dialog.exec_()

    def closeEvent(self, event):
        self.preview_timer.stop()

        if self.is_recording:
            paths = self.recording_manager.stop()
            self.is_recording = False
            if paths:
                self.recording_manager.finalize(paths)

        self.stop_capture_thread()
        self.recording_manager.cleanup()
        event.accept()
