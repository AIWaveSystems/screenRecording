"""Genera logo.ico con todas las resoluciones que Windows pide.

El icono anterior tenía una sola imagen de 256x256, así que Windows la reducía
al vuelo para la barra de tareas y se veía borrosa. Aquí se dibuja cada tamaño
por separado, con el grosor de trazo proporcional, y se ensambla el contenedor
ICO a mano porque Qt solo escribe una imagen por archivo.

    python tools/make_icon.py
"""
import pathlib
import struct
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from PyQt5.QtCore import QBuffer, QByteArray, QIODevice
from PyQt5.QtWidgets import QApplication

from src.ui import icons

TAMANOS = (16, 20, 24, 32, 40, 48, 64, 128, 256)
DESTINO = pathlib.Path(__file__).resolve().parents[1] / "logo.ico"


def png_bytes(size):
    almacen = QByteArray()
    buffer = QBuffer(almacen)
    buffer.open(QIODevice.WriteOnly)
    if not icons.pixmap('app', "#f0f0f0", size).save(buffer, "PNG"):
        raise SystemExit(f"no se pudo renderizar el tamano {size}")
    buffer.close()
    return bytes(almacen)


def build_ico(imagenes):
    """Cabecera ICONDIR + una ICONDIRENTRY por imagen + los PNG al final."""
    cabecera = struct.pack('<HHH', 0, 1, len(imagenes))
    offset = len(cabecera) + 16 * len(imagenes)

    entradas = bytearray()
    cuerpo = bytearray()
    for size, blob in imagenes:
        entradas += struct.pack(
            '<BBBBHHII',
            0 if size >= 256 else size,
            0 if size >= 256 else size,
            0, 0, 1, 32, len(blob), offset,
        )
        cuerpo += blob
        offset += len(blob)

    return cabecera + bytes(entradas) + bytes(cuerpo)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    imagenes = [(size, png_bytes(size)) for size in TAMANOS]
    DESTINO.write_bytes(build_ico(imagenes))
    print(f"generado: {DESTINO} ({DESTINO.stat().st_size} bytes)")
    for size, blob in imagenes:
        print(f"  {size:3d}x{size:<3d} {len(blob):6d} bytes")
