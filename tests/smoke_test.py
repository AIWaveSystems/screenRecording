"""Prueba de humo: graba de verdad y verifica duracion, sincronia y mute."""

import pathlib as _pathlib
import sys as _sys
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))

import os
import shutil
import time
import wave

import cv2
import sounddevice as sd
from PyQt5.QtWidgets import QApplication

from src.core.recording_manager import MIC, SPEAKERS, RecordingManager
from src.core.screen_capture import ScreenCaptureThread
from src.ui.main_window import get_screen_list

DURATION = 6.0
UI_TIMER_HZ = 15
OUTDIR = os.path.abspath("_smoke_out")

app = QApplication(_sys.argv)
screens = get_screen_list()
print("monitores:", [s['name'] for s in screens])
mon = screens[0]['monitor']

cap = ScreenCaptureThread(mon)
cap.start()
time.sleep(1.0)
assert cap.latest_frame is not None, "no llego ningun frame"
print("frame:", cap.latest_frame.shape, cap.latest_frame.dtype)

seen, prev = 0, None
t0 = time.perf_counter()
while time.perf_counter() - t0 < 2.0:
    frame = cap.latest_frame
    if frame is not prev:
        seen += 1
        prev = frame
    time.sleep(0.002)
print(f"FPS de captura: {seen / 2.0:.1f}")

speaker = None
for i, dev in enumerate(sd.query_devices()):
    if (dev['max_output_channels'] > 0
            and 'wasapi' in sd.query_hostapis(dev['hostapi'])['name'].lower()):
        speaker = {'id': i, 'name': dev['name']}
        break
print("altavoz:", speaker)

shutil.rmtree(OUTDIR, ignore_errors=True)
mgr = RecordingManager(OUTDIR)
mgr.start(mon, [speaker] if speaker else [], [])
t_start = time.perf_counter()

print(f"grabando {DURATION}s bombeando frames a {UI_TIMER_HZ} Hz "
      f"(el archivo declara {mgr.fps} fps)")
muted_from, muted_to = 2.0, 4.0
was_muted = False
while True:
    elapsed = time.perf_counter() - t_start
    if elapsed >= DURATION:
        break
    should_mute = muted_from <= elapsed < muted_to
    if should_mute != was_muted:
        mgr.set_muted(SPEAKERS, should_mute)
        was_muted = should_mute
        print(f"  t={elapsed:.1f}s -> sistema {'silenciado' if should_mute else 'activo'}")
    mgr.write_frame(cap.latest_frame)
    time.sleep(1.0 / UI_TIMER_HZ)

paths = mgr.stop()
wall = time.perf_counter() - t_start
print("offsets de audio:", {k: round(v, 3) for k, v in paths['offsets'].items()})

audio_durations = {}
for key in (MIC, SPEAKERS):
    path = paths.get(key)
    if path and os.path.exists(path):
        with wave.open(path) as wav:
            seconds = wav.getnframes() / wav.getframerate()
            audio_durations[key] = seconds
            print(f"{key}: {wav.getnchannels()}ch {wav.getframerate()}Hz "
                  f"{seconds:.2f}s")

final = mgr.finalize(paths)
cap.stop()

print(f"\n--- resultados (grabacion real {wall:.2f}s) ---")
video = cv2.VideoCapture(final)
frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
fps = video.get(cv2.CAP_PROP_FPS)
width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
video.release()
duration = frames / fps
print(f"video: {width}x{height} {fps}fps {frames} frames = {duration:.2f}s "
      f"(desvio {duration - wall:+.2f}s)")
print("tamano:", os.path.getsize(final), "bytes")

errors = []
if abs(duration - wall) > 0.5:
    errors.append(f"la duracion del video se desvia {duration - wall:+.2f}s")
for key, seconds in audio_durations.items():
    if abs(seconds - wall) > 0.5:
        errors.append(f"el audio '{key}' dura {seconds:.2f}s frente a {wall:.2f}s "
                      "(el mute no debe acortar la pista)")

if errors:
    print("\nFALLOS:")
    for error in errors:
        print(" -", error)
    _sys.exit(1)
print("\nOK: duracion, sincronia y mute correctos")
