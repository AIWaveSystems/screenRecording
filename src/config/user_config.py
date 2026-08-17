"""Configuración persistente del usuario.

Se guarda en %APPDATA%\\ScreenRecorder\\config.json (o junto al ejecutable si
existe un portable.txt). La carga nunca lanza: un archivo corrupto se aparta
como .bak y se arranca con los valores por defecto de settings.py.
"""
import json
import os
import shutil
import sys
import tempfile

from . import settings

APP_DIR_NAME = "ScreenRecorder"
CONFIG_FILE = "config.json"
STATE_FILE = "state.json"
PORTABLE_MARKER = "portable.txt"
SCHEMA_VERSION = 1

USE_SYSTEM_DEFAULT = "__default__"

def _app_root():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def is_portable():
    return os.path.exists(os.path.join(_app_root(), PORTABLE_MARKER))

def config_dir():
    if is_portable():
        return os.path.join(_app_root(), "config")
    roaming = os.getenv('APPDATA')
    if roaming:
        return os.path.join(roaming, APP_DIR_NAME)
    return os.path.join(os.path.expanduser('~'), '.config', 'screen-recorder')

def data_dir():
    if is_portable():
        return os.path.join(_app_root(), "logs")
    local = os.getenv('LOCALAPPDATA')
    if local:
        return os.path.join(local, APP_DIR_NAME)
    return os.path.join(os.path.expanduser('~'), '.local', 'share', 'screen-recorder')

def config_path():
    return os.path.join(config_dir(), CONFIG_FILE)

def state_path():
    return os.path.join(config_dir(), STATE_FILE)

def defaults():
    return {
        'schema_version': SCHEMA_VERSION,
        'output_dir': settings.OUTPUT_DIR,
        'video': {
            'fps': settings.VIDEO_FPS,
            'codec': settings.VIDEO_CODEC,
            'capture_cursor': settings.CAPTURE_CURSOR,
        },
        'preview': {
            'fps': settings.PREVIEW_FPS,
            'max_width': settings.PREVIEW_MAX_WIDTH,
        },
        'audio': {
            'mic_device': USE_SYSTEM_DEFAULT,
            'speaker_device': USE_SYSTEM_DEFAULT,
            'mic_volume': 1.0,
            'speaker_volume': 1.0,
            'mic_muted': False,
            'speaker_muted': False,
            'mic_boost': settings.MIC_BOOST,
            'sample_rate': settings.AUDIO_SAMPLE_RATE,
        },
        'monitor': {
            'index': 0,
            'width': None,
            'height': None,
        },
        'ui': {
            'compact': settings.COMPACT_UI,
        },
    }

def _merge(base, incoming):
    """Fusiona sin perder claves desconocidas de versiones más nuevas."""
    result = dict(base)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result

def _as_int(value, low, high, fallback):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return number if low <= number <= high else fallback

def _as_float(value, low, high, fallback):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return number if low <= number <= high else fallback

def _as_bool(value, fallback):
    return value if isinstance(value, bool) else fallback

