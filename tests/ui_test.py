"""Prueba del flujo real de la ventana: grabar, pausar, silenciar, cerrar y persistir."""

import pathlib as _pathlib
import sys as _sys
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))

import asyncio
import os
import threading

import qasync
from PyQt5.QtWidgets import QApplication

from src.config import user_config
from src.core.recording_manager import MIC, SPEAKERS
from src.ui.main_window import StreamApp

failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"  ok   {name}")
    else:
        failures.append(name)
        print(f"  FALLA {name} {detail}")


app = QApplication(_sys.argv)
loop = qasync.QEventLoop(app)
asyncio.set_event_loop(loop)

closed = asyncio.Event()
app.aboutToQuit.connect(closed.set)

window = StreamApp()
window.show()

print("configuracion en:", user_config.config_path())
print("mic preseleccionado    :", [d['name'] for d in window.selected_mics])
print("altavoz preseleccionado:", [d['name'] for d in window.selected_speakers])


async def guion():
    await asyncio.sleep(2)

    print("\nestado inicial")
    check("preview activo", window.preview_label.pixmap() is not None)
    check("medidores en marcha", window._meter_timer.isActive())
    check("temporizador oculto", not window.timer_label.isVisible())

    print("\nmute antes de grabar")
    window.mic_panel.mute_button.setChecked(True)
    check("panel refleja el mute", window.mic_panel.is_muted())
    check("slider deshabilitado al silenciar",
          not window.mic_panel.slider.isEnabled())

    print("\nvolumen")
    window.speaker_panel.set_volume(0.6)
    check("volumen aplicado", abs(window.speaker_panel.get_volume() - 0.6) < 0.01)

    print("\ngrabacion")
    await window.start_recording()
    check("grabando", window.is_recording)
    check("selector bloqueado", not window.screen_selector.isEnabled())
    check("temporizador visible", window.timer_label.isVisible())
    check("mute propagado a la pista",
          window.recording_manager._tracks[MIC].is_muted
          if MIC in window.recording_manager._tracks else True)
    check("volumen propagado a la pista",
          abs(window.recording_manager._tracks[SPEAKERS].volume - 0.6) < 0.01
          if SPEAKERS in window.recording_manager._tracks else True)

    await asyncio.sleep(2)
    check("temporizador avanza", window.timer_label.text() != "00:00")

    print("\npausa")
    window.toggle_pause()
    check("pausado", window.is_paused)
    frames_at_pause = window.recording_manager.frames_written
    await asyncio.sleep(1.5)
    check("no escribe frames en pausa",
          window.recording_manager.frames_written == frames_at_pause,
          f"({window.recording_manager.frames_written} vs {frames_at_pause})")

    window.toggle_pause()
    check("reanudado", not window.is_paused)
    await asyncio.sleep(2)

    print("\nmute en caliente durante la grabacion")
    window.speaker_panel.mute_button.setChecked(True)
    check("mute en vivo propagado",
          window.recording_manager._tracks[SPEAKERS].is_muted
          if SPEAKERS in window.recording_manager._tracks else True)
    await asyncio.sleep(1)

    print("\ndetencion")
    await window.stop_recording()
    check("ya no graba", not window.is_recording)
    check("selector reactivado", window.screen_selector.isEnabled())
    check("ruta guardada visible", window.saved_path_label.isVisible())
    check("archivo existe", bool(window._saved_path)
          and os.path.exists(window._saved_path))
    check("monitor de niveles reiniciado",
          bool(window._live_monitor.get_levels()))

    print("\npersistencia")
    window._save_config()
    stored = user_config.load()
    check("mute del micro guardado", stored['audio']['mic_muted'] is True)
    check("volumen guardado", abs(stored['audio']['speaker_volume'] - 0.6) < 0.01)
    check("monitor guardado", stored['monitor']['index'] == window.current_screen)
    check("dispositivo guardado por nombre",
          stored['audio']['speaker_device'] is None
          or isinstance(stored['audio']['speaker_device'], str))

    print("\ncierre")
    window.close()


async def ejecutar():
    """Un fallo del guion no debe dejar la prueba colgada para siempre."""
    try:
        await guion()
    except Exception:
        import traceback
        traceback.print_exc()
        failures.append("excepcion en el guion")
    finally:
        app.quit()

with loop:
    loop.create_task(ejecutar())
    loop.run_until_complete(closed.wait())

alive = [t.name for t in threading.enumerate() if t is not threading.main_thread()]
print("\nhilos vivos al salir:", alive)
print(f"{'FALLOS: ' + ', '.join(failures) if failures else 'OK: todos los flujos pasan'}")
_sys.exit(1 if failures else 0)
