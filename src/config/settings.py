# Configuración de Video
VIDEO_FPS = 20  # Reducido de 30 a 20 para menor uso de CPU
VIDEO_CODEC = 'XVID'
VIDEO_QUALITY = 1  # 1 es la mejor calidad, aumentar para reducir tamaño

# Configuración de Audio
AUDIO_CHANNELS = 2
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHUNK_SIZE = 4096  # Aumentado para reducir la carga de CPU
AUDIO_FORMAT = 'int16'

# Configuración de Buffer
PREVIEW_SCALE = 0.75  # Escala de previsualización (reducir para menor uso de memoria)
BUFFER_SIZE = 10  # Número de frames en buffer

# Optimización
PROCESS_PRIORITY = 'normal'  # Puede ser 'low', 'normal', 'high'
THREAD_PRIORITY = 'normal'
USE_GPU = False  # Activar solo si hay GPU disponible

# Paths
import os
OUTPUT_DIR = os.path.join(os.path.expanduser('~'), 'ScreenRecordings')
TEMP_DIR = os.path.join(OUTPUT_DIR, 'temp')

# Crear directorios necesarios
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True) 