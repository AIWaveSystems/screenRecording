"""Prueba de humo: captura + grabacion real, sin UI."""

import pathlib as _pathlib
import sys as _sys
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))
import os
import sys
import time
import wave

import cv2
import sounddevice as sd
from PyQt5.QtWidgets import QApplication

from src.core.recording_manager import RecordingManager
from src.core.screen_capture import ScreenCaptureThread
from src.ui.main_window import get_screen_list

DURATION = 6.0

app = QApplication(sys.argv)
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

mgr = RecordingManager(os.path.abspath("_smoke_out"))
mgr.start(mon, [speaker] if speaker else [], [], lambda: cap.latest_frame)
t_start = time.perf_counter()
time.sleep(DURATION)
paths = mgr.stop()
wall = time.perf_counter() - t_start
print("offsets de audio:", {k: round(v, 3) for k, v in paths['offsets'].items()})

for key in ('mic', 'speakers'):
    path = paths.get(key)
    if path and os.path.exists(path):
        with wave.open(path) as wav:
            print(f"{key}: {wav.getnchannels()}ch {wav.getframerate()}Hz "
                  f"{wav.getnframes() / wav.getframerate():.2f}s")

final = mgr.finalize(paths)
cap.stop()

print(f"\n--- resultados (grabacion real {wall:.2f}s) ---")
video = cv2.VideoCapture(final)
frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
fps = video.get(cv2.CAP_PROP_FPS)
width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
video.release()
print(f"video: {width}x{height} {fps}fps {frames} frames = {frames / fps:.2f}s "
      f"(desvio {frames / fps - wall:+.2f}s)")
print("tamano:", os.path.getsize(final), "bytes")
