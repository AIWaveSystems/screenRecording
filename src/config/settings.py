"""Configuración global de la aplicación."""
import os

VIDEO_FPS = 30
PREVIEW_FPS = 15
VIDEO_CODEC = 'XVID'
VIDEO_QUALITY = 3
PREVIEW_MAX_WIDTH = 640
CAPTURE_CURSOR = True

AUDIO_MAX_CHANNELS = 2
AUDIO_SAMPLE_RATE = 48000
AUDIO_CHUNK_SIZE = 1024
AUDIO_QUEUE_MAX = 512

OUTPUT_DIR = os.path.join(os.path.expanduser('~'), 'ScreenRecordings')
os.makedirs(OUTPUT_DIR, exist_ok=True)
