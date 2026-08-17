import asyncio
import os
import subprocess
import sys

import cv2
import mss
import qasync
import sounddevice as sd
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..config import user_config
from ..core.audio_capture import LiveAudioMonitor
from ..core.recording_manager import (
    MIC,
    SPEAKERS,
    RecordingError,
    RecordingManager,
)
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
METER_MUTED = "#555565"

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {DARK_BG};
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}
QMenuBar {{
    background-color: {DARK_PANEL};
    color: {TEXT_PRIMARY};
}}
QMenuBar::item:selected {{
    background-color: {ACCENT_BLUE};
}}
QMenu {{
    background-color: {DARK_PANEL};
    color: {TEXT_PRIMARY};
    border: 1px solid {DARK_BORDER};
}}
QMenu::item:selected {{
    background-color: {ACCENT_BLUE};
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
#muteButton {{
    padding: 4px 6px;
    font-size: 11px;
    min-height: 22px;
    font-weight: bold;
}}
#muteButton:checked {{
    background-color: {ACCENT_RED};
    border: 1px solid {ACCENT_RED};
    color: #ffffff;
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
#timerLabel {{
    color: {TEXT_PRIMARY};
    font-size: 18px;
    font-weight: bold;
    padding: 4px 10px;
}}
#previewLabel {{
    background-color: #111;
    border: 2px solid {DARK_BORDER};
    border-radius: 6px;
}}
#channelTitle {{
    color: {TEXT_PRIMARY};
    font-size: 11px;
    font-weight: bold;
}}
#channelDevice {{
    color: {TEXT_SECONDARY};
    font-size: 9px;
}}
#channelValue {{
    color: {TEXT_SECONDARY};
    font-size: 10px;
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
    """Medidor de nivel vertical estilo OBS."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 0.0
        self._muted = False
        self.setFixedWidth(18)
        self.setMinimumHeight(110)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

    def set_level(self, level):
        level = max(0.0, min(1.0, level))
        if abs(level - self._level) > 0.005:
            self._level = level
            self.update()

    def set_muted(self, muted):
        if muted != self._muted:
            self._muted = muted
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        bar_w = self.width()
        bar_h = max(1, self.height())

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#333"))
        painter.drawRoundedRect(0, 0, bar_w, bar_h, 3, 3)

        if self._level <= 0:
            painter.end()
            return

        if self._muted:
            fill_h = int(bar_h * self._level)
            painter.setBrush(QColor(METER_MUTED))
            painter.drawRoundedRect(1, bar_h - fill_h, bar_w - 2, fill_h, 2, 2)
            painter.end()
            return

        for low, high, color in ((0.0, 0.6, METER_GREEN),
                                 (0.6, 0.85, METER_YELLOW),
                                 (0.85, 1.0, METER_RED)):
            top = min(self._level, high)
            if top <= low:
                continue
            band_h = int(bar_h * (top - low))
            if band_h < 1:
                continue
            painter.setBrush(QColor(color))
            painter.drawRect(1, int(bar_h * (1.0 - top)), bar_w - 2, band_h)

        painter.end()


class AudioChannelPanel(QWidget):
    """Columna de un canal de audio: nivel, volumen y silencio."""

    volume_changed = pyqtSignal(float)
    mute_toggled = pyqtSignal(bool)

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFixedWidth(96)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(3)

        self._title = QLabel(title)
        self._title.setObjectName("channelTitle")
        self._title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._title)

        self._device = QLabel("-")
        self._device.setObjectName("channelDevice")
        self._device.setAlignment(Qt.AlignCenter)
        self._device.setWordWrap(True)
        self._device.setFixedHeight(24)
        layout.addWidget(self._device)

        self._value = QLabel("100%")
        self._value.setObjectName("channelValue")
        self._value.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._value)

        body = QHBoxLayout()
        body.setSpacing(6)
        body.setAlignment(Qt.AlignHCenter)

        self.meter = AudioMeterWidget()
        body.addWidget(self.meter)

        self.slider = QSlider(Qt.Vertical)
        self.slider.setRange(0, 200)
        self.slider.setValue(100)
        self.slider.setTickPosition(QSlider.TicksRight)
        self.slider.setTickInterval(25)
        self.slider.setMinimumHeight(110)
        self.slider.valueChanged.connect(self._on_slider)
        body.addWidget(self.slider)

        layout.addLayout(body, 1)

        self.mute_button = QPushButton("Silenciar")
        self.mute_button.setObjectName("muteButton")
        self.mute_button.setCheckable(True)
        self.mute_button.toggled.connect(self._on_mute)
        layout.addWidget(self.mute_button)

    def _on_slider(self, value):
        self._value.setText(f"{value}%")
        self.volume_changed.emit(value / 100.0)

    def _on_mute(self, muted):
        self.mute_button.setText("Silenciado" if muted else "Silenciar")
        self.meter.set_muted(muted)
        self.slider.setEnabled(not muted)
        self.mute_toggled.emit(muted)

    def set_device_name(self, name):
        self._device.setText(name or "(sin grabar)")
        self._device.setToolTip(name or "(sin grabar)")
        enabled = bool(name)
        self.slider.setEnabled(enabled and not self.is_muted())
        self.mute_button.setEnabled(enabled)

    def set_level(self, level):
        self.meter.set_level(level)

    def get_volume(self):
        return self.slider.value() / 100.0

    def set_volume(self, volume):
        self.slider.blockSignals(True)
        self.slider.setValue(int(round(volume * 100)))
        self._value.setText(f"{int(round(volume * 100))}%")
        self.slider.blockSignals(False)

    def is_muted(self):
        return self.mute_button.isChecked()

    def set_muted(self, muted):
        self.mute_button.blockSignals(True)
        self.mute_button.setChecked(bool(muted))
        self.mute_button.setText("Silenciado" if muted else "Silenciar")
        self.meter.set_muted(bool(muted))
        self.slider.setEnabled(not muted)
        self.mute_button.blockSignals(False)


class StreamApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screen Recorder")
        self.setMinimumSize(900, 650)
        self.resize(1000, 700)
        self.setStyleSheet(STYLESHEET)

        self.config = user_config.load()
        self.preview_fps = self.config['preview']['fps']
        self.preview_max_width = self.config['preview']['max_width']

        self.recording_manager = RecordingManager(
            self.config['output_dir'],
            fps=self.config['video']['fps'],
            codec=self.config['video']['codec'],
        )

        self.screens = []
        self.current_screen = None
        self.capture_thread = None
        self.is_recording = False
        self.is_paused = False
        self._saved_path = None
        self._live_monitor = LiveAudioMonitor()
        self._pending_warnings = []

        self.audio_devices = self.get_audio_devices()
        self.selected_mics = self._restore_device('mics', 'mic_device')
        self.selected_speakers = self._restore_device('speakers', 'speaker_device')

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(700)
        self._save_timer.timeout.connect(self._save_config)

        self.init_ui()
        self._restore_geometry()
        self._apply_audio_config()
        self._start_live_monitor()

        if not self.recording_manager.ffmpeg_available():
            self._pending_warnings.append(
                "FFmpeg no encontrado: se grabará vídeo sin audio mezclado."
            )
        if self._pending_warnings:
            self.status_label.setText(self._pending_warnings[0])

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

    def _restore_device(self, kind, config_key):
        """Resuelve el dispositivo guardado por nombre, no por índice.

        Los índices cambian al conectar o quitar hardware, así que un índice
        guardado apuntaría a otro aparato en el siguiente arranque.
        """
        stored = self.config['audio'].get(config_key, user_config.USE_SYSTEM_DEFAULT)
        if stored is None:
            return []
        if stored == user_config.USE_SYSTEM_DEFAULT:
            return self._default_selection(kind)
        for device in self.audio_devices[kind]:
            if device['name'] == stored:
                return [device]
        self._pending_warnings.append(
            f"El dispositivo guardado '{stored}' ya no está disponible; "
            "se usa el predeterminado."
        )
        return self._default_selection(kind)

    def init_ui(self):
        self._build_menu()

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

        self.timer_label = QLabel("00:00")
        self.timer_label.setObjectName("timerLabel")
        self.timer_label.setVisible(False)
        controls_row.addWidget(self.timer_label)

        controls_row.addStretch()
        left_panel.addLayout(controls_row)

        audio_section = QLabel("Mezclador")
        audio_section.setObjectName("sectionTitle")
        audio_section.setAlignment(Qt.AlignCenter)
        right_panel.addWidget(audio_section)

        self.mic_panel = AudioChannelPanel("MICRÓFONO")
        self.mic_panel.volume_changed.connect(
            lambda value: self._on_volume_changed(MIC, value)
        )
        self.mic_panel.mute_toggled.connect(
            lambda muted: self._on_mute_toggled(MIC, muted)
        )

        self.speaker_panel = AudioChannelPanel("SISTEMA")
        self.speaker_panel.volume_changed.connect(
            lambda value: self._on_volume_changed(SPEAKERS, value)
        )
        self.speaker_panel.mute_toggled.connect(
            lambda muted: self._on_mute_toggled(SPEAKERS, muted)
        )

        audio_row = QHBoxLayout()
        audio_row.setSpacing(4)
        audio_row.setAlignment(Qt.AlignHCenter)
        audio_row.addWidget(self.mic_panel)
        audio_row.addWidget(self.speaker_panel)

        right_panel.addLayout(audio_row, 1)

        root.addLayout(left_panel, 3)
        root.addLayout(right_panel, 0)

        self._meter_timer = QTimer(self)
        self._meter_timer.timeout.connect(self._update_meters)
        self._meter_timer.start(50)

        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.start(max(1, 1000 // self.preview_fps))

        self.update_screen_list()

    def _build_menu(self):
        menu = self.menuBar()

        archivo = menu.addMenu("Archivo")
        archivo.addAction("Abrir carpeta de grabaciones", self._open_output_folder)
        archivo.addAction("Cambiar carpeta de salida...", self._choose_output_folder)
        archivo.addSeparator()
        archivo.addAction("Salir", self.close)

        config = menu.addMenu("Configuración")
        config.addAction("Fuentes de audio...", self.show_audio_settings)
        config.addSeparator()
        config.addAction("Abrir carpeta de configuración", self._open_config_folder)
        config.addAction("Restablecer configuración", self._reset_config)

    def _apply_audio_config(self):
        audio = self.config['audio']
        self.mic_panel.set_volume(audio['mic_volume'])
        self.mic_panel.set_muted(audio['mic_muted'])
        self.speaker_panel.set_volume(audio['speaker_volume'])
        self.speaker_panel.set_muted(audio['speaker_muted'])
        self._refresh_channel_labels()

    def _refresh_channel_labels(self):
        self.mic_panel.set_device_name(
            self.selected_mics[0]['name'] if self.selected_mics else None
        )
        self.speaker_panel.set_device_name(
            self.selected_speakers[0]['name'] if self.selected_speakers else None
        )

    def _on_volume_changed(self, key, value):
        self.recording_manager.set_volume(key, value)
        self._schedule_save()

    def _on_mute_toggled(self, key, muted):
        self.recording_manager.set_muted(key, muted)
        self._schedule_save()

    def _start_live_monitor(self):
        mic_id = self.selected_mics[0]['id'] if self.selected_mics else None
        spk_id = self.selected_speakers[0]['id'] if self.selected_speakers else None
        self._live_monitor.start(mic_id, spk_id)

    def _update_meters(self):
        if self.is_recording:
            levels = self.recording_manager.get_levels()
            mic_level = levels.get(MIC, 0.0)
            spk_level = levels.get(SPEAKERS, 0.0)
            self.timer_label.setText(
                self._format_elapsed(self.recording_manager.elapsed_seconds())
            )
        else:
            levels = self._live_monitor.get_levels()
            mic_level = levels.get('mic', 0.0)
            spk_level = levels.get('speakers', 0.0)

        self.mic_panel.set_level(mic_level * self.mic_panel.get_volume())
        self.speaker_panel.set_level(spk_level * self.speaker_panel.get_volume())

    @staticmethod
    def _format_elapsed(seconds):
        total = int(seconds)
        hours, remainder = divmod(total, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours:d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def update_preview(self):
        if self.capture_thread is None or not self.capture_thread.isRunning():
            return

        frame = self.capture_thread.latest_frame
        if frame is None:
            return

        try:
            if self.is_recording:
                self.recording_manager.write_frame(frame)

            height, width = frame.shape[:2]
            preview_width = min(self.preview_max_width, width)
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
        if self.current_screen is None or not self.screens:
            QMessageBox.warning(self, "Sin monitor",
                                "No hay ninguna pantalla seleccionada.")
            return
        if self.capture_thread is None or not self.capture_thread.isRunning():
            QMessageBox.warning(self, "Sin captura",
                                "No hay ninguna pantalla capturándose.")
            return

        self.record_button.setEnabled(False)
        self._saved_path = None
        self.saved_path_label.setVisible(False)
        self.open_folder_button.setVisible(False)
        self._live_monitor.stop()

        volumes = {
            MIC: self.mic_panel.get_volume(),
            SPEAKERS: self.speaker_panel.get_volume(),
        }
        muted = {
            MIC: self.mic_panel.is_muted(),
            SPEAKERS: self.speaker_panel.is_muted(),
        }

        try:
            self.recording_manager.start(
                self.screens[self.current_screen]['monitor'],
                self.selected_speakers,
                self.selected_mics,
                volumes=volumes,
                muted=muted,
            )
        except RecordingError as exc:
            QMessageBox.critical(self, "No se pudo iniciar la grabación", str(exc))
            self.record_button.setEnabled(True)
            self.status_label.setText("Listo")
            self._start_live_monitor()
            return
        except Exception as exc:
            QMessageBox.critical(self, "Error inesperado", str(exc))
            self.record_button.setEnabled(True)
            self._start_live_monitor()
            return

        self.is_recording = True
        self.is_paused = False
        self.record_button.setText("Detener")
        self.record_button.setEnabled(True)
        self.pause_button.setVisible(True)
        self.pause_button.setText("Pausa")
        self.timer_label.setText("00:00")
        self.timer_label.setVisible(True)
        self.screen_selector.setEnabled(False)
        self.audio_button.setEnabled(False)
        self.status_label.setText("Grabando...")

    async def stop_recording(self):
        self.record_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.record_button.setText("Procesando...")
        self.status_label.setText("Cerrando archivos...")

        try:
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
                self.status_label.setText("Grabación guardada")
                self.saved_path_label.setText(result)
                self.saved_path_label.setToolTip(result)
                self.saved_path_label.setVisible(True)
                self.open_folder_button.setVisible(True)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"Error al guardar: {exc}")
            self.is_recording = False
            self.is_paused = False

        self.record_button.setText("Iniciar Grabacion")
        self.record_button.setEnabled(True)
        self.pause_button.setVisible(False)
        self.pause_button.setEnabled(True)
        self.timer_label.setVisible(False)
        self.screen_selector.setEnabled(True)
        self.audio_button.setEnabled(True)
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
            self.status_label.setText("Pausado")

    def update_screen_list(self):
        self.screens = get_screen_list()
        self.screen_selector.blockSignals(True)
        self.screen_selector.clear()
        for screen in self.screens:
            self.screen_selector.addItem(screen['name'])
        self.screen_selector.blockSignals(False)

        if not self.screens:
            QMessageBox.critical(self, "Sin monitores",
                                 "No se detectó ningún monitor para capturar.")
            return

        stored = self.config['monitor'].get('index', 0)
        index = stored if 0 <= stored < len(self.screens) else 0
        self.screen_selector.setCurrentIndex(index)
        self.update_screen_selection(index)

    def update_screen_selection(self, index):
        if not (0 <= index < len(self.screens)) or self.is_recording:
            return

        self.current_screen = index
        self.stop_capture_thread()
        self.start_capture_thread()
        self._schedule_save()

    def start_capture_thread(self):
        if self.current_screen is None:
            return
        monitor = self.screens[self.current_screen]['monitor']
        self.capture_thread = ScreenCaptureThread(
            monitor,
            fps=self.config['video']['fps'],
            draw_cursor=self.config['video']['capture_cursor'],
            parent=self,
        )
        self.capture_thread.start()

    def stop_capture_thread(self):
        thread = self.capture_thread
        if thread is None:
            return
        self.capture_thread = None
        thread.stop()
        if thread.isFinished():
            thread.deleteLater()
        else:
            thread.finished.connect(thread.deleteLater)
        self.preview_label.clear()

    def show_audio_settings(self):
        if self.is_recording:
            QMessageBox.information(
                self, "Grabación en curso",
                "Detén la grabación para cambiar los dispositivos de audio."
            )
            return
        dialog = AudioSettingsDialog(self)
        if dialog.exec_():
            self._refresh_channel_labels()
            self._start_live_monitor()
            self._schedule_save()

    def _schedule_save(self):
        self._save_timer.start()

    def _collect_config(self):
        config = dict(self.config)
        config['output_dir'] = self.recording_manager.output_dir
        config['audio'] = dict(self.config['audio'])
        config['audio'].update({
            'mic_device': self.selected_mics[0]['name'] if self.selected_mics else None,
            'speaker_device': (self.selected_speakers[0]['name']
                               if self.selected_speakers else None),
            'mic_volume': self.mic_panel.get_volume(),
            'speaker_volume': self.speaker_panel.get_volume(),
            'mic_muted': self.mic_panel.is_muted(),
            'speaker_muted': self.speaker_panel.is_muted(),
        })
        config['monitor'] = dict(self.config['monitor'])
        if self.current_screen is not None and self.screens:
            monitor = self.screens[self.current_screen]['monitor']
            config['monitor'].update({
                'index': self.current_screen,
                'width': monitor['width'],
                'height': monitor['height'],
            })
        return config

    def _save_config(self):
        self.config = self._collect_config()
        user_config.save(self.config)

    def _open_folder(self, folder):
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "Carpeta no disponible",
                                f"No existe la carpeta:\n{folder}")
            return
        try:
            if sys.platform == 'win32':
                os.startfile(folder)
            elif sys.platform == 'darwin':
                subprocess.run(['open', folder], check=False)
            else:
                subprocess.run(['xdg-open', folder], check=False)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo abrir la carpeta", str(exc))

    def _open_recording_folder(self):
        if self._saved_path:
            self._open_folder(os.path.dirname(self._saved_path))
        else:
            self._open_output_folder()

    def _open_output_folder(self):
        self._open_folder(self.recording_manager.output_dir)

    def _open_config_folder(self):
        folder = user_config.config_dir()
        os.makedirs(folder, exist_ok=True)
        if not os.path.exists(user_config.config_path()):
            self._save_config()
        self._open_folder(folder)

    def _choose_output_folder(self):
        if self.is_recording:
            QMessageBox.information(self, "Grabación en curso",
                                    "Detén la grabación para cambiar la carpeta.")
            return
        folder = QFileDialog.getExistingDirectory(
            self, "Carpeta para las grabaciones", self.recording_manager.output_dir
        )
        if not folder:
            return
        if not os.access(folder, os.W_OK):
            QMessageBox.warning(self, "Carpeta no escribible",
                                "No hay permisos de escritura en esa carpeta.")
            return
        self.recording_manager.output_dir = folder
        self.status_label.setText(f"Las grabaciones se guardarán en {folder}")
        self._save_config()

    def _reset_config(self):
        answer = QMessageBox.question(
            self, "Restablecer configuración",
            "Se volverá a los valores por defecto. La configuración actual se "
            "guardará como config.json.bak.\n\n¿Continuar?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        self.config = user_config.reset()
        self.recording_manager.output_dir = self.config['output_dir']
        self.selected_mics = self._restore_device('mics', 'mic_device')
        self.selected_speakers = self._restore_device('speakers', 'speaker_device')
        self._apply_audio_config()
        self._start_live_monitor()
        self.status_label.setText("Configuración restablecida")

    def _restore_geometry(self):
        state = user_config.load_state()
        geometry = state.get('window')
        if not isinstance(geometry, dict):
            return
        try:
            available = QApplication.desktop().availableGeometry(self)
            width = min(int(geometry['width']), available.width())
            height = min(int(geometry['height']), available.height())
            x = int(geometry['x'])
            y = int(geometry['y'])
            if not available.contains(x, y):
                x, y = available.x() + 40, available.y() + 40
            self.setGeometry(x, y, width, height)
        except Exception:
            pass

    def _save_state(self):
        rect = self.geometry()
        user_config.save_state({
            'window': {
                'x': rect.x(), 'y': rect.y(),
                'width': rect.width(), 'height': rect.height(),
            },
        })

    def closeEvent(self, event):
        self.preview_timer.stop()
        self._meter_timer.stop()
        self._save_timer.stop()

        self._live_monitor.stop()

        if self.is_recording:
            try:
                paths = self.recording_manager.stop()
                self.is_recording = False
                if paths:
                    self.recording_manager.finalize(paths)
            except Exception as exc:
                print(f"[closeEvent] error deteniendo grabación: {exc}")

        self.stop_capture_thread()
        self.recording_manager.cleanup()

        self._save_config()
        self._save_state()

        event.accept()
        QApplication.quit()
