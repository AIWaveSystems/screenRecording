"""Punto de entrada de Screen Recorder."""
import argparse
import asyncio
import sys

import qasync
from PyQt5.QtWidgets import QApplication

from src.config import user_config
from src.ui.main_window import StreamApp


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

    app = QApplication(sys.argv)
    app.setApplicationName("Screen Recorder")

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    closed = asyncio.Event()
    app.aboutToQuit.connect(closed.set)

    window = StreamApp()
    window.show()

    with loop:
        loop.run_until_complete(closed.wait())
    return 0

if __name__ == "__main__":
    sys.exit(main())
