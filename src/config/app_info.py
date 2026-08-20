"""Datos de marca y version, leidos de .env con valores por defecto en codigo.

El .env se busca junto al ejecutable empaquetado, en la raiz del proyecto y en
el directorio actual. Si falta o esta incompleto la aplicacion arranca igual:
cada clave tiene un valor por defecto.
"""
import os
import sys

ENV_FILE = ".env"

DEFAULTS = {
    'APP_NAME': "Screen Recorder",
    'APP_VERSION': "1.0.0",
    'APP_DESCRIPTION': "Grabador de pantalla con audio del sistema y microfono",
    'APP_REPO_URL': "https://github.com/AIWaveSystems/screenRecording",
    'APP_RELEASES_URL': "https://github.com/AIWaveSystems/screenRecording/releases",
    'APP_ISSUES_URL': "https://github.com/AIWaveSystems/screenRecording/issues",
    'APP_LICENSE': "MIT",
    'APP_AUTHOR': "Ilesandres",
    'APP_AUTHOR_URL': "https://github.com/Ilesandres",
    'APP_COPYRIGHT': "Copyright (c) 2026 Ilesandres",
    'ORG_NAME': "AIWaveSystems",
    'ORG_URL': "https://github.com/AIWaveSystems",
    'ORG_LOGO_URL': "https://avatars.githubusercontent.com/u/196564504?s=200&v=4",
    'ORG_LOGO_FILE': "assets/aiwavesystems.png",
    'ORG_TAGLINE': "Powered by AIWaveSystems",
}


def app_root():
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _search_paths():
    seen = []
    for folder in (getattr(sys, '_MEIPASS', None),
                   os.path.dirname(os.path.abspath(sys.argv[0] or '.')),
                   app_root(),
                   os.getcwd()):
        if folder and folder not in seen:
            seen.append(folder)
    return [os.path.join(folder, ENV_FILE) for folder in seen]


def _parse(path):
    valores = {}
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            for linea in handle:
                linea = linea.strip()
                if not linea or linea.startswith('#') or '=' not in linea:
                    continue
                clave, _, valor = linea.partition('=')
                valor = valor.strip()
                if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
                    valor = valor[1:-1]
                valores[clave.strip()] = valor
    except OSError as exc:
        print(f"[app_info] no se pudo leer {path}: {exc}")
    return valores


def _load():
    valores = dict(DEFAULTS)
    for path in _search_paths():
        if os.path.exists(path):
            valores.update({k: v for k, v in _parse(path).items() if v})
            break
    for clave in DEFAULTS:
        entorno = os.environ.get(clave)
        if entorno:
            valores[clave] = entorno
    return valores


_VALUES = _load()


def get(key, default=""):
    return _VALUES.get(key, DEFAULTS.get(key, default))


def reload():
    """Vuelve a leer el .env, util tras editarlo a mano."""
    global _VALUES
    _VALUES = _load()
    return _VALUES


def version_label():
    return f"v{get('APP_VERSION')}"


def org_logo_path():
    """Ruta absoluta del logo de la organizacion incluido, o None."""
    relativa = get('ORG_LOGO_FILE')
    if not relativa:
        return None
    for folder in (getattr(sys, '_MEIPASS', None), app_root(), os.getcwd()):
        if not folder:
            continue
        candidata = os.path.join(folder, relativa)
        if os.path.exists(candidata):
            return candidata
    return None


APP_NAME = get('APP_NAME')
APP_VERSION = get('APP_VERSION')
ORG_NAME = get('ORG_NAME')
ORG_TAGLINE = get('ORG_TAGLINE')
