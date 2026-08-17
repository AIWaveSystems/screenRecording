from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
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


class MicBoostDialog(QDialog):
    """Refuerzo fijo del micrófono sobre el resto de la mezcla.

    Se aplica siempre, además del volumen de la pista, para que la voz quede
    por encima del audio del sistema sin tener que bajar este último.
    """

    def __init__(self, boost=1.15, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Refuerzo del micrófono")
        self.setMinimumWidth(460)
        self.setStyleSheet(parent.styleSheet() if parent else "")
        self._build(boost)

    def _build(self, boost):
        layout = QVBoxLayout(self)

        description = QLabel(
            "El micrófono se graba con esta ganancia extra sobre su volumen, "
            "para que la voz destaque por encima del audio del sistema."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        row = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(int(round((boost - 1.0) * 100)))
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(10)
        self.slider.valueChanged.connect(self._update_label)
        row.addWidget(self.slider, 1)

        self.value_label = QLabel()
        self.value_label.setMinimumWidth(56)
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(self.value_label)
        layout.addLayout(row)

        self.hint = QLabel()
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        self._update_label(self.slider.value())

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_label(self, value):
        self.value_label.setText(f"+{value}%")
        if value == 0:
            self.hint.setText("Sin refuerzo: el micrófono se graba tal cual.")
        elif value <= 25:
            self.hint.setText("Rango recomendado: la voz destaca sin distorsionar.")
        else:
            self.hint.setText(
                "Un refuerzo alto puede saturar si el micrófono ya graba fuerte."
            )

    def boost(self):
        return 1.0 + self.slider.value() / 100.0
