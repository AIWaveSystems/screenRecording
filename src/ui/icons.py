"""Iconos vectoriales dibujados en tiempo de ejecución.

No dependen de archivos externos, así que sobreviven al empaquetado con
PyInstaller y se adaptan a cualquier color del tema.
"""
from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

SIZE = 64


def _pen(painter, color, width, cap=Qt.RoundCap):
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setCapStyle(cap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)


def _fill(painter, color):
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color))


def _record(painter, s, color):
    _fill(painter, color)
    painter.drawEllipse(QRectF(s * 0.20, s * 0.20, s * 0.60, s * 0.60))


def _stop(painter, s, color):
    _fill(painter, color)
    painter.drawRoundedRect(QRectF(s * 0.24, s * 0.24, s * 0.52, s * 0.52),
                            s * 0.06, s * 0.06)


def _pause(painter, s, color):
    _fill(painter, color)
    bar = s * 0.16
    painter.drawRoundedRect(QRectF(s * 0.26, s * 0.22, bar, s * 0.56),
                            bar * 0.35, bar * 0.35)
    painter.drawRoundedRect(QRectF(s * 0.58, s * 0.22, bar, s * 0.56),
                            bar * 0.35, bar * 0.35)


def _play(painter, s, color):
    _fill(painter, color)
    path = QPainterPath()
    path.moveTo(s * 0.30, s * 0.20)
    path.lineTo(s * 0.78, s * 0.50)
    path.lineTo(s * 0.30, s * 0.80)
    path.closeSubpath()
    painter.drawPath(path)


def _folder(painter, s, color):
    _fill(painter, color)
    path = QPainterPath()
    path.moveTo(s * 0.12, s * 0.76)
    path.lineTo(s * 0.12, s * 0.26)
    path.lineTo(s * 0.40, s * 0.26)
    path.lineTo(s * 0.48, s * 0.36)
    path.lineTo(s * 0.88, s * 0.36)
    path.lineTo(s * 0.88, s * 0.76)
    path.closeSubpath()
    painter.drawPath(path)


def _mic_body(painter, s, color):
    _fill(painter, color)
    width = s * 0.26
    painter.drawRoundedRect(QRectF((s - width) / 2, s * 0.12, width, s * 0.44),
                            width / 2, width / 2)
    _pen(painter, color, s * 0.07)
    painter.drawArc(QRectF(s * 0.26, s * 0.34, s * 0.48, s * 0.44),
                    180 * 16, 180 * 16)
    painter.drawLine(QPointF(s * 0.50, s * 0.78), QPointF(s * 0.50, s * 0.88))


def _mic(painter, s, color):
    _mic_body(painter, s, color)


def _speaker_body(painter, s, color):
    _fill(painter, color)
    path = QPainterPath()
    path.moveTo(s * 0.10, s * 0.38)
    path.lineTo(s * 0.26, s * 0.38)
    path.lineTo(s * 0.46, s * 0.18)
    path.lineTo(s * 0.46, s * 0.82)
    path.lineTo(s * 0.26, s * 0.62)
    path.lineTo(s * 0.10, s * 0.62)
    path.closeSubpath()
    painter.drawPath(path)


def _speaker(painter, s, color):
    _speaker_body(painter, s, color)
    _pen(painter, color, s * 0.07)
    painter.drawArc(QRectF(s * 0.46, s * 0.32, s * 0.24, s * 0.36), -70 * 16, 140 * 16)
    painter.drawArc(QRectF(s * 0.46, s * 0.20, s * 0.42, s * 0.60), -70 * 16, 140 * 16)


def _cross(painter, s, color):
    _pen(painter, color, s * 0.09)
    painter.drawLine(QPointF(s * 0.58, s * 0.36), QPointF(s * 0.86, s * 0.64))
    painter.drawLine(QPointF(s * 0.86, s * 0.36), QPointF(s * 0.58, s * 0.64))


def _speaker_off(painter, s, color):
    _speaker_body(painter, s, color)
    _cross(painter, s, color)


def _slash(painter, s, color):
    _pen(painter, color, s * 0.09)
    painter.drawLine(QPointF(s * 0.18, s * 0.86), QPointF(s * 0.82, s * 0.14))


