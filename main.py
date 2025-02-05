# video_streaming_project/main.py
import sys
import asyncio
import qasync
from PyQt5.QtWidgets import QApplication
from src.ui.main_window import StreamApp

def main():
    app = QApplication(sys.argv)
    
    # Crear loop de eventos asíncrono
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Crear y mostrar la ventana principal
    window = StreamApp()
    window.show()
    
    # Ejecutar la aplicación con soporte asíncrono
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()
