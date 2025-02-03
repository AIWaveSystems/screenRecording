# video_streaming_project/main.py
import sys
from PyQt5.QtWidgets import QApplication
from src.ui import StreamApp  # Importamos la clase StreamApp

def main():
    app = QApplication(sys.argv)
    window = StreamApp()  # Creamos la ventana de la aplicación
    window.show()  # Mostramos la ventana
    sys.exit(app.exec_())  # Ejecutamos la aplicación

if __name__ == "__main__":
    main()
