"""Verifica que el refuerzo del microfono se aplica de verdad al WAV grabado."""

import pathlib as _pathlib
import sys as _sys
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))

import os
import shutil
import tempfile
import wave

import numpy as np

from src.core.audio_capture import BaseTrack

failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"  ok   {name}")
    else:
        failures.append(name)
        print(f"  FALLA {name} {detail}")


WORKDIR = tempfile.mkdtemp(prefix="srboost_")


def render(volume, boost, muted=False, amplitude=0.3, blocks=8):
    """Escribe una senal conocida por la pista y devuelve el pico resultante."""
    path = os.path.join(WORKDIR, f"t_{volume}_{boost}_{muted}.wav")
    track = BaseTrack("prueba", path)
    track.volume = volume
    track.boost = boost
    track.set_muted(muted)
    track._open_wav(1, 48000)

    tone = (np.ones((512, 1), dtype=np.float32) * amplitude)
    for _ in range(blocks):
        track._submit(tone.copy())
    track._running = False
    track._close_wav()

    with wave.open(path) as wav:
        data = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)
    return (float(np.abs(data).max()) / 32767.0) if data.size else 0.0


print("ganancia aplicada al archivo")
plain = render(1.0, 1.0)
check("sin refuerzo se graba la senal tal cual", abs(plain - 0.3) < 0.01,
      f"(pico {plain:.3f})")

boosted = render(1.0, 1.15)
check("con +15% la senal sube un 15%", abs(boosted - 0.345) < 0.01,
      f"(pico {boosted:.3f})")
check("el microfono queda por encima de la salida", boosted > plain,
      f"({boosted:.3f} vs {plain:.3f})")

ratio = boosted / plain
check("la relacion es la esperada", abs(ratio - 1.15) < 0.02, f"(x{ratio:.3f})")

print("\ncombinacion con el volumen de la pista")
half = render(0.5, 1.15)
check("volumen y refuerzo se multiplican", abs(half - 0.5 * 0.345) < 0.01,
      f"(pico {half:.3f})")

print("\nproteccion contra saturacion")
loud = render(1.0, 3.0, amplitude=0.9)
check("nunca supera el maximo del formato", loud <= 1.0, f"(pico {loud:.3f})")

print("\nsilencio")
silent = render(1.0, 1.15, muted=True)
check("silenciado graba silencio", silent == 0.0, f"(pico {silent:.3f})")

path = os.path.join(WORKDIR, "t_1.0_1.15_True.wav")
with wave.open(path) as wav:
    frames_muted = wav.getnframes()
with wave.open(os.path.join(WORKDIR, "t_1.0_1.15_False.wav")) as wav:
    frames_normal = wav.getnframes()
check("silenciar no acorta la pista", frames_muted == frames_normal,
      f"({frames_muted} vs {frames_normal})")

shutil.rmtree(WORKDIR, ignore_errors=True)
print(f"\n{'FALLOS: ' + ', '.join(failures) if failures else 'OK: refuerzo correcto'}")
_sys.exit(1 if failures else 0)
