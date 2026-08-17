"""Comprueba iconos, modo compacto y refuerzo del microfono, y guarda capturas."""

import pathlib as _pathlib
import sys as _sys
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))

import os

from PyQt5.QtWidgets import QApplication

from src.config import user_config
from src.ui import icons
from src.ui.main_window import StreamApp

failures = []
OUTDIR = os.path.abspath("_ui_shots")


def check(name, condition, detail=""):
    if condition:
        print(f"  ok   {name}")
    else:
        failures.append(name)
        print(f"  FALLA {name} {detail}")


app = QApplication(_sys.argv)

print("iconos")
for name in icons.available():
    pix = icons.pixmap(name, "#f0f0f0")
    check(f"'{name}' se dibuja", not pix.isNull() and pix.width() == icons.SIZE)

image = icons.pixmap('record', "#e74c3c").toImage()
opaque = sum(1 for y in range(0, image.height(), 4) for x in range(0, image.width(), 4)
             if image.pixelColor(x, y).alpha() > 0)
check("el icono no sale vacio", opaque > 10, f"(pixeles opacos: {opaque})")

window = StreamApp()
window.show()
app.processEvents()

os.makedirs(OUTDIR, exist_ok=True)

print("\nmodo texto")
window._apply_compact_mode(False)
app.processEvents()
check("boton de grabar con texto", window.record_button.text() != "")
check("boton de audio con texto", window.audio_button.text() == "Audio")
check("nombre del dispositivo visible", window.mic_panel._device.isVisible())
check("boton de grabar con icono", not window.record_button.icon().isNull())
width_text = window.mic_panel.width()
window.grab().save(os.path.join(OUTDIR, "modo_texto.png"))

print("\nmodo iconos")
window._apply_compact_mode(True)
app.processEvents()
check("boton de grabar sin texto", window.record_button.text() == "")
check("boton de grabar conserva icono", not window.record_button.icon().isNull())
check("tooltip informativo", "Grabacion" in window.record_button.toolTip()
      or "Detener" in window.record_button.toolTip())
check("boton de audio sin texto", window.audio_button.text() == "")
check("nombre del dispositivo oculto", not window.mic_panel._device.isVisible())
check("el mezclador ocupa menos", window.mic_panel.width() < width_text,
      f"({window.mic_panel.width()} vs {width_text})")
window.grab().save(os.path.join(OUTDIR, "modo_iconos.png"))

print("\nmute cambia el icono")
window.mic_panel.set_muted(False)
app.processEvents()
normal = window.mic_panel.mute_button.icon().pixmap(32, 32).toImage()

window.mic_panel.mute_button.setChecked(True)
app.processEvents()
muted = window.mic_panel.mute_button.icon().pixmap(32, 32).toImage()

check("el icono de mute cambia de dibujo", normal != muted)
check("el medidor se marca como silenciado", window.mic_panel.meter._muted)
window.mic_panel.mute_button.setChecked(False)
app.processEvents()
check("al reactivar vuelve el icono normal",
      window.mic_panel.mute_button.icon().pixmap(32, 32).toImage() == normal)

print("\nrefuerzo del microfono")
window.recording_manager.set_mic_boost(1.2)
window.mic_panel.set_boost(1.2)
app.processEvents()
check("en compacto el refuerzo no desborda la columna",
      window.mic_panel._value.text().count('%') == 1,
      f"('{window.mic_panel._value.text()}')")

window._apply_compact_mode(False)
app.processEvents()
check("en modo texto el panel muestra el refuerzo",
      "+20%" in window.mic_panel._value.text(),
      f"('{window.mic_panel._value.text()}')")
window._apply_compact_mode(True)
check("se limita el maximo", window.recording_manager.set_mic_boost(9.0) is None
      and window.recording_manager.mic_boost <= 3.0)
check("no baja de 1.0", window.recording_manager.set_mic_boost(0.1) is None
      and window.recording_manager.mic_boost == 1.0)

window.recording_manager.set_mic_boost(1.15)

print("\npersistencia")
window._save_config()
stored = user_config.load()
check("refuerzo guardado", abs(stored['audio']['mic_boost'] - 1.15) < 0.001)
check("modo compacto guardado", stored['ui']['compact'] is True)

window._apply_compact_mode(False)
window._save_config()
check("modo texto guardado", user_config.load()['ui']['compact'] is False)

window.close()
print(f"\ncapturas en {OUTDIR}")
print(f"{'FALLOS: ' + ', '.join(failures) if failures else 'OK: interfaz correcta'}")
_sys.exit(1 if failures else 0)
