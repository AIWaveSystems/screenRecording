"""Pantalla de carga que se muestra mientras la aplicación se inicializa.

El arranque tarda varios segundos entre importar Qt, OpenCV y los backends de
audio, enumerar dispositivos y abrir la captura. Sin esta ventana no hay ninguna
señal de que el programa esté vivo.
"""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPainterPath
from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from ..config import app_info
from . import icons

WIDTH = 420
HEIGHT = 286
BG = "#1e1e2e"
BORDER = "#3e3e5e"
TEXT_PRIMARY = "#f0f0f0"
TEXT_SECONDARY = "#a0a0b0"
ACCENT = "#3498db"

STYLESHEET = f"""
#splashTitle {{
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 22px;
    font-weight: bold;
}}
#splashSubtitle {{
    color: {TEXT_SECONDARY};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 12px;
}}
#splashOrg {{
    color: {TEXT_SECONDARY};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 10px;
}}
#splashStatus {{
    color: {TEXT_SECONDARY};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 11px;
}}
QProgressBar {{
    background-color: #2b2b3d;
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 3px;
}}
"""


class SplashScreen(QWidget):
    """Ventana sin bordes con logo, mensaje de estado y barra de progreso."""

    def __init__(self, version=None):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                         | Qt.SplashScreen)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(WIDTH, HEIGHT)
        self.setStyleSheet(STYLESHEET)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 30, 34, 26)
        layout.setSpacing(6)

        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        logo.setPixmap(icons.pixmap('logo', TEXT_PRIMARY, 96).scaled(
            72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(logo)

        title = QLabel(app_info.get('APP_NAME'))
        title.setObjectName("splashTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(version or app_info.version_label())
        subtitle.setObjectName("splashSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addStretch()

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        layout.addWidget(self._progress)

        self._status = QLabel("Preparando...")
        self._status.setObjectName("splashStatus")
        self._status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._status)

        org = QLabel(app_info.get('ORG_TAGLINE'))
        org.setObjectName("splashOrg")
        org.setAlignment(Qt.AlignCenter)
        layout.addWidget(org)

        self._center()

    def _center(self):
        screen = QApplication.desktop().screenGeometry(
            QApplication.desktop().primaryScreen())
        self.move(screen.center().x() - WIDTH // 2,
                  screen.center().y() - HEIGHT // 2)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, WIDTH, HEIGHT, 12, 12)
        painter.fillPath(path, QColor(BG))
        painter.strokePath(path, QColor(BORDER))
        painter.end()

    def set_progress(self, value, message=None):
        """Actualiza el progreso y repinta de inmediato.

        La inicialización bloquea el hilo de UI, así que sin procesar eventos
        aquí la ventana se quedaría congelada y en blanco.
        """
        self._progress.setValue(max(0, min(100, int(value))))
        if message is not None:
            self._status.setText(message)
        QApplication.processEvents()

    def finish(self, window=None):
        self.set_progress(100, "Listo")
        self.close()
        if window is not None:
            window.raise_()
            window.activateWindow()
