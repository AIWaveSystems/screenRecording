# Screen Recorder

Una aplicación de escritorio eficiente y optimizada para grabar la pantalla con audio del sistema y micrófono.

## 🚀 Características

- Grabación de pantalla con captura de cursor
- Captura de audio del sistema
- Captura de audio del micrófono
- Previsualización en tiempo real
- Optimizado para bajo consumo de recursos
- Soporte para múltiples monitores
- Formato de salida en AVI con compresión XVID

## 📋 Requisitos Previos

- Python 3.8 o superior
- Windows 10/11
- FFmpeg instalado y en el PATH del sistema
- Controladores de audio actualizados

### Instalación de FFmpeg
1. Descarga FFmpeg desde [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extrae el archivo zip
3. Añade la carpeta `bin` al PATH del sistema

## 🔧 Instalación

1. Clona el repositorio:
```bash
git clone https://github.com/yourusername/screen-recorder.git
cd screen-recorder
```

2. Crea un entorno virtual:
```bash
python -m venv .venv
```

3. Activa el entorno virtual:
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
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
3. Configura las opciones de audio (sistema y/o micrófono)
4. Haz clic en "Iniciar Grabación"
5. Para detener, haz clic en "Detener Grabación"

Las grabaciones se guardan en:
- Windows: `C:\Users\<usuario>\ScreenRecordings\`

## 🛠️ Configuración

Puedes modificar la configuración en `src/config/settings.py`:

- `VIDEO_FPS`: Frames por segundo (default: 20)
- `VIDEO_QUALITY`: Calidad de video (1-31, menor es mejor)
- `PREVIEW_SCALE`: Escala de previsualización (0.1-1.0)
- `PROCESS_PRIORITY`: Prioridad del proceso ('low', 'normal', 'high')

## 📁 Estructura del Proyecto

```
screen-recorder/
├── src/
│   ├── config/
│   │   └── settings.py     # Configuración global
│   ├── core/
│   │   ├── screen_capture.py   # Captura de pantalla
│   │   └── audio_capture.py    # Captura de audio
│   ├── utils/
│   │   └── video_utils.py      # Utilidades de video
│   ├── ui/
│   │   └── main_window.py      # Interfaz de usuario
│   └── __init__.py
├── main.py                 # Punto de entrada
├── requirements.txt        # Dependencias
└── README.md
```

## 🔍 Solución de Problemas

### No se captura el audio del sistema
1. Verifica que VB-Cable o similar esté instalado
2. Configura el dispositivo de salida en la configuración de Windows
3. Asegúrate de que el volumen no esté silenciado

### Error de FFmpeg
1. Verifica que FFmpeg esté instalado correctamente
2. Asegúrate de que esté en el PATH del sistema
3. Reinicia la aplicación

## 🤝 Contribuir

1. Haz un Fork del proyecto
2. Crea una rama para tu característica (`git checkout -b feature/AmazingFeature`)
3. Haz commit de tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Notas de Optimización

- La aplicación está optimizada para bajo consumo de recursos
- Usa buffering para reducir escrituras a disco
- Implementa captura de cursor eficiente
- Control adaptativo de FPS
- Procesamiento de audio en lotes

## 📦 Dependencias Principales

- `opencv-python`: Procesamiento de video
- `numpy`: Manipulación de datos
- `PyQt5`: Interfaz gráfica
- `mss`: Captura de pantalla
- `sounddevice`: Captura de audio
- `pywin32`: Funcionalidades de Windows
- `psutil`: Gestión de procesos

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## ✨ Agradecimientos

- [FFmpeg](https://ffmpeg.org/) por el procesamiento de video
- [VB-Audio](https://vb-audio.com/) por VB-Cable
- Todos los contribuidores y usuarios

---
Desarrollado con ❤️ por [Tu Nombre]