def _mic_off(painter, s, color):
    _mic_body(painter, s, color)
    _slash(painter, s, color)


def _sliders(painter, s, color):
    _pen(painter, color, s * 0.08)
    for x in (0.28, 0.50, 0.72):
        painter.drawLine(QPointF(s * x, s * 0.16), QPointF(s * x, s * 0.84))
    _fill(painter, color)
    for x, knob in ((0.28, 0.36), (0.50, 0.62), (0.72, 0.46)):
        painter.drawEllipse(QPointF(s * x, s * knob), s * 0.11, s * 0.11)


def _monitor(painter, s, color):
    _pen(painter, color, s * 0.08)
    painter.drawRoundedRect(QRectF(s * 0.12, s * 0.18, s * 0.76, s * 0.50),
                            s * 0.06, s * 0.06)
    painter.drawLine(QPointF(s * 0.34, s * 0.84), QPointF(s * 0.66, s * 0.84))
    painter.drawLine(QPointF(s * 0.50, s * 0.68), QPointF(s * 0.50, s * 0.84))


def _gear(painter, s, color):
    _pen(painter, color, s * 0.09)
    painter.drawEllipse(QPointF(s * 0.50, s * 0.50), s * 0.16, s * 0.16)
    painter.drawEllipse(QPointF(s * 0.50, s * 0.50), s * 0.32, s * 0.32)


def _boost(painter, s, color):
    _pen(painter, color, s * 0.09)
    painter.drawLine(QPointF(s * 0.50, s * 0.84), QPointF(s * 0.50, s * 0.20))
    painter.drawLine(QPointF(s * 0.28, s * 0.42), QPointF(s * 0.50, s * 0.18))
    painter.drawLine(QPointF(s * 0.72, s * 0.42), QPointF(s * 0.50, s * 0.18))


def _exit(painter, s, color):
    _pen(painter, color, s * 0.09)
    painter.drawArc(QRectF(s * 0.22, s * 0.22, s * 0.56, s * 0.56), 60 * 16, 240 * 16)
    painter.drawLine(QPointF(s * 0.50, s * 0.14), QPointF(s * 0.50, s * 0.46))


def _reset(painter, s, color):
    _pen(painter, color, s * 0.09)
    painter.drawArc(QRectF(s * 0.20, s * 0.20, s * 0.60, s * 0.60), 40 * 16, 280 * 16)
    _fill(painter, color)
    path = QPainterPath()
    path.moveTo(s * 0.74, s * 0.12)
    path.lineTo(s * 0.88, s * 0.40)
    path.lineTo(s * 0.58, s * 0.36)
    path.closeSubpath()
    painter.drawPath(path)


def _compact(painter, s, color):
    _pen(painter, color, s * 0.08)
    painter.drawRoundedRect(QRectF(s * 0.14, s * 0.14, s * 0.30, s * 0.30), 4, 4)
    painter.drawRoundedRect(QRectF(s * 0.56, s * 0.14, s * 0.30, s * 0.30), 4, 4)
    painter.drawRoundedRect(QRectF(s * 0.14, s * 0.56, s * 0.30, s * 0.30), 4, 4)
    painter.drawRoundedRect(QRectF(s * 0.56, s * 0.56, s * 0.30, s * 0.30), 4, 4)


_DRAWERS = {
    'record': _record,
    'stop': _stop,
    'pause': _pause,
    'play': _play,
    'folder': _folder,
    'mic': _mic,
    'mic_off': _mic_off,
    'speaker': _speaker,
    'speaker_off': _speaker_off,
    'sliders': _sliders,
    'monitor': _monitor,
    'gear': _gear,
    'boost': _boost,
    'exit': _exit,
    'reset': _reset,
    'compact': _compact,
}

_CACHE = {}


def pixmap(name, color="#f0f0f0", size=SIZE):
    key = (name, color, size)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    drawer = _DRAWERS.get(name)
    canvas = QPixmap(size, size)
    canvas.fill(Qt.transparent)
    if drawer is not None:
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.Antialiasing)
        drawer(painter, size, color)
        painter.end()

    _CACHE[key] = canvas
    return canvas


def icon(name, color="#f0f0f0", size=SIZE):
    return QIcon(pixmap(name, color, size))


def available():
    return sorted(_DRAWERS)
