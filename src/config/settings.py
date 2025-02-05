"""Configuración global de la aplicación."""
import os

# Configuración de Video
VIDEO_FPS = 30  # FPS para la grabación
PREVIEW_FPS = 30  # FPS para la previsualización
VIDEO_CODEC = 'XVID'
VIDEO_QUALITY = 1  # 1 es la mejor calidad, aumentar para reducir tamaño

# Configuración de Audio
AUDIO_CHANNELS = 2  # Cambiado a 2 canales (stereo)
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHUNK_SIZE = 1024
AUDIO_FORMAT = 'int16'

# Configuración de Buffer
PREVIEW_SCALE = 0.75  # Escala de previsualización (reducir para menor uso de memoria)
BUFFER_SIZE = 10  # Número de frames en buffer

# Optimización
PROCESS_PRIORITY = 'normal'  # Puede ser 'low', 'normal', 'high'
THREAD_PRIORITY = 'normal'
USE_GPU = False  # Activar solo si hay GPU disponible

# Paths
TEMP_DIR = os.path.join(os.path.expanduser('~'), 'ScreenRecordings', 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

# Crear directorios necesarios
OUTPUT_DIR = os.path.join(os.path.expanduser('~'), 'ScreenRecordings')
os.makedirs(OUTPUT_DIR, exist_ok=True) 