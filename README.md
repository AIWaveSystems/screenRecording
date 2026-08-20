# Screen Recorder

Grabador de pantalla para Windows con captura de audio del sistema y micrófono,
pensado para ser ligero y no pelearse con la configuración de sonido de Windows.

[![Descargar](https://img.shields.io/github/v/release/AIWaveSystems/screenRecording?label=descargar&style=for-the-badge)](https://github.com/AIWaveSystems/screenRecording/releases/latest)
[![Licencia](https://img.shields.io/badge/c%C3%B3digo-MIT-blue?style=for-the-badge)](LICENSE)
[![Plataforma](https://img.shields.io/badge/plataforma-Windows%2010%20%7C%2011-lightgrey?style=for-the-badge)](#-requisitos)

## ⬇️ Descarga

**[Descargar ScreenRecorder.exe](https://github.com/AIWaveSystems/screenRecording/releases/latest/download/ScreenRecorder.exe)**
— o revisa [todas las versiones](https://github.com/AIWaveSystems/screenRecording/releases).

No requiere instalación ni dependencias: FFmpeg y todo lo necesario van dentro
del ejecutable. Descárgalo y ábrelo.

> **Aviso de Windows SmartScreen.** El ejecutable no está firmado digitalmente,
> así que Windows mostrará una advertencia la primera vez. Pulsa
> *Más información → Ejecutar de todas formas*.

Si prefieres ejecutarlo desde el código fuente, ve a [Instalación](#-instalación).

## 🚀 Características

- Grabación de pantalla con captura de cursor
- Audio del sistema por **loopback WASAPI** (sin necesidad de "Mezcla estéreo" ni VB-Cable)
- Captura de micrófono, con canales y sample rate negociados con el dispositivo
- Sincronía audio/vídeo exacta: el vídeo se escribe a FPS constante contra el reloj real
  y el desfase de arranque de cada pista se compensa en la mezcla
- Mezclador con medidores de nivel, volumen y **silencio por pista**, ajustables
  también en mitad de la grabación
- **Refuerzo del micrófono** configurable, para que la voz destaque sobre el
  audio del sistema
- Interfaz con iconos, con modo compacto de solo iconos (`Ctrl+I`)
- Pantalla de carga con progreso real durante el arranque
- Ventana *Acerca de* con la versión y los datos de la organización
- Pausa y reanudación sin descuadrar la duración del archivo
- Previsualización en tiempo real, independiente de la grabación
- Soporte para múltiples monitores
- Configuración persistente entre sesiones (monitor, dispositivos, volúmenes)
- Salida AVI con compresión XVID, mezclada sin recodificar el vídeo

## 📋 Requisitos

| | Ejecutable | Desde el código |
|---|---|---|
| Sistema | Windows 10 u 11 (64 bits) | Windows 10 u 11 (64 bits) |
| Python | no hace falta | 3.9 o superior |
| FFmpeg | incluido | incluido vía `imageio-ffmpeg` |

Si tienes tu propio FFmpeg en el PATH, se usa ese en lugar del incluido.

## 🔧 Instalación

> Solo si vas a ejecutarlo desde el código. Para usarlo sin más, ve a
> [Descarga](#-descarga).

1. Clona el repositorio:
```bash
git clone https://github.com/AIWaveSystems/screenRecording.git
cd screenRecording
```

2. Crea un entorno virtual:
```bash
python -m venv .venv
```

3. Actívalo:
```bash
.venv\Scripts\activate
```

4. Instala las dependencias:
```bash
pip install -r requirements.txt
```

## 🎮 Uso

Abre `ScreenRecorder.exe`, o desde el código:

```bash
python main.py
```

1. Selecciona el monitor a grabar
2. Opcionalmente ajusta las fuentes de audio (por defecto se usan el micrófono y
   la salida predeterminados de Windows)
3. Ajusta volúmenes o silencia una pista en el mezclador de la derecha; se puede
   hacer antes y durante la grabación
4. Pulsa "Iniciar Grabación"
5. Para terminar, pulsa "Detener Grabación"

Las grabaciones se guardan en `C:\Users\<usuario>\ScreenRecordings\<fecha>\`,
o en la carpeta que elijas en *Archivo → Cambiar carpeta de salida*.

**Silenciar no es lo mismo que no grabar.** Una pista silenciada se sigue
grabando como silencio, así que la duración y la sincronía se mantienen. Para no
grabar una fuente en absoluto, elige "(Sin grabar)" en *Configuración → Fuentes
de audio*.

### Refuerzo del micrófono

El micrófono se graba con una ganancia extra fija (**+15% por defecto**) además
de su volumen, para que la voz quede por encima del audio del sistema sin tener
que bajar este último. Se ajusta entre 0% y +100% en *Configuración → Refuerzo
del micrófono*, y se aplica también en mitad de una grabación.

En el mezclador aparece junto al volumen, por ejemplo `100% +15%`. La señal se
recorta antes de saturar, pero un refuerzo alto sobre un micrófono que ya graba
fuerte puede distorsionar: 10-20% es el rango sensato.

### Iconos o texto

Toda la interfaz funciona en dos modos: con **texto e iconos**, o **solo
iconos** para ahorrar espacio. Se alterna con el botón de la barra superior, en
*Ver → Solo iconos* o con `Ctrl+I`, y la elección se recuerda. En modo compacto
cada botón conserva su descripción en el tooltip.

## ⚙️ Configuración

Los ajustes se guardan solos al cambiarlos y se recuperan al arrancar.

| Sistema | Ruta |
|---|---|
| Windows | `%APPDATA%\ScreenRecorder\config.json` |
| Otros | `~/.config/screen-recorder/config.json` |

La posición de la ventana va aparte, en `state.json`, para que un problema con
ella no afecte a las preferencias. Consulta la ruta exacta con:

```bash
ScreenRecorder.exe --config-path    # o: python main.py --config-path
```

### Qué se guarda

| Clave | Por defecto | Descripción |
|---|---|---|
| `output_dir` | `~\ScreenRecordings` | Carpeta de las grabaciones |
| `video.fps` | `30` | FPS reales del archivo grabado (1-240) |
| `video.codec` | `"XVID"` | FourCC de OpenCV, 4 caracteres |
| `video.capture_cursor` | `true` | Dibujar el cursor sobre los frames |
| `preview.fps` | `15` | FPS de la previsualización (no afecta a la grabación) |
| `preview.max_width` | `640` | Ancho máximo del preview (160-3840) |
| `audio.mic_device` | `"__default__"` | Nombre del micrófono, `"__default__"` para el del sistema o `null` para no grabarlo |
| `audio.speaker_device` | `"__default__"` | Igual, para la salida de audio |
| `audio.mic_volume` | `1.0` | Volumen del micrófono (0.0-2.0) |
| `audio.speaker_volume` | `1.0` | Volumen del audio del sistema (0.0-2.0) |
| `audio.mic_muted` | `false` | Micrófono silenciado |
| `audio.speaker_muted` | `false` | Audio del sistema silenciado |
| `audio.mic_boost` | `1.15` | Refuerzo fijo del micrófono, `1.15` = +15% (1.0-3.0) |
| `audio.sample_rate` | `48000` | Preferido; se usa el nativo si no se admite |
| `monitor.index` | `0` | Monitor seleccionado |
| `ui.compact` | `false` | Interfaz de solo iconos |

Los dispositivos se guardan **por nombre**, no por índice: los índices cambian
al conectar o quitar hardware. Si el dispositivo guardado ya no existe, se usa
el predeterminado y se avisa en la barra de estado.

Hay un ejemplo completo en [config.example.json](config.example.json).

### Editarlo y restablecerlo

El archivo es JSON y se puede editar a mano con cualquier editor; los cambios se
aplican al siguiente arranque. Si queda mal escrito, la aplicación **no falla**:
lo aparta como `config.json.bak` y arranca con los valores por defecto. Los
valores fuera de rango se corrigen en silencio en lugar de descartar el archivo
entero.

Desde el menú *Configuración*: **Abrir carpeta de configuración** y
**Restablecer configuración** (que también deja una copia `.bak`).

Borrar la carpeta a mano es seguro: la aplicación vuelve a los valores por
defecto en el siguiente arranque.

### Modo portable

Si colocas un archivo vacío llamado `portable.txt` junto al ejecutable, la
configuración y los logs se guardan en subcarpetas de la propia aplicación en
lugar de en `%APPDATA%`. Útil para llevarla en un USB sin dejar rastro.

### Desinstalar

No hay instalador, así que la limpieza la hace la propia aplicación:

```bash
python main.py --purge        # o: ScreenRecorder.exe --purge
```

Muestra qué carpetas va a borrar con su tamaño y pide confirmación. Borra
configuración y logs. **Tus grabaciones no se tocan**: se ofrecen aparte, en una
segunda pregunta que por defecto responde que no.

## 🏷️ Marca y versión

El nombre, la versión y los datos de la organización viven en
[`.env`](.env), no repartidos por el código:

| Clave | Valor actual | Dónde se ve |
|---|---|---|
| `APP_NAME` | `Screen Recorder` | Título, pantalla de carga, Acerca de |
| `APP_VERSION` | `1.0.0` | Pantalla de carga y Acerca de |
| `ORG_NAME` | `AIWaveSystems` | Acerca de |
| `ORG_TAGLINE` | `Powered by AIWaveSystems` | Pie de la pantalla de carga |
| `ORG_LOGO_URL` | avatar de la organización | Acerca de |
| `ORG_LOGO_FILE` | `assets/aiwavesystems.png` | Copia local del logo |
| `APP_REPO_URL`, `APP_ISSUES_URL` | enlaces del repositorio | Botones de Acerca de |

Para publicar una versión nueva basta cambiar `APP_VERSION`. El archivo se
versiona en git porque no contiene secretos, solo datos públicos que la
aplicación necesita al arrancar; si falta, cada clave tiene un valor por defecto
en `src/config/app_info.py` y la aplicación funciona igual.

El logo de la organización se muestra desde la copia incluida en `assets/`. Si
no estuviera, se descarga de `ORG_LOGO_URL` en segundo plano y se guarda en
caché; sin conexión se usa el icono de la aplicación.

Los recursos gráficos se regeneran con:

```bash
python tools/make_icon.py     # logo.ico con las 9 resoluciones de Windows
python tools/make_splash.py   # assets/splash.png para el arranque del .exe
```

## 📁 Estructura del Proyecto

```
screenRecording/
├── src/
│   ├── config/
│   │   ├── settings.py            # Valores por defecto
│   │   ├── app_info.py            # Marca y versión leídas del .env
│   │   └── user_config.py         # Configuración persistente del usuario
│   ├── core/
│   │   ├── screen_capture.py      # Hilo de captura + cursor
│   │   ├── audio_capture.py       # Pistas de micrófono y loopback
│   │   └── recording_manager.py   # Orquestación de la grabación
│   ├── utils/
│   │   └── video_utils.py         # Mezcla con FFmpeg
│   └── ui/
│       ├── main_window.py         # Ventana principal y mezclador
│       ├── icons.py               # Iconos vectoriales sin archivos externos
│       ├── splash.py              # Pantalla de carga
│       ├── about.py               # Ventana Acerca de
│       └── audio_settings.py      # Diálogos de audio y refuerzo
├── assets/                        # Logo de la organización e imagen de carga
├── tools/                         # Generadores de logo.ico y splash.png
├── tests/                         # Pruebas (ver abajo)
├── .env                           # Nombre, versión y datos de la organización
├── config.example.json            # Configuración de referencia
├── main.py                        # Punto de entrada
├── main.spec                      # Receta de PyInstaller
├── requirements.txt
├── CHANGELOG.md                   # Novedades por versión
├── LICENSE / LICENSE.es.md        # Licencia MIT del código
└── NOTICE                         # Licencias de terceros
```

## 📦 Compilar el ejecutable

```bash
pip install pyinstaller
pyinstaller main.spec
```

El resultado queda en `dist/ScreenRecorder.exe`. La receta incluye el binario de
FFmpeg y el backend de audio, así que el ejecutable no necesita nada más. Pesa
unos 150 MB porque lleva Qt y FFmpeg completos dentro.

## 🧪 Pruebas

```bash
python tests/config_test.py     # configuración: round-trip, corrupción, migración
python tests/boost_test.py      # el refuerzo del micrófono llega al WAV
python tests/about_test.py      # .env, ventana Acerca de y marca
python tests/splash_test.py     # pantalla de carga e icono de la aplicación
python tests/ui_visual_test.py  # iconos, modo compacto y capturas de pantalla
python tests/smoke_test.py      # graba 6s: duración, sincronía, mute y mezcla
python tests/ui_test.py         # ventana: grabar, pausar, silenciar, cerrar
python tests/leak_test.py       # comprueba que no se filtran handles GDI
```

`config_test.py` y `boost_test.py` no tocan hardware; el resto captura la
pantalla y abre dispositivos de audio reales. `ui_visual_test.py` deja capturas
de ambos modos de interfaz en `_ui_shots/`.

## ⚠️ Limitaciones conocidas

Conviene saber qué **no** hace todavía antes de usarlo para algo serio:

- **Solo Windows.** Usa APIs propias del sistema para el cursor y el audio.
- **Codificación por CPU** (XVID). Aún no usa el codificador por hardware de la
  tarjeta gráfica, así que en 4K o con equipos modestos el consumo es notable.
- **Se graba el monitor completo**: no hay selección de región ni de una ventana
  concreta.
- Sin cámara web, sin atajos de teclado globales y sin escenas ni fuentes
  múltiples al estilo de OBS.
- Salida en AVI. Todavía no hay MP4 ni elección de contenedor desde la interfaz.

## 🔍 Solución de Problemas

### Windows bloquea el ejecutable o el antivirus lo marca
El `.exe` no está firmado digitalmente y PyInstaller empaqueta un intérprete de
Python dentro, algo que algunos antivirus marcan por heurística. En SmartScreen,
*Más información → Ejecutar de todas formas*. Si prefieres no fiarte del binario,
[ejecútalo desde el código fuente](#-instalación): hace exactamente lo mismo.

### No se captura el audio del sistema
1. Verifica que la salida elegida en *Configuración → Fuentes de audio* es la que
   realmente está sonando
2. Si el equipo no expone loopback, se usa "Mezcla estéreo" como alternativa
3. Ejecutando desde el código, comprueba que `PyAudioWPatch` está instalado
   (`pip install PyAudioWPatch`)

### El vídeo se guarda sin audio
La app avisa en la barra de estado. Suele ser que FFmpeg no está disponible:
en el ejecutable va incluido, y desde el código se reinstala con
`pip install -r requirements.txt`.

### He editado el config y la app no lo respeta
Si el JSON quedó mal escrito, se apartó como `config.json.bak` y se arrancó con
los valores por defecto. Revísalo con cualquier validador de JSON. Los valores
fuera de rango se corrigen solos: revisa los límites en la tabla de arriba.

### No recuerda mi micrófono
Los dispositivos se guardan por nombre. Si Windows lo renombró (pasa al cambiar
de puerto USB o actualizar drivers), vuelve a elegirlo en *Configuración →
Fuentes de audio*.

## 🤝 Contribuir

¿Un fallo o una idea? Abre un
[issue](https://github.com/AIWaveSystems/screenRecording/issues). Si reportas un
problema de grabación, indica tu versión de Windows y qué dispositivos de audio
tenías seleccionados.

Para contribuir código:

1. Haz un Fork del proyecto
2. Crea una rama para tu característica (`git checkout -b feature/AmazingFeature`)
3. Ejecuta las pruebas antes de enviar los cambios
4. Haz commit de tus cambios (`git commit -m 'Add some AmazingFeature'`)
5. Push a la rama (`git push origin feature/AmazingFeature`)
6. Abre un Pull Request

## 📦 Dependencias Principales

- `opencv-python`: escritura de vídeo
- `numpy`: manipulación de frames y audio
- `PyQt5` + `qasync`: interfaz gráfica y bucle asíncrono
- `mss`: captura de pantalla
- `sounddevice`: captura de micrófono y enumeración de dispositivos
- `PyAudioWPatch`: loopback WASAPI del audio del sistema
- `imageio-ffmpeg`: binario de FFmpeg para la mezcla
- `pywin32`: cursor y APIs de Windows

## 📄 Licencia

El **código fuente** está bajo la Licencia MIT — ver [LICENSE](LICENSE), con una
[traducción informativa al español](LICENSE.es.md) que además explica qué
implica en la práctica.

El **ejecutable distribuido** es otra cosa: incorpora PyQt5 y una compilación de
FFmpeg que son GPL v3, así que el binario ya compilado queda sujeto a GPL v3.
Los componentes de terceros, sus licencias y las alternativas para distribuir la
aplicación con una licencia permisiva están detallados en [NOTICE](NOTICE).

## ✨ Agradecimientos

- [FFmpeg](https://ffmpeg.org/) por el procesamiento de vídeo
- [PortAudio](http://www.portaudio.com/) y
  [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch) por hacer viable el
  loopback WASAPI
- [python-mss](https://github.com/BoboTiG/python-mss) por la captura de pantalla
- Todos los contribuidores y usuarios

---
Desarrollado con ❤️ por [Ilesandres](https://github.com/Ilesandres)
