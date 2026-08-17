"""Prueba del flujo real de la ventana: arrancar, grabar, parar y cerrar."""

import pathlib as _pathlib
import sys as _sys
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))
import asyncio
import os
import sys

import qasync
from PyQt5.QtWidgets import QApplication

from src.ui.main_window import StreamApp

app = QApplication(sys.argv)
loop = qasync.QEventLoop(app)
asyncio.set_event_loop(loop)

closed = asyncio.Event()
app.aboutToQuit.connect(closed.set)

window = StreamApp()
window.show()

print("mic preseleccionado    :", [d['name'] for d in window.selected_mics])
print("altavoz preseleccionado:", [d['name'] for d in window.selected_speakers])


async def guion():
    await asyncio.sleep(2)
    print("preview activo:", window.preview_label.pixmap() is not None)

    print("-> iniciando grabacion")
    await window.start_recording()
    assert window.is_recording, "no arranco la grabacion"
    assert not window.screen_selector.isEnabled(), "el selector debia bloquearse"

    await asyncio.sleep(5)

    print("-> deteniendo grabacion")
    await window.stop_recording()
    assert not window.is_recording
    assert window.screen_selector.isEnabled(), "el selector debia reactivarse"
    print("estado:", window.status_label.text())

    print("-> cerrando ventana")
    window.close()
    app.quit()

with loop:
    loop.create_task(guion())
    loop.run_until_complete(closed.wait())

print("hilos vivos al salir:", [t.name for t in __import__('threading').enumerate()
                                if t is not __import__('threading').main_thread()])
print("OK: la app arranco, grabo y cerro sin bloquearse")
