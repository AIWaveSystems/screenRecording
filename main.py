"""Punto de entrada de Screen Recorder."""
import asyncio
import sys

import qasync
from PyQt5.QtWidgets import QApplication

from src.ui.main_window import StreamApp


def main():
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

if __name__ == "__main__":
    main()
