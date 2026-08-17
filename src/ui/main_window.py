import asyncio
import os
import subprocess
import sys

import cv2
import mss
import qasync
import sounddevice as sd
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QColor, QImage, QPixmap, QPainter, QFont
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..config.settings import OUTPUT_DIR, PREVIEW_FPS, PREVIEW_MAX_WIDTH
from ..core.audio_capture import LiveAudioMonitor
from ..core.recording_manager import RecordingError, RecordingManager
from ..core.screen_capture import ScreenCaptureThread
from .audio_settings import AudioSettingsDialog

DARK_BG = "#1e1e2e"
DARK_PANEL = "#2b2b3d"
DARK_BORDER = "#3e3e5e"
ACCENT_RED = "#e74c3c"
ACCENT_GREEN = "#2ecc71"
ACCENT_BLUE = "#3498db"
TEXT_PRIMARY = "#f0f0f0"
TEXT_SECONDARY = "#a0a0b0"
METER_GREEN = "#2ecc71"
METER_YELLOW = "#f1c40f"
METER_RED = "#e74c3c"


STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {DARK_BG};
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}
QComboBox {{
    background-color: {DARK_PANEL};
    border: 1px solid {DARK_BORDER};
    border-radius: 4px;
    padding: 6px 10px;
    color: {TEXT_PRIMARY};
    min-height: 24px;
}}
QComboBox:hover {{
    border: 1px solid {ACCENT_BLUE};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {DARK_PANEL};
    color: {TEXT_PRIMARY};
    border: 1px solid {DARK_BORDER};
    selection-background-color: {ACCENT_BLUE};
}}
QPushButton {{
    background-color: {DARK_PANEL};
    border: 1px solid {DARK_BORDER};
    border-radius: 4px;
    padding: 8px 16px;
    color: {TEXT_PRIMARY};
    font-weight: bold;
    min-height: 28px;
}}
QPushButton:hover {{
    border: 1px solid {ACCENT_BLUE};
    background-color: #353550;
}}
QPushButton:pressed {{
    background-color: #1a1a2e;
}}
QPushButton:disabled {{
    color: #666;
    border-color: #444;
}}
#recordButton {{
    background-color: {ACCENT_RED};
    border: none;
    border-radius: 6px;
    padding: 10px 24px;
    font-size: 15px;
    font-weight: bold;
    min-height: 36px;
}}
#recordButton:hover {{
    background-color: #c0392b;
}}
#pauseButton {{
    background-color: {METER_YELLOW};
    color: #1e1e2e;
    border: none;
    border-radius: 6px;
    padding: 10px 24px;
    font-size: 15px;
    font-weight: bold;
    min-height: 36px;
}}
#pauseButton:hover {{
    background-color: #d4ac0d;
}}
#openFolderButton {{
    background-color: {ACCENT_GREEN};
    color: #1e1e2e;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: bold;
}}
#openFolderButton:hover {{
    background-color: #27ae60;
}}
QSlider::groove:vertical {{
    background: #444;
    width: 8px;
    border-radius: 4px;
}}
QSlider::handle:vertical {{
    background: {ACCENT_BLUE};
    height: 16px;
    margin: -4px 0;
    border-radius: 8px;
}}
QSlider::sub-page:vertical {{
    background: {ACCENT_BLUE};
    border-radius: 4px;
}}
QLabel {{
    color: {TEXT_PRIMARY};
}}
#statusLabel {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
    padding: 4px;
}}
#previewLabel {{
    background-color: #111;
    border: 2px solid {DARK_BORDER};
    border-radius: 6px;
}}
#meterLabel {{
    color: {TEXT_SECONDARY};
    font-size: 10px;
    font-weight: bold;
    min-width: 16px;
    max-width: 16px;
}}
#sectionTitle {{
    color: {ACCENT_BLUE};
    font-weight: bold;
    font-size: 13px;
    padding-top: 4px;
}}
#savedPathLabel {{
    color: {ACCENT_GREEN};
    font-size: 11px;
    padding: 2px;
    background-color: {DARK_PANEL};
    border: 1px solid {DARK_BORDER};
    border-radius: 3px;
}}
"""


def get_screen_list():
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


class AudioMeterWidget(QWidget):
    """Widget de nivel de audio vertical estilo OBS."""

    def __init__(self, label_text="", parent=None):
        super().__init__(parent)
        self._level = 0.0
        self._label_text = label_text
        self.setFixedWidth(40)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

    def set_level(self, level):
        self._level = max(0.0, min(1.0, level))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        bar_w = 14
        x = (w - bar_w) // 2
        margin_top = 20
        margin_bot = 20
        bar_h = h - margin_top - margin_bot

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#333"))
        painter.drawRoundedRect(x, margin_top, bar_w, bar_h, 3, 3)

        fill_h = int(bar_h * self._level)
        if fill_h > 0:
            y = margin_top + bar_h - fill_h
            segments = max(1, fill_h // 4)
            seg_h = fill_h / segments
            for i in range(segments):
                sy = y + i * seg_h
                ratio = (margin_top + bar_h - sy) / bar_h
                if ratio > 0.85:
                    color = QColor(METER_RED)
                elif ratio > 0.6:
                    color = QColor(METER_YELLOW)
                else:
                    color = QColor(METER_GREEN)
                painter.setBrush(color)
                painter.drawRoundedRect(x + 1, int(sy) + 1, bar_w - 2,
                                        int(seg_h) - 1, 2, 2)

        painter.setPen(QColor(TEXT_SECONDARY))
        font = QFont("Segoe UI", 8)
        painter.setFont(font)
        painter.drawText(0, 0, w, 16, Qt.AlignCenter, self._label_text)

        painter.end()


class VolumeSliderWidget(QWidget):
    """Slider vertical de volumen con etiqueta y nivel."""

    def __init__(self, label_text="", parent=None):
        super().__init__(parent)
        self._label_text = label_text
        self.setFixedWidth(50)
        self.setMinimumHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._label = QLabel(label_text)
        self._label.setObjectName("meterLabel")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px; font-weight: bold;")
        layout.addWidget(self._label)

        self._value_label = QLabel("100%")
        self._value_label.setAlignment(Qt.AlignCenter)
        self._value_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 10px;")
        layout.addWidget(self._value_label)

        self.slider = QSlider(Qt.Vertical)
        self.slider.setRange(0, 200)
        self.slider.setValue(100)
        self.slider.setTickPosition(QSlider.TicksRight)
        self.slider.setTickInterval(25)
        self.slider.setMinimumHeight(80)
        layout.addWidget(self.slider, 1)

        self.slider.valueChanged.connect(self._on_change)

    def _on_change(self, value):
        self._value_label.setText(f"{value}%")

    def get_volume(self):
        return self.slider.value() / 100.0

    def set_volume(self, v):
        self.slider.blockSignals(True)
        self.slider.setValue(int(v * 100))
        self._value_label.setText(f"{int(v * 100)}%")
        self.slider.blockSignals(False)


class StreamApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screen Recorder")
        self.setMinimumSize(900, 650)
        self.resize(1000, 700)
        self.setStyleSheet(STYLESHEET)

        self.recording_manager = RecordingManager(OUTPUT_DIR)

        self.screens = []
        self.current_screen = None
        self.capture_thread = None
        self.is_recording = False
        self.is_paused = False
        self.audio_devices = self.get_audio_devices()
        self.selected_mics = self._default_selection('mics')
        self.selected_speakers = self._default_selection('speakers')
        self._saved_path = None
        self._meter_timer = None
        self._live_monitor = LiveAudioMonitor()

        self.init_ui()
        self._start_live_monitor()

        if not self.recording_manager.ffmpeg_available():
            self.status_label.setText(
                "FFmpeg no encontrado: se grabará vídeo sin audio mezclado."
            )

    def get_audio_devices(self):
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
        candidates = self.audio_devices[kind]
        if not candidates:
            return []
        for device in candidates:
            if device['is_default']:
                return [device]
        return [candidates[0]]

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        left_panel = QVBoxLayout()
        left_panel.setSpacing(6)
        right_panel = QVBoxLayout()
        right_panel.setSpacing(6)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        self.screen_selector = QComboBox()
        self.screen_selector.currentIndexChanged.connect(self.update_screen_selection)
        top_bar.addWidget(self.screen_selector, 1)

        self.audio_button = QPushButton("Audio")
        self.audio_button.setFixedWidth(80)
        self.audio_button.clicked.connect(self.show_audio_settings)
        top_bar.addWidget(self.audio_button)
        left_panel.addLayout(top_bar)

        self.preview_label = QLabel()
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(480, 270)
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_panel.addWidget(self.preview_label, 1)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)

        self.status_label = QLabel("Listo")
        self.status_label.setObjectName("statusLabel")
        status_row.addWidget(self.status_label, 1)

        self.saved_path_label = QLabel("")
        self.saved_path_label.setObjectName("savedPathLabel")
        self.saved_path_label.setVisible(False)
        self.saved_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        status_row.addWidget(self.saved_path_label, 1)

        left_panel.addLayout(status_row)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)

        self.record_button = QPushButton("Iniciar Grabacion")
        self.record_button.setObjectName("recordButton")
        self.record_button.clicked.connect(self.toggle_recording)
        controls_row.addWidget(self.record_button)

        self.pause_button = QPushButton("Pausa")
        self.pause_button.setObjectName("pauseButton")
        self.pause_button.setVisible(False)
        self.pause_button.clicked.connect(self.toggle_pause)
        controls_row.addWidget(self.pause_button)

        self.open_folder_button = QPushButton("Abrir carpeta")
        self.open_folder_button.setObjectName("openFolderButton")
        self.open_folder_button.setVisible(False)
        self.open_folder_button.clicked.connect(self._open_recording_folder)
        controls_row.addWidget(self.open_folder_button)

        controls_row.addStretch()
        left_panel.addLayout(controls_row)

        right_panel.addStretch()

        self.mic_meter = AudioMeterWidget("MIC")
        self.mic_slider = VolumeSliderWidget("MIC")
        self.speaker_meter = AudioMeterWidget("SPK")
        self.speaker_slider = VolumeSliderWidget("SPK")

        audio_section = QLabel("Audio")
        audio_section.setObjectName("sectionTitle")
        right_panel.addWidget(audio_section)

        audio_row = QHBoxLayout()
        audio_row.setSpacing(4)
        audio_row.setAlignment(Qt.AlignHCenter)

        audio_row.addWidget(self.mic_meter)
        audio_row.addWidget(self.mic_slider)
        audio_row.addSpacing(8)
        audio_row.addWidget(self.speaker_meter)
        audio_row.addWidget(self.speaker_slider)

        right_panel.addLayout(audio_row)
        right_panel.addStretch()

        right_panel.addStretch()

        root.addLayout(left_panel, 3)
        root.addLayout(right_panel, 0)

        self._meter_timer = QTimer(self)
        self._meter_timer.timeout.connect(self._update_meters)
        self._meter_timer.start(50)

        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.start(max(1, 1000 // PREVIEW_FPS))

        self.update_screen_list()

    def _update_meters(self):
        if self.is_recording:
            levels = self.recording_manager.get_track_levels()
            mic_level = 0.0
            spk_level = 0.0
            for label, level in levels.items():
                if 'Micr' in label or 'mic' in label.lower():
                    mic_level = level
                else:
                    spk_level = level
            self.mic_meter.set_level(mic_level * self.mic_slider.get_volume())
            self.speaker_meter.set_level(spk_level * self.speaker_slider.get_volume())
        else:
            levels = self._live_monitor.get_levels()
            self.mic_meter.set_level(levels.get('mic', 0.0) * self.mic_slider.get_volume())
            self.speaker_meter.set_level(levels.get('speakers', 0.0) * self.speaker_slider.get_volume())

    def _start_live_monitor(self):
        mic_id = self.selected_mics[0]['id'] if self.selected_mics else None
        spk_id = self.selected_speakers[0]['id'] if self.selected_speakers else None
        self._live_monitor.start(mic_id, spk_id)

    def update_preview(self):
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
        self._saved_path = None
        self.saved_path_label.setVisible(False)
        self.open_folder_button.setVisible(False)
        self._live_monitor.stop()

        mic_vol = self.mic_slider.get_volume()
        spk_vol = self.speaker_slider.get_volume()

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

        for track in self.recording_manager._tracks:
            if 'Micr' in track.label or 'mic' in track.label.lower():
                track.volume = mic_vol
            else:
                track.volume = spk_vol

        self.is_recording = True
        self.is_paused = False
        self.record_button.setText("Detener")
        self.record_button.setEnabled(True)
        self.pause_button.setVisible(True)
        self.pause_button.setText("Pausa")
        self.screen_selector.setEnabled(False)
        self.audio_button.setEnabled(False)
        self.mic_slider.setEnabled(False)
        self.speaker_slider.setEnabled(False)
        self.status_label.setText("Grabando...")

    async def stop_recording(self):
        self.record_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.record_button.setText("Procesando...")
        self.status_label.setText("Cerrando archivos...")

        if self.is_paused:
            self.recording_manager.resume()
            self.is_paused = False

        paths = self.recording_manager.stop()
        self.is_recording = False
        self.is_paused = False

        if paths:
            self.status_label.setText("Mezclando audio y vídeo...")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self.recording_manager.finalize, paths
            )
            self._saved_path = result
            self.status_label.setText(f"Guardado: {result}")
            self.saved_path_label.setText(result)
            self.saved_path_label.setVisible(True)
            self.open_folder_button.setVisible(True)

        self.record_button.setText("Iniciar Grabacion")
        self.record_button.setEnabled(True)
        self.pause_button.setVisible(False)
        self.pause_button.setEnabled(True)
        self.screen_selector.setEnabled(True)
        self.audio_button.setEnabled(True)
        self.mic_slider.setEnabled(True)
        self.speaker_slider.setEnabled(True)
        self._start_live_monitor()

    def toggle_pause(self):
        if not self.is_recording:
            return
        if self.is_paused:
            self.recording_manager.resume()
            self.is_paused = False
            self.pause_button.setText("Pausa")
            self.status_label.setText("Grabando...")
        else:
            self.recording_manager.pause()
            self.is_paused = True
            self.pause_button.setText("Reanudar")
            self.status_label.setText("Pausado...")

    def _open_recording_folder(self):
        if not self._saved_path:
            return
        folder = os.path.dirname(self._saved_path)
        if sys.platform == 'win32':
            os.startfile(folder)
        elif sys.platform == 'darwin':
            subprocess.run(['open', folder])
        else:
            subprocess.run(['xdg-open', folder])

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
        if dialog.exec_():
            self._start_live_monitor()

    def closeEvent(self, event):
        self.preview_timer.stop()
        if self._meter_timer:
            self._meter_timer.stop()
        self._live_monitor.stop()

        if self.is_recording:
            if self.is_paused:
                self.recording_manager.resume()
            paths = self.recording_manager.stop()
            self.is_recording = False
            if paths:
                self.recording_manager.finalize(paths)

        self.stop_capture_thread()
        self.recording_manager.cleanup()
        event.accept()
