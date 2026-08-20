"""Verifica el .env, la ventana Acerca de y la marca en la pantalla de carga."""

import pathlib as _pathlib
import sys as _sys
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))

import os
import tempfile

from PyQt5.QtWidgets import QApplication

from src.config import app_info

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
os.makedirs(OUTDIR, exist_ok=True)

print("archivo .env")
env = RAIZ / ".env"
check(".env existe", env.exists())
check(".env.example existe", (RAIZ / ".env.example").exists())
claves = {l.split('=')[0].strip() for l in env.read_text(encoding='utf-8').splitlines()
          if '=' in l and not l.strip().startswith('#')}
faltan = set(app_info.DEFAULTS) - claves
check("el .env cubre todas las claves", not faltan, f"(faltan {sorted(faltan)})")

print()
print("lectura de valores")
check("version leida del .env", app_info.get('APP_VERSION') == "1.0.0",
      f"('{app_info.get('APP_VERSION')}')")
check("etiqueta de version", app_info.version_label() == "v1.0.0")
check("organizacion", app_info.get('ORG_NAME') == "AIWaveSystems")
check("lema con la organizacion", "AIWaveSystems" in app_info.get('ORG_TAGLINE'))
check("url del logo", app_info.get('ORG_LOGO_URL').startswith("https://"))

print()
print("tolerancia a fallos")
valores = app_info._parse(str(RAIZ / ".env"))
check("el parser lee pares clave=valor", valores.get('ORG_NAME') == "AIWaveSystems")
temporal = _pathlib.Path(tempfile.mkdtemp()) / "roto.env"
temporal.write_text("basura sin igual\n\n# comentario\nAPP_VERSION=9.9.9\n",
                    encoding="utf-8")
sueltos = app_info._parse(str(temporal))
check("ignora lineas invalidas y comentarios", sueltos == {'APP_VERSION': '9.9.9'},
      f"{sueltos}")
check("hay valores por defecto para todo",
      all(app_info.DEFAULTS.get(k) for k in app_info.DEFAULTS))

print()
print("logo de la organizacion")
ruta = app_info.org_logo_path()
check("el logo incluido se encuentra", ruta is not None and os.path.exists(ruta))
if ruta:
    from PyQt5.QtGui import QPixmap
    pixmap = QPixmap(ruta)
    check("el logo se puede cargar", not pixmap.isNull(),
          f"({pixmap.width()}x{pixmap.height()})")
    check("tiene resolucion suficiente", pixmap.width() >= 128)

print()
print("ventana Acerca de")
from src.ui.about import AboutDialog

dialogo = AboutDialog()
check("se construye", dialogo is not None)
check("el titulo nombra la aplicacion",
      app_info.get('APP_NAME') in dialogo.windowTitle())

etiquetas = dialogo.findChildren(__import__('PyQt5.QtWidgets', fromlist=['QLabel']).QLabel)
textos = " ".join(e.text() for e in etiquetas)
check("muestra la version", "1.0.0" in textos, )
check("muestra la organizacion", "AIWaveSystems" in textos)
check("muestra el lema", app_info.get('ORG_TAGLINE') in textos)
check("muestra el autor", app_info.get('APP_AUTHOR') in textos)
check("muestra la licencia", "MIT" in textos)
check("muestra la ruta de configuracion", "ScreenRecorder" in textos)
check("el logo esta renderizado",
      any(not e.pixmap().isNull() for e in etiquetas if e.pixmap() is not None))

dialogo.show()
app.processEvents()
dialogo.grab().save(os.path.join(OUTDIR, "acerca_de.png"))
dialogo.close()

print()
print("marca en la pantalla de carga")
from src.ui.splash import SplashScreen

splash = SplashScreen()
splash.show()
app.processEvents()
hijos = splash.findChildren(__import__('PyQt5.QtWidgets', fromlist=['QLabel']).QLabel)
texto_splash = " ".join(e.text() for e in hijos)
check("muestra la version del .env", "v1.0.0" in texto_splash, f"('{texto_splash}')")
check("muestra el lema de la organizacion",
      app_info.get('ORG_TAGLINE') in texto_splash)
splash.grab().save(os.path.join(OUTDIR, "pantalla_carga_marca.png"))
splash.close()

print()
print(f"capturas en {OUTDIR}")
print("FALLOS: " + ", ".join(failures) if failures
      else "OK: marca, .env y Acerca de correctos")
_sys.exit(1 if failures else 0)