def _validate(config):
    """Corrige valores fuera de rango en lugar de rechazar el archivo entero."""
    base = defaults()

    video = config.setdefault('video', {})
    video['fps'] = _as_int(video.get('fps'), 1, 240, base['video']['fps'])
    codec = video.get('codec')
    video['codec'] = codec if isinstance(codec, str) and len(codec) == 4 \
        else base['video']['codec']
    video['capture_cursor'] = _as_bool(video.get('capture_cursor'),
                                       base['video']['capture_cursor'])

    preview = config.setdefault('preview', {})
    preview['fps'] = _as_int(preview.get('fps'), 1, 120, base['preview']['fps'])
    preview['max_width'] = _as_int(preview.get('max_width'), 160, 3840,
                                   base['preview']['max_width'])

    audio = config.setdefault('audio', {})
    for key in ('mic_volume', 'speaker_volume'):
        audio[key] = _as_float(audio.get(key), 0.0, 2.0, base['audio'][key])
    for key in ('mic_muted', 'speaker_muted'):
        audio[key] = _as_bool(audio.get(key), base['audio'][key])
    for key in ('mic_device', 'speaker_device'):
        value = audio.get(key, USE_SYSTEM_DEFAULT)
        audio[key] = value if value is None or isinstance(value, str) \
            else USE_SYSTEM_DEFAULT
    audio['mic_boost'] = _as_float(audio.get('mic_boost'), 1.0, 3.0,
                                   base['audio']['mic_boost'])
    audio['sample_rate'] = _as_int(audio.get('sample_rate'), 8000, 192000,
                                   base['audio']['sample_rate'])

    monitor = config.setdefault('monitor', {})
    monitor['index'] = _as_int(monitor.get('index'), 0, 63, 0)

    ui = config.setdefault('ui', {})
    ui['compact'] = _as_bool(ui.get('compact'), base['ui']['compact'])

    output_dir = config.get('output_dir')
    if not isinstance(output_dir, str) or not output_dir.strip():
        config['output_dir'] = base['output_dir']

    return config

def _migrate(config):
    """Aplica migraciones de esquema, una por versión."""
    version = config.get('schema_version', 0)
    if version < 1:
        config['schema_version'] = 1
    return config

def load():
    """Devuelve la configuración fusionada con los valores por defecto."""
    path = config_path()
    config = defaults()

    if not os.path.exists(path):
        return config

    try:
        with open(path, 'r', encoding='utf-8') as handle:
            stored = json.load(handle)
        if not isinstance(stored, dict):
            raise ValueError("el archivo no contiene un objeto JSON")
    except Exception as exc:
        backup = path + '.bak'
        try:
            shutil.move(path, backup)
            print(f"[config] {path} ilegible ({exc}); apartado en {backup}")
        except OSError:
            print(f"[config] {path} ilegible ({exc}); se usan los valores por defecto")
        return config

    return _validate(_merge(config, _migrate(stored)))

def save(config, path=None):
    """Guarda de forma atómica: un corte a mitad no deja un JSON truncado."""
    target = path or config_path()
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', delete=False,
            dir=os.path.dirname(target), suffix='.tmp',
        )
        with handle:
            json.dump(config, handle, indent=2, ensure_ascii=False)
        os.replace(handle.name, target)
        return True
    except Exception as exc:
        print(f"[config] no se pudo guardar {target}: {exc}")
        return False

def load_state():
    path = state_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            state = json.load(handle)
        return state if isinstance(state, dict) else {}
    except Exception:
        return {}

def save_state(state):
    return save(state, path=state_path())

def reset():
    """Aparta la configuración actual como .bak y devuelve los valores por defecto."""
    path = config_path()
    if os.path.exists(path):
        try:
            shutil.move(path, path + '.bak')
        except OSError as exc:
            print(f"[config] no se pudo apartar {path}: {exc}")
    return defaults()

def _folder_size(folder):
    total = 0
    for root, _, files in os.walk(folder):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total

def purge_targets(include_recordings=False, output_dir=None):
    """Carpetas que borraría --purge, con su tamaño. No borra nada."""
    targets = []
    for folder in (config_dir(), data_dir()):
        if os.path.isdir(folder):
            targets.append((folder, _folder_size(folder)))
    if include_recordings:
        folder = output_dir or load().get('output_dir')
        if folder and os.path.isdir(folder):
            targets.append((folder, _folder_size(folder)))
    return targets

def purge(include_recordings=False, output_dir=None):
    """Borra configuración y logs. Las grabaciones solo si se piden explícitamente."""
    removed = []
    for folder, _ in purge_targets(include_recordings, output_dir):
        try:
            shutil.rmtree(folder)
            removed.append(folder)
        except OSError as exc:
            print(f"[config] no se pudo borrar {folder}: {exc}")
    return removed
