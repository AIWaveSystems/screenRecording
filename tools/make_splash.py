"""Genera assets/splash.png, la imagen que PyInstaller muestra al extraer el .exe.

Se dibuja con el mismo juego de iconos que la interfaz, para que ambas
pantallas de carga se vean iguales. Ejecutar solo si cambia el diseño:

    python tools/make_splash.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt5.QtWidgets import QApplication

from src.config import app_info
from src.ui import icons

WIDTH = 420
HEIGHT = 286
BG = "#1e1e2e"
BORDER = "#3e3e5e"
TEXT_PRIMARY = "#f0f0f0"
TEXT_SECONDARY = "#a0a0b0"
DESTINO = pathlib.Path(__file__).resolve().parents[1] / "assets" / "splash.png"


def build():
    canvas = QPixmap(WIDTH, HEIGHT)
    canvas.fill(Qt.transparent)

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)

    painter.setPen(QColor(BORDER))
    painter.setBrush(QColor(BG))
    painter.drawRoundedRect(QRectF(0.5, 0.5, WIDTH - 1, HEIGHT - 1), 12, 12)

    logo = icons.pixmap('logo', TEXT_PRIMARY, 96).scaled(
        72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    painter.drawPixmap((WIDTH - 72) // 2, 34, logo)

    painter.setPen(QColor(TEXT_PRIMARY))
    font = QFont("Segoe UI", 16)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(QRectF(0, 118, WIDTH, 34), Qt.AlignCenter,
                     app_info.get('APP_NAME'))

    painter.setPen(QColor(TEXT_SECONDARY))
    painter.setFont(QFont("Segoe UI", 9))
    painter.drawText(QRectF(0, 150, WIDTH, 24), Qt.AlignCenter,
                     app_info.version_label())
    painter.setFont(QFont("Segoe UI", 8))
    painter.drawText(QRectF(0, HEIGHT - 34, WIDTH, 20), Qt.AlignCenter,
                     app_info.get('ORG_TAGLINE'))

    painter.end()
    return canvas


if __name__ == "__main__":
    app = QApplication(sys.argv)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    if not build().save(str(DESTINO), "PNG"):
        raise SystemExit(f"no se pudo escribir {DESTINO}")
    print(f"generado: {DESTINO} ({DESTINO.stat().st_size} bytes)")
