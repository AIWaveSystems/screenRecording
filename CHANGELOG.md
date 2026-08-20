# Registro de cambios

## v1.0 — 2026-08-17

Primera versión publicada.
[Descargar](https://github.com/AIWaveSystems/screenRecording/releases/latest)

### Añadido
- **Pantalla de carga** al arrancar, con logo, barra de progreso y el paso en
  curso. Cubre los segundos de importar Qt, OpenCV y los backends de audio, más
  la enumeración de dispositivos. En el ejecutable se apoya en la pantalla nativa
  de PyInstaller, que aparece durante la extracción, antes de que exista
  intérprete de Python.
- **Ventana Acerca de** (*Ayuda → Acerca de*) con el logo de la organización,
  versión, autor, licencia, ruta de configuración y accesos al repositorio, las
  novedades y el reporte de fallos.
- **Archivo `.env`** con el nombre, la versión y los datos de la organización,
  usados por la pantalla de carga y por Acerca de. Cada clave tiene un valor por
  defecto en el código, así que la aplicación arranca aunque falte.
- Generadores de recursos en `tools/`: `make_icon.py` y `make_splash.py`.
- **Refuerzo del micrófono**: ganancia extra fija (+15% por defecto, ajustable
  de 0% a +100% desde *Configuración → Refuerzo del micrófono*) que se suma al
  volumen de la pista para que la voz quede por encima del audio del sistema.
  Se aplica también en mitad de una grabación y se recorta antes de saturar.
- **Interfaz con iconos** vectoriales dibujados en código, sin archivos
  externos, y **modo compacto de solo iconos** conmutable desde la barra
  superior, *Ver → Solo iconos* o `Ctrl+I`. La elección se recuerda y en modo
  compacto cada control conserva su descripción en el tooltip.
- Archivos de licencia: `LICENSE` (MIT), `LICENSE.es.md` (traducción
  informativa al español) y `NOTICE` con los componentes de terceros y sus
  licencias verificadas, incluido el aviso de que el ejecutable distribuido
  queda sujeto a GPL v3 por PyQt5 y la compilación de FFmpeg incorporada.
- Iconos en los menús y en los botones de silencio, que cambian de forma según
  el estado de la pista.
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
- **Icono de la aplicación borroso en la barra de tareas**: `logo.ico` solo tenía
  una imagen de 256x256 y Windows la reducía al vuelo. Ahora incluye las nueve
  resoluciones que el sistema pide (16 a 256 px), dibujadas una a una.
- **La ventana no usaba el icono del proyecto** mientras la aplicación estaba en
  ejecución: nunca se llamaba a `setWindowIcon`, así que se veía el icono
  genérico de Qt. Se añade también el identificador de aplicación de Windows para
  que la barra de tareas no la agrupe bajo el proceso anfitrión.
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

## Desarrollo previo

### Corregido
- Sincronía audio/vídeo, fuga de handles GDI en la captura del cursor,
  renderizado del cursor, cierre de la aplicación, congelación de la interfaz
  al guardar, negociación de canales de audio y mezcla sin recodificar.

### Cambiado
- FFmpeg incluido mediante `imageio-ffmpeg`.
- Eliminados `src/ui.py` y la infraestructura asíncrona sin usar.
