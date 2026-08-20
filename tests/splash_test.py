"""Verifica la pantalla de carga y el icono de la aplicacion."""

import pathlib as _pathlib
import sys as _sys
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))

import os
import struct
import time

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QApplication

from src.ui import icons
from src.ui.splash import SplashScreen

failures = []
OUTDIR = os.path.abspath("_ui_shots")
RAIZ = _pathlib.Path(__file__).resolve().parents[1]


def check(name, condition, detail=""):
    if condition:
        print(f"  ok   {name}")
    else:
        failures.append(name)
        print(f"  FALLA {name} {detail}")


app = QApplication(_sys.argv)
app.setWindowIcon(icons.app_icon())
os.makedirs(OUTDIR, exist_ok=True)

print("aparicion")
t0 = time.perf_counter()
splash = SplashScreen("v1.0")
splash.show()
app.processEvents()
elapsed = (time.perf_counter() - t0) * 1000
check("se construye y muestra rapido", elapsed < 500, f"({elapsed:.0f} ms)")
check("es visible", splash.isVisible())

print()
print("progreso")
splash.set_progress(0, "Preparando...")
check("empieza en 0", splash._progress.value() == 0)

for value, message in ((25, "Cargando audio..."), (65, "Construyendo...")):
    splash.set_progress(value, message)
    check(f"acepta {value}%", splash._progress.value() == value)
    check(f"muestra el mensaje de {value}%", splash._status.text() == message)

splash.set_progress(999, None)
check("recorta por encima de 100", splash._progress.value() == 100)
splash.set_progress(-50, None)
check("recorta por debajo de 0", splash._progress.value() == 0)
check("un mensaje None conserva el anterior",
      splash._status.text() == "Construyendo...")

print()
print("aspecto")
splash.set_progress(65, "Construyendo la interfaz...")
app.processEvents()
shot = splash.grab()
check("se pinta contenido", not shot.isNull() and shot.width() > 100)
image = shot.toImage()
colores = {image.pixelColor(x, y).name()
           for x in range(0, image.width(), 7)
           for y in range(0, image.height(), 7)}
check("no sale en blanco", len(colores) > 3, f"(colores distintos: {len(colores)})")
shot.save(os.path.join(OUTDIR, "pantalla_carga.png"))

print()
print("cierre")
splash.finish()
app.processEvents()
check("llega al 100 al terminar", splash._progress.value() == 100)
check("se oculta", not splash.isVisible())

print()
print("icono de la aplicacion")
ruta_ico = RAIZ / "logo.ico"
check("logo.ico existe", ruta_ico.exists())
if ruta_ico.exists():
    datos = ruta_ico.read_bytes()
    _, tipo, imagenes = struct.unpack('<HHH', datos[:6])
    check("es un .ico valido", tipo == 1, f"(tipo {tipo})")
    check("trae varias resoluciones", imagenes >= 6, f"({imagenes} imagenes)")

icono = icons.app_icon()
check("se carga el icono de la aplicacion", not icono.isNull())
disponibles = sorted(s.width() for s in icono.availableSizes())
check("incluye los tamanos de barra de tareas",
      16 in disponibles and 32 in disponibles, f"{disponibles}")

for lado in (16, 32, 48):
    pixmap = icono.pixmap(QSize(lado, lado))
    check(f"se dibuja a {lado}px", not pixmap.isNull() and pixmap.width() == lado)
    render = pixmap.toImage()
    opacos = sum(1 for x in range(0, lado, 2) for y in range(0, lado, 2)
                 if render.pixelColor(x, y).alpha() > 0)
    check(f"a {lado}px no sale vacio", opacos > (lado // 2) ** 2 * 0.3,
          f"({opacos} puntos opacos)")

print()
print("integracion con la ventana principal")
from src.ui.main_window import StreamApp

pasos = []
splash2 = SplashScreen("v1.0")
splash2.show()


def registrar(value, message=None):
    pasos.append((value, message))
    splash2.set_progress(value, message)


t0 = time.perf_counter()
window = StreamApp(progress=registrar)
build_ms = (time.perf_counter() - t0) * 1000
window.show()
splash2.finish(window)
app.processEvents()

check("la ventana reporta progreso", len(pasos) >= 5, f"({len(pasos)} pasos)")
check("el progreso solo avanza",
      all(b[0] >= a[0] for a, b in zip(pasos, pasos[1:])), f"{[p[0] for p in pasos]}")
check("todos los pasos llevan mensaje", all(p[1] for p in pasos))
check("termina cerca del final", pasos[-1][0] >= 90, f"(ultimo {pasos[-1][0]}%)")
check("la ventana queda visible", window.isVisible())
check("la carga se cierra", not splash2.isVisible())
check("la ventana hereda el icono", not window.windowIcon().isNull())
print(f"  (construccion de la ventana: {build_ms:.0f} ms)")
for value, message in pasos:
    print(f"     {value:3d}%  {message}")

window.close()
app.processEvents()

print()
print("sin pantalla de carga sigue funcionando")
sin_splash = StreamApp()
check("el parametro progress es opcional", sin_splash is not None)
sin_splash.close()
app.processEvents()

print()
print(f"captura en {OUTDIR}")
print("FALLOS: " + ", ".join(failures) if failures
      else "OK: pantalla de carga e icono correctos")
_sys.exit(1 if failures else 0)
