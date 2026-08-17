from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)


class AudioSettingsDialog(QDialog):
    """Selección de las fuentes de audio a grabar.

    Se elige como máximo una fuente de cada tipo: el grabador abre un stream
    por pista, así que ofrecer varias casillas prometía algo que nunca se
    cumplía. La elección se recuerda por nombre entre sesiones.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self.setWindowTitle("Fuentes de audio")
        self.setMinimumWidth(520)
        self.setStyleSheet(parent.styleSheet() if parent else "")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.mic_combo = self._build_combo(
            self._app.audio_devices['mics'], self._app.selected_mics
        )
        self.speaker_combo = self._build_combo(
            self._app.audio_devices['speakers'], self._app.selected_speakers
        )

        form.addRow("Micrófono:", self.mic_combo)
        form.addRow("Audio del sistema:", self.speaker_combo)
        layout.addLayout(form)

        hint = QLabel(
            "El audio del sistema se captura por loopback WASAPI sobre la salida "
            "elegida; no hace falta 'Mezcla estéreo' ni VB-Cable.\n"
            "Para silenciar una pista sin dejar de grabarla, usa el botón "
            "Silenciar del mezclador."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _build_combo(devices, selected):
        combo = QComboBox()
        combo.addItem("(Sin grabar)", None)
        selected_id = selected[0]['id'] if selected else None

        for device in devices:
            label = device['name']
            if device.get('is_default'):
                label += "  [predeterminado]"
            combo.addItem(label, device)
            if device['id'] == selected_id:
                combo.setCurrentIndex(combo.count() - 1)
        return combo

    def accept(self):
        mic = self.mic_combo.currentData()
        speaker = self.speaker_combo.currentData()
        self._app.selected_mics = [mic] if mic else []
        self._app.selected_speakers = [speaker] if speaker else []
        super().accept()
