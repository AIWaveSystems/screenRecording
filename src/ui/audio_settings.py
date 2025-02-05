from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QCheckBox,
    QPushButton, QScrollArea, QWidget, QTabWidget
)
from PyQt5.QtCore import Qt
import sounddevice as sd

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