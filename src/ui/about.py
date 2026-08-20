"""Ventana Acerca de: version, organizacion, enlaces y licencias."""
import os

from PyQt5.QtCore import QSize, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QDesktopServices, QPainter, QPainterPath, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ..config import app_info, user_config
from . import icons

LOGO_SIZE = 88


def _rounded(pixmap, size, radius=16):
    escalado = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding,
                             Qt.SmoothTransformation)
    salida = QPixmap(size, size)
    salida.fill(Qt.transparent)

    painter = QPainter(salida)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    recorte = QPainterPath()
    recorte.addRoundedRect(0, 0, size, size, radius, radius)
    painter.setClipPath(recorte)
    painter.drawPixmap(int((size - escalado.width()) / 2),
                       int((size - escalado.height()) / 2), escalado)
    painter.end()
    return salida


class LogoDownloader(QThread):
    """Descarga el logo de la organizacion sin bloquear la ventana."""

    ready = pyqtSignal(QPixmap)

    def __init__(self, url, destino, parent=None):
        super().__init__(parent)
        self._url = url
        self._destino = destino

    def run(self):
        try:
            import urllib.request

            peticion = urllib.request.Request(
                self._url, headers={'User-Agent': app_info.get('APP_NAME')})
            with urllib.request.urlopen(peticion, timeout=6) as respuesta:
                datos = respuesta.read()

            pixmap = QPixmap()
            if not pixmap.loadFromData(datos) or pixmap.isNull():
                return

            try:
                os.makedirs(os.path.dirname(self._destino), exist_ok=True)
                pixmap.save(self._destino, "PNG")
            except OSError:
                pass

            self.ready.emit(pixmap)
        except Exception as exc:
            print(f"[about] no se pudo descargar el logo: {exc}")


class AboutDialog(QDialog):
    """Identidad de la aplicacion, version y accesos a la documentacion."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Acerca de {app_info.get('APP_NAME')}")
        self.setMinimumWidth(520)
        self.setStyleSheet(parent.styleSheet() if parent else "")
        self._downloader = None
        self._build()
        self._load_logo()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        cabecera = QHBoxLayout()
        cabecera.setSpacing(16)

        self._logo = QLabel()
        self._logo.setFixedSize(LOGO_SIZE, LOGO_SIZE)
        self._logo.setAlignment(Qt.AlignCenter)
        self._logo.setPixmap(icons.pixmap('app', "#f0f0f0", LOGO_SIZE))
        cabecera.addWidget(self._logo)

        textos = QVBoxLayout()
        textos.setSpacing(2)

        nombre = QLabel(app_info.get('APP_NAME'))
        nombre.setStyleSheet("font-size: 20px; font-weight: bold;")
        textos.addWidget(nombre)

        version = QLabel(f"Version {app_info.get('APP_VERSION')}")
        version.setStyleSheet("font-size: 13px; color: #3498db; font-weight: bold;")
        textos.addWidget(version)

        descripcion = QLabel(app_info.get('APP_DESCRIPTION'))
        descripcion.setWordWrap(True)
        descripcion.setStyleSheet("color: #a0a0b0;")
        textos.addWidget(descripcion)

        tagline = QLabel(app_info.get('ORG_TAGLINE'))
        tagline.setStyleSheet("color: #a0a0b0; font-size: 11px; padding-top: 4px;")
        textos.addWidget(tagline)

        textos.addStretch()
        cabecera.addLayout(textos, 1)
        layout.addLayout(cabecera)

        separador = QFrame()
        separador.setFrameShape(QFrame.HLine)
        separador.setStyleSheet("color: #3e3e5e;")
        layout.addWidget(separador)

        for etiqueta, valor in self._detalles():
            fila = QHBoxLayout()
            titulo = QLabel(etiqueta)
            titulo.setFixedWidth(120)
            titulo.setStyleSheet("color: #a0a0b0; font-size: 12px;")
            fila.addWidget(titulo)

            contenido = QLabel(valor)
            contenido.setOpenExternalLinks(True)
            contenido.setTextInteractionFlags(Qt.TextBrowserInteraction)
            contenido.setWordWrap(True)
            contenido.setStyleSheet("font-size: 12px;")
            fila.addWidget(contenido, 1)
            layout.addLayout(fila)

        layout.addSpacing(6)

        acciones = QHBoxLayout()
        acciones.setSpacing(8)
        for texto, icono, url in (
            ("Repositorio", 'folder', app_info.get('APP_REPO_URL')),
            ("Novedades", 'boost', app_info.get('APP_RELEASES_URL')),
            ("Reportar un fallo", 'gear', app_info.get('APP_ISSUES_URL')),
        ):
            boton = QPushButton(texto)
            boton.setIcon(icons.icon(icono, "#f0f0f0"))
            boton.setIconSize(QSize(16, 16))
            boton.clicked.connect(lambda _, destino=url: self._abrir(destino))
            acciones.addWidget(boton)
        acciones.addStretch()
        layout.addLayout(acciones)

        botones = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        botones.button(QDialogButtonBox.Close).setText("Cerrar")
        botones.rejected.connect(self.reject)
        botones.accepted.connect(self.accept)
        layout.addWidget(botones)

    def _detalles(self):
        org = app_info.get('ORG_NAME')
        org_url = app_info.get('ORG_URL')
        autor = app_info.get('APP_AUTHOR')
        autor_url = app_info.get('APP_AUTHOR_URL')
        return [
            ("Organizacion", f'<a href="{org_url}" style="color:#3498db;">{org}</a>'),
            ("Autor", f'<a href="{autor_url}" style="color:#3498db;">{autor}</a>'),
            ("Licencia", f"{app_info.get('APP_LICENSE')} para el codigo fuente; "
                         "el ejecutable incluye componentes GPL v3"),
            ("Copyright", app_info.get('APP_COPYRIGHT')),
            ("Configuracion", user_config.config_dir()),
        ]

    @staticmethod
    def _abrir(url):
        if url:
            QDesktopServices.openUrl(_qurl(url))

    def _load_logo(self):
        local = app_info.org_logo_path()
        if local:
            pixmap = QPixmap(local)
            if not pixmap.isNull():
                self._logo.setPixmap(_rounded(pixmap, LOGO_SIZE))
                return

        url = app_info.get('ORG_LOGO_URL')
        if not url:
            return

        destino = os.path.join(user_config.config_dir(), "org_logo.png")
        if os.path.exists(destino):
            pixmap = QPixmap(destino)
            if not pixmap.isNull():
                self._logo.setPixmap(_rounded(pixmap, LOGO_SIZE))
                return

        self._downloader = LogoDownloader(url, destino, self)
        self._downloader.ready.connect(self._apply_logo)
        self._downloader.start()

    def _apply_logo(self, pixmap):
        if not pixmap.isNull():
            self._logo.setPixmap(_rounded(pixmap, LOGO_SIZE))

    def closeEvent(self, event):
        if self._downloader is not None and self._downloader.isRunning():
            self._downloader.wait(3000)
        super().closeEvent(event)


def _qurl(url):
    from PyQt5.QtCore import QUrl
    return QUrl(url)
