# Screen Recorder

Aplicación de escritorio para grabar la pantalla con audio del sistema y micrófono.
La versión del instalador puede no ser la más reciente del programa.

## 🚀 Características

- Grabación de pantalla con captura de cursor
- Audio del sistema por **loopback WASAPI** (sin necesidad de "Mezcla estéreo" ni VB-Cable)
- Captura de micrófono, con canales y sample rate negociados con el dispositivo
- Sincronía audio/vídeo exacta: el vídeo se escribe a FPS constante contra el reloj real
  y el desfase de arranque de cada pista se compensa en la mezcla
- Previsualización en tiempo real, independiente de la grabación
- Soporte para múltiples monitores
- Salida AVI con compresión XVID, mezclada sin recodificar el vídeo

## 📋 Requisitos Previos

- Python 3.9 o superior
- Windows 10/11

FFmpeg viene incluido a través de `imageio-ffmpeg`; si tienes uno propio en el PATH,
se usa ese.

## 🔧 Instalación

1. Clona el repositorio:
```bash
git clone https://github.com/AIWaveSystems/screenRecording.git
cd screenRecording
```
* Ejecutable directo para Windows [aquí](https://github.com/AIWaveSystems/screenRecording/dist/)

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

1. Ejecuta la aplicación:
```bash
python main.py
```

2. Selecciona el monitor a grabar
3. Opcionalmente ajusta las fuentes de audio (por defecto se usan el micrófono y
   la salida predeterminados de Windows)
4. Pulsa "Iniciar Grabación"
5. Para terminar, pulsa "Detener Grabación"

Las grabaciones se guardan en `C:\Users\<usuario>\ScreenRecordings\<fecha>\`.

## 🛠️ Configuración

En `src/config/settings.py`:

| Ajuste | Por defecto | Descripción |
|---|---|---|
| `VIDEO_FPS` | 30 | FPS reales del archivo grabado |
| `PREVIEW_FPS` | 15 | FPS de la previsualización (no afecta a la grabación) |
| `VIDEO_CODEC` | `XVID` | FourCC del codec de OpenCV |
| `PREVIEW_MAX_WIDTH` | 640 | Ancho máximo del preview |
| `CAPTURE_CURSOR` | `True` | Dibujar el cursor sobre los frames |
| `AUDIO_MAX_CHANNELS` | 2 | Techo de canales; se negocia con el dispositivo |
| `AUDIO_SAMPLE_RATE` | 48000 | Preferido; se usa el nativo si no lo admite |

## 📁 Estructura del Proyecto

```
screenRecording/
├── src/
│   ├── config/
│   │   └── settings.py            # Configuración global
│   ├── core/
│   │   ├── screen_capture.py      # Hilo de captura + cursor
│   │   ├── audio_capture.py       # Pistas de micrófono y loopback
│   │   └── recording_manager.py   # Orquestación de la grabación
│   ├── utils/
│   │   └── video_utils.py         # Mezcla con FFmpeg
│   └── ui/
│       ├── main_window.py         # Ventana principal
│       └── audio_settings.py      # Diálogo de fuentes de audio
├── tests/                         # Pruebas manuales (ver abajo)
├── main.py                        # Punto de entrada
└── requirements.txt
```

## 🧪 Pruebas

Scripts manuales que ejercitan el hardware real:

```bash
python tests/smoke_test.py   # graba 6s y verifica duración, sincronía y mezcla
python tests/ui_test.py      # abre la ventana, graba, para y cierra
python tests/leak_test.py    # comprueba que no se filtran handles GDI
```

## 🔍 Solución de Problemas

### No se captura el audio del sistema
1. Comprueba que `soundcard` está instalado (`pip install soundcard`)
2. Verifica que la salida elegida es la que realmente está sonando
3. Si el equipo no admite loopback, se usa "Mezcla estéreo" como alternativa

### El vídeo se guarda sin audio
La app avisa en la barra de estado. Suele ser que FFmpeg no está disponible:
reinstala las dependencias con `pip install -r requirements.txt`.

## 🤝 Contribuir

1. Haz un Fork del proyecto
2. Crea una rama para tu característica (`git checkout -b feature/AmazingFeature`)
3. Haz commit de tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📦 Dependencias Principales

- `opencv-python`: escritura de vídeo
- `numpy`: manipulación de frames y audio
- `PyQt5` + `qasync`: interfaz gráfica y bucle asíncrono
- `mss`: captura de pantalla
- `sounddevice`: captura de micrófono
- `soundcard`: loopback WASAPI del audio del sistema
- `imageio-ffmpeg`: binario de FFmpeg para la mezcla
- `pywin32`: cursor y APIs de Windows

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## ✨ Agradecimientos

- [FFmpeg](https://ffmpeg.org/) por el procesamiento de vídeo
- Todos los contribuidores y usuarios

---
Desarrollado con ❤️ por [Ilesandres]
