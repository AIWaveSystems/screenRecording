# Registro de cambios

## Sin publicar

### Añadido
- Configuración persistente en `%APPDATA%\ScreenRecorder\config.json`
  (`schema_version` 1): carpeta de salida, monitor, dispositivos de audio por
  nombre, volúmenes, silencios, FPS y cursor.
- Modo portable: si existe un `portable.txt` junto al ejecutable, la
  configuración se guarda en la carpeta de la aplicación.
- Menú *Archivo* y *Configuración*: abrir carpeta de grabaciones, cambiar
  carpeta de salida, abrir carpeta de configuración y restablecer valores.
- `--purge` para borrar configuración y logs, y `--config-path` para consultar
  la ruta del archivo. Las grabaciones nunca se borran sin confirmación aparte.
- Mezclador con silencio por pista (micrófono y audio del sistema), aplicable
  antes y durante la grabación.
- Volumen por pista ajustable en caliente, sin detener la grabación.
- Temporizador de grabación en la ventana.
- Posición y tamaño de la ventana recordados en `state.json`.

### Corregido
- **Vídeo al doble de velocidad y audio desincronizado**: los frames se
  escribían al ritmo del temporizador de la interfaz (15 Hz) mientras el
  archivo declaraba 30 fps. Ahora el número de frames lo decide el reloj real.
- **Cierres inesperados de la aplicación**: `soundcard` provocaba violaciones
  de acceso intermitentes (~1 de cada 2 arranques en pruebas) al usarse a la
  vez que la captura de pantalla. El audio del sistema pasa a capturarse con
  `PyAudioWPatch`, sobre PortAudio, igual que el micrófono.
- **Audio del sistema más corto que el vídeo**: WASAPI no entrega datos
  mientras no suena nada, así que los tramos en silencio se rellenan contra el
  reloj para que la pista conserve su duración real.
- Silenciar una pista ya no acorta el archivo de audio: se escribe silencio en
  lugar de descartar los bloques.
- La pausa ya no descuadra la duración del vídeo.
- El medidor de niveles vuelve a funcionar tras detener una grabación.
- `sys.exit()` dentro del cierre de la ventana dejaba hilos vivos; ahora el
  cierre es ordenado.
- Abrir una carpeta inexistente ya no lanza una excepción sin gestionar.
- No se destruye el hilo de captura mientras sigue en ejecución.
- El diálogo de audio avisa en lugar de no hacer nada si se abre grabando.

### Cambiado
- El mezclador sustituye a los medidores y sliders sueltos, y muestra qué
  dispositivo está asignado a cada pista.
- `RecordingManager` expone `set_volume`, `set_muted` y `get_levels` con las
  claves `mic` y `speakers`, en lugar de exigir acceso a atributos privados.
- Dependencia `soundcard` sustituida por `PyAudioWPatch`.

## Anterior

### Corregido
- Sincronía audio/vídeo, fuga de handles GDI en la captura del cursor,
  renderizado del cursor, cierre de la aplicación, congelación de la interfaz
  al guardar, negociación de canales de audio y mezcla sin recodificar.

### Cambiado
- FFmpeg incluido mediante `imageio-ffmpeg`.
- Eliminados `src/ui.py` y la infraestructura asíncrona sin usar.
