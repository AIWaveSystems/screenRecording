"""Punto de entrada de Screen Recorder.

Los módulos pesados (Qt, OpenCV, los backends de audio) se importan dentro de
main(), después de que la pantalla de carga esté visible. Importarlos arriba
dejaría la pantalla en negro durante los primeros segundos.
"""
import argparse
import sys

from src.config import app_info, user_config


def _format_size(size):
    for unit in ('B', 'KB', 'MB'):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def run_purge():
    """Borra configuración y logs. Las grabaciones solo si se confirman aparte."""
    output_dir = user_config.load().get('output_dir')
    targets = user_config.purge_targets()
    if not targets:
        print("No hay configuración que borrar.")
    else:
        print("Se borrarán estas carpetas:")
        for folder, size in targets:
            print(f"  {folder}  ({_format_size(size)})")
        if input("¿Continuar? [s/N]: ").strip().lower() not in ('s', 'si', 'y'):
            print("Cancelado.")
            return 1
        for folder in user_config.purge():
            print(f"borrado: {folder}")

    with_recordings = user_config.purge_targets(include_recordings=True,
                                                output_dir=output_dir)
    for folder, size in with_recordings:
        if any(folder == done for done, _ in targets):
            continue
        print(f"\nTus grabaciones siguen en:\n  {folder}  ({_format_size(size)})")
        if input("¿Borrarlas también? [s/N]: ").strip().lower() in ('s', 'si', 'y'):
            for removed in user_config.purge(include_recordings=True,
                                             output_dir=folder):
                print(f"borrado: {removed}")
        else:
            print("Las grabaciones se conservan.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Screen Recorder")
    parser.add_argument('--purge', action='store_true',
                        help="borra la configuración y los logs de la aplicación")
    parser.add_argument('--config-path', action='store_true',
                        help="muestra la ruta del archivo de configuración")
    args = parser.parse_args()

    if args.config_path:
        print(user_config.config_path())
        return 0
    if args.purge:
        return run_purge()

    return run_app()


def _close_installer_splash():
    """Cierra la pantalla nativa del instalador, si la aplicación va empaquetada.

    PyInstaller la muestra durante la extracción del ejecutable, antes de que
    exista intérprete de Python; se cierra en cuanto Qt puede pintar la suya.
    """
    try:
        import pyi_splash
        pyi_splash.close()
    except Exception:
        pass


def _set_taskbar_identity():
    """Da a la ventana identidad propia en la barra de tareas de Windows.

    Sin esto Windows agrupa la aplicación bajo el proceso anfitrión y muestra
    el icono de ese proceso en lugar del nuestro.
    """
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "AIWaveSystems.ScreenRecorder.1")
    except Exception:
        pass


def run_app():
    from PyQt5.QtWidgets import QApplication

    _set_taskbar_identity()

    app = QApplication(sys.argv)
    app.setApplicationName("Screen Recorder")

    from src.ui import icons

    app.setWindowIcon(icons.app_icon())

    from src.ui.splash import SplashScreen

    splash = SplashScreen(app_info.version_label())
    splash.show()
    splash.set_progress(5, "Iniciando...")
    _close_installer_splash()

    splash.set_progress(15, "Cargando componentes de vídeo...")
    import cv2

    splash.set_progress(25, "Cargando componentes de audio...")
    import sounddevice

    splash.set_progress(30, "Preparando el bucle de eventos...")
    import asyncio

    import qasync

    from src.ui.main_window import StreamApp

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    closed = asyncio.Event()
    app.aboutToQuit.connect(closed.set)

    try:
        window = StreamApp(progress=splash.set_progress)
    except Exception:
        splash.close()
        raise

    window.show()
    splash.finish(window)

    with loop:
        loop.run_until_complete(closed.wait())
    return 0

if __name__ == "__main__":
    sys.exit(main())